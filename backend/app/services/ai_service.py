import json
import re
import socket
import threading
import urllib.error
import urllib.request
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.ai import AiGenerationRecord, RagRetrievalRecord
from app.models.case import TestCaseNode, TestCaseSet
from app.models.knowledge import FaissIndex, KnowledgeChunk, KnowledgeSource
from app.schemas.ai import AiGenerateRequest
from app.schemas.rag import RagSearchRequest
from app.services.case_service import create_node_version, ensure_user_exists
from app.services.rag_service import search_knowledge_base


PROMPT_TEMPLATE_VERSION = "v1"
MAX_GENERATED_NODE_COUNT = 120
MAX_GENERATED_TREE_DEPTH = 6
VALID_NODE_TYPES = {"folder", "case"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
GENERATION_MODE_GUIDES = {
    "comprehensive": "综合覆盖功能主流程、异常场景、边界条件、兼容性与回归风险，输出结构均衡的测试用例。",
    "functional": "重点覆盖功能主流程、关键业务路径、典型用户操作和正向验证。",
    "boundary": "重点覆盖边界值、阈值、极限输入、容量限制、状态临界点和参数组合边界。",
    "exception": "重点覆盖异常输入、错误状态、断网断电、资源不足、权限不足、设备故障和恢复场景。",
    "compatibility": "重点覆盖不同硬件版本、浏览器、分辨率、协议、系统版本和外设组合的兼容性。",
    "regression": "重点覆盖历史缺陷、核心链路、版本升级影响面和高风险回归路径。",
}
_generation_tasks: dict[str, dict] = {}


SYSTEM_PROMPT = """
你是硬件测试用例生成助手。
必须遵守以下要求：
1. 禁止输出思考过程。
2. 禁止输出推理草稿。
3. 禁止输出 <reasoning> 标签内容。
4. 只输出最终结构化测试用例结果。
5. 输出必须是合法 JSON，不要使用 Markdown 代码块。
6. JSON 顶层必须包含 case_set_name 和 nodes。
7. nodes 是树形数组，每个节点包含 title、node_type、priority、precondition、test_steps、expected_result、children。
8. node_type 只能是 folder 或 case。
9. priority 只能是 P0、P1、P2、P3。
""".strip()


def generate_test_cases(db: Session, data: AiGenerateRequest, progress_callback=None) -> dict:
    ensure_user_exists(db, data.created_by)

    if progress_callback:
        progress_callback(8, "准备生成", "正在校验用户与生成参数...")

    if progress_callback:
        progress_callback(20, "RAG检索", "正在获取知识片段上下文...")
    search_result = get_generation_context(db, data)
    retrieved_items = search_result["items"]
    if not retrieved_items:
        raise HTTPException(status_code=400, detail="RAG没有检索到可用上下文，请先补充知识库资料")

    if progress_callback:
        progress_callback(35, "记录检索", f"已获取 {len(retrieved_items)} 个知识片段，正在保存检索记录...")
    faiss_index = db.get(FaissIndex, search_result["faiss_index_id"])
    chunk_ids = [item["chunk_id"] for item in retrieved_items]
    scores = [item["score"] for item in retrieved_items]

    retrieval_record = RagRetrievalRecord(
        user_id=data.created_by,
        knowledge_base_id=data.knowledge_base_id,
        faiss_index_id=search_result["faiss_index_id"],
        query_text=data.requirement_text,
        embedding_model=faiss_index.embedding_model if faiss_index else settings.embedding_model_name,
        top_k=data.top_k,
        retrieved_chunk_ids=chunk_ids,
        retrieved_scores=scores,
    )
    db.add(retrieval_record)
    db.flush()

    prompt_variables = {
        "requirement_text": data.requirement_text,
        "contexts": [item["chunk_text"] for item in retrieved_items],
        "selected_chunk_ids": data.selected_chunk_ids or [],
        "generation_mode": normalize_generation_mode(data.generation_mode),
        "score_threshold": data.score_threshold,
    }
    if progress_callback:
        progress_callback(45, "拼接Prompt", "正在整理需求与知识片段...")
    user_prompt = build_user_prompt(data.requirement_text, retrieved_items, data.generation_mode)

    generation_record = AiGenerationRecord(
        user_id=data.created_by,
        retrieval_id=retrieval_record.retrieval_id,
        requirement_text=data.requirement_text,
        model_provider="DeepSeek",
        model_name=settings.deepseek_model,
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
        prompt_variables_json=prompt_variables,
        used_chunk_ids=chunk_ids,
        generated_text="",
        generation_status="success",
    )
    db.add(generation_record)
    db.flush()

    try:
        if progress_callback:
            progress_callback(58, "调用模型", "正在调用 DeepSeek 生成测试用例...")
        generated_text = call_deepseek(user_prompt)
        if progress_callback:
            progress_callback(78, "校验结果", "正在解析并校验生成的JSON结构...")
        generated_json = parse_generated_json(generated_text)
        if progress_callback and data.save_to_case_set:
            progress_callback(88, "保存草稿", "正在保存为草稿用例集...")
        case_set_id = save_generated_case_set(db, generated_json, data.created_by) if data.save_to_case_set else None

        generation_record.generated_text = generated_text
        generation_record.generated_json = generated_json
        generation_record.case_set_id = case_set_id
        generation_record.generation_status = "success"
        db.commit()
        db.refresh(generation_record)
        if progress_callback:
            progress_callback(100, "完成", "AI生成完成")

        return {
            "generation_id": generation_record.generation_id,
            "retrieval_id": retrieval_record.retrieval_id,
            "case_set_id": case_set_id,
            "generated_json": generated_json,
            "generated_text": generated_text,
        }
    except Exception as error:
        safe_message = safe_ai_error_message(error)
        generation_record.generated_text = generation_record.generated_text or ""
        generation_record.generation_status = "failed"
        generation_record.error_message = safe_message
        db.commit()
        raise HTTPException(status_code=500, detail=safe_message) from error


def start_generate_test_cases(data: AiGenerateRequest, operator_id: int) -> dict:
    """启动异步 AI 生成任务，立即返回 task_id。"""
    data.created_by = operator_id
    task_id = str(uuid.uuid4())
    _generation_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "stage": "等待",
        "detail": "任务排队中",
    }
    thread = threading.Thread(target=_run_generation_task, args=(task_id, data), daemon=True)
    thread.start()
    return {"task_id": task_id, "status": "running"}


def get_generation_progress(task_id: str) -> dict:
    task = _generation_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="生成任务不存在")
    return task


def _run_generation_task(task_id: str, data: AiGenerateRequest) -> None:
    def progress_callback(progress: int, stage: str, detail: str) -> None:
        _generation_tasks[task_id] = {
            "status": "running",
            "progress": progress,
            "stage": stage,
            "detail": detail,
        }

    db = SessionLocal()
    try:
        progress_callback(3, "开始", "任务已启动")
        result = generate_test_cases(db, data, progress_callback)
        _generation_tasks[task_id] = {
            "status": "success",
            "progress": 100,
            "stage": "完成",
            "detail": "AI生成完成",
            "result": result,
        }
    except HTTPException as error:
        _generation_tasks[task_id] = {
            "status": "error",
            "progress": _generation_tasks.get(task_id, {}).get("progress", 0),
            "stage": "失败",
            "detail": str(error.detail),
        }
    except Exception as error:
        _generation_tasks[task_id] = {
            "status": "error",
            "progress": _generation_tasks.get(task_id, {}).get("progress", 0),
            "stage": "失败",
            "detail": safe_ai_error_message(error),
        }
    finally:
        db.close()


def get_generation_context(db: Session, data: AiGenerateRequest) -> dict:
    """获取 AI 生成上下文：优先使用用户勾选的知识片段，否则按 top_k 自动检索。"""
    if data.selected_chunk_ids:
        return load_selected_chunks_for_generation(db, data.knowledge_base_id, data.selected_chunk_ids, data.requirement_text)
    return search_knowledge_base(
        db,
        data.knowledge_base_id,
        RagSearchRequest(query_text=data.requirement_text, top_k=data.top_k, score_threshold=data.score_threshold),
    )


def load_selected_chunks_for_generation(
    db: Session,
    knowledge_base_id: int,
    selected_chunk_ids: list[int],
    requirement_text: str,
) -> dict:
    chunk_ids = list(dict.fromkeys(selected_chunk_ids))
    if len(chunk_ids) > 10:
        raise HTTPException(status_code=400, detail="最多只能选择10个知识片段参与生成")

    faiss_index = db.scalar(
        select(FaissIndex).where(
            FaissIndex.knowledge_base_id == knowledge_base_id,
            FaissIndex.index_name == "main",
            FaissIndex.status == "active",
        )
    )
    if not faiss_index:
        raise HTTPException(status_code=400, detail="当前知识库还没有可用FAISS索引，请先构建索引")

    chunks = list(
        db.scalars(
            select(KnowledgeChunk).where(
                KnowledgeChunk.chunk_id.in_(chunk_ids),
                KnowledgeChunk.faiss_index_id == faiss_index.faiss_index_id,
                KnowledgeChunk.is_deleted == 0,
            )
        ).all()
    )
    if len(chunks) != len(chunk_ids):
        raise HTTPException(status_code=400, detail="存在无效或已删除的知识片段，请重新预检索后再生成")

    chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
    ordered_chunks = [chunk_map[chunk_id] for chunk_id in chunk_ids]
    source_ids = list({chunk.source_id for chunk in ordered_chunks})
    sources = list(db.scalars(select(KnowledgeSource).where(KnowledgeSource.source_id.in_(source_ids))).all())
    source_names = {source.source_id: source.source_name for source in sources}

    return {
        "knowledge_base_id": knowledge_base_id,
        "faiss_index_id": faiss_index.faiss_index_id,
        "query_text": requirement_text,
        "items": [
            {
                "chunk_id": chunk.chunk_id,
                "source_id": chunk.source_id,
                "source_name": source_names.get(chunk.source_id),
                "score": 1.0,
                "chunk_text": chunk.chunk_text,
                "metadata": chunk.metadata_json,
            }
            for chunk in ordered_chunks
        ],
    }


def safe_ai_error_message(error: Exception) -> str:
    if isinstance(error, HTTPException):
        return str(error.detail)

    text = str(error)
    if "DEEPSEEK_API_KEY" in text:
        return "AI服务未配置，请检查DeepSeek API Key"
    if "HTTP 401" in text or "HTTP 403" in text:
        return "AI服务鉴权失败，请检查DeepSeek API Key"
    if "HTTP 429" in text:
        return "AI服务请求过于频繁，请稍后重试"
    if "HTTP 5" in text:
        return "AI服务暂时不可用，请稍后重试"
    if "超时" in text or "network" in text.lower() or "timed out" in text.lower():
        return "AI服务响应超时，请稍后重试或缩短需求文本"
    if "JSON" in text or "json" in text or "合法" in text:
        return "AI返回内容格式不符合要求，请重试"
    return "AI生成失败，请检查后端日志"


def list_generation_records(db: Session) -> list[AiGenerationRecord]:
    statement = select(AiGenerationRecord).order_by(AiGenerationRecord.generation_id.desc()).limit(50)
    return list(db.scalars(statement).all())


def get_generation_record_detail(db: Session, generation_id: int) -> dict:
    record = db.get(AiGenerationRecord, generation_id)
    if not record:
        raise HTTPException(status_code=404, detail="AI生成记录不存在")

    retrieved_items = []
    retrieval = db.get(RagRetrievalRecord, record.retrieval_id) if record.retrieval_id else None
    chunk_ids = list(retrieval.retrieved_chunk_ids or record.used_chunk_ids or []) if retrieval else list(record.used_chunk_ids or [])
    scores = list(retrieval.retrieved_scores or []) if retrieval else []
    if chunk_ids:
        chunks = list(
            db.scalars(
                select(KnowledgeChunk).where(
                    KnowledgeChunk.chunk_id.in_(chunk_ids),
                    KnowledgeChunk.is_deleted == 0,
                )
            ).all()
        )
        chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
        source_ids = list({chunk.source_id for chunk in chunks})
        sources = list(db.scalars(select(KnowledgeSource).where(KnowledgeSource.source_id.in_(source_ids))).all())
        source_names = {source.source_id: source.source_name for source in sources}
        for index, chunk_id in enumerate(chunk_ids):
            chunk = chunk_map.get(chunk_id)
            if not chunk:
                continue
            retrieved_items.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "source_id": chunk.source_id,
                    "source_name": source_names.get(chunk.source_id),
                    "score": scores[index] if index < len(scores) else None,
                    "chunk_text": chunk.chunk_text,
                    "metadata": chunk.metadata_json,
                }
            )

    return {
        "generation_id": record.generation_id,
        "user_id": record.user_id,
        "retrieval_id": record.retrieval_id,
        "knowledge_base_id": retrieval.knowledge_base_id if retrieval else None,
        "top_k": retrieval.top_k if retrieval else None,
        "score_threshold": (record.prompt_variables_json or {}).get("score_threshold") if record.prompt_variables_json else None,
        "generation_mode": (record.prompt_variables_json or {}).get("generation_mode") if record.prompt_variables_json else None,
        "prompt_variables_json": record.prompt_variables_json,
        "requirement_text": record.requirement_text,
        "model_provider": record.model_provider,
        "model_name": record.model_name,
        "prompt_template_version": record.prompt_template_version,
        "used_chunk_ids": record.used_chunk_ids,
        "generated_json": record.generated_json,
        "case_set_id": record.case_set_id,
        "generation_status": record.generation_status,
        "error_message": record.error_message,
        "created_at": record.created_at,
        "retrieved_items": retrieved_items,
    }


def normalize_generation_mode(mode: str | None) -> str:
    return mode if mode in GENERATION_MODE_GUIDES else "comprehensive"


def build_user_prompt(requirement_text: str, retrieved_items: list[dict], generation_mode: str = "comprehensive") -> str:
    mode = normalize_generation_mode(generation_mode)
    mode_guide = GENERATION_MODE_GUIDES[mode]
    context_text = "\n\n".join(
        f"【知识片段{i}】\n{item['chunk_text']}" for i, item in enumerate(retrieved_items, start=1)
    )
    return f"""
请根据下面的RAG知识库上下文和用户测试需求，生成硬件测试用例思维导图结构。

【RAG知识库上下文】
{context_text}

【用户测试需求】
{requirement_text}

【生成侧重点】
{mode_guide}

【输出JSON格式示例】
{{
  "case_set_name": "摄像头夜视功能测试用例集",
  "nodes": [
    {{
      "title": "夜视功能测试",
      "node_type": "folder",
      "priority": "P1",
      "precondition": null,
      "test_steps": null,
      "expected_result": null,
      "children": [
        {{
          "title": "红外灯自动开启测试",
          "node_type": "case",
          "priority": "P0",
          "precondition": "设备处于低照度环境，摄像头已正常上电。",
          "test_steps": "1. 将设备置于暗光环境；2. 启动摄像头；3. 观察红外灯状态。",
          "expected_result": "红外灯自动开启，夜视画面清晰稳定。",
          "children": []
        }}
      ]
    }}
  ]
}}

请只输出合法JSON。
""".strip()


def call_deepseek(user_prompt: str) -> str:
    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY未配置")

    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2500,
    }

    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            response_json = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ValueError(f"DeepSeek接口请求失败：HTTP {error.code}") from error
    except (urllib.error.URLError, TimeoutError, socket.timeout) as error:
        raise ValueError("DeepSeek接口请求超时或网络不可用") from error

    return response_json["choices"][0]["message"]["content"]


def parse_generated_json(generated_text: str) -> dict:
    clean_text = generated_text.strip()
    clean_text = clean_text.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(clean_text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", clean_text)
        if not match:
            raise ValueError("大模型输出不是合法JSON")
        parsed = json.loads(match.group(0))

    if "case_set_name" not in parsed or "nodes" not in parsed:
        raise ValueError("大模型JSON缺少case_set_name或nodes字段")
    if not isinstance(parsed["nodes"], list):
        raise ValueError("nodes字段必须是数组")
    return normalize_generated_json(parsed)


def normalize_generated_json(parsed: dict) -> dict:
    """规范化并校验大模型返回的用例树，避免脏结构入库。"""
    case_set_name = str(parsed.get("case_set_name") or "AI生成用例集").strip()[:200] or "AI生成用例集"
    counter = {"count": 0}
    nodes = normalize_generated_nodes(parsed.get("nodes") or [], 1, counter)
    if not nodes:
        raise ValueError("AI生成结果没有可用节点")
    return {
        "case_set_name": case_set_name,
        "nodes": nodes,
        "quality_warnings": build_quality_warnings(nodes),
    }


def normalize_generated_nodes(nodes: list, depth: int, counter: dict) -> list[dict]:
    if not isinstance(nodes, list):
        raise ValueError("children字段必须是数组")
    if depth > MAX_GENERATED_TREE_DEPTH:
        if nodes:
            raise ValueError(f"AI生成结果层级过深，最多支持{MAX_GENERATED_TREE_DEPTH}层")
        return []

    result = []
    for index, node_data in enumerate(nodes, start=1):
        if not isinstance(node_data, dict):
            raise ValueError("nodes中存在非对象节点")
        counter["count"] += 1
        if counter["count"] > MAX_GENERATED_NODE_COUNT:
            raise ValueError(f"AI生成节点过多，最多支持{MAX_GENERATED_NODE_COUNT}个节点")

        children = normalize_generated_nodes(node_data.get("children") or [], depth + 1, counter)
        raw_node_type = node_data.get("node_type")
        node_type = raw_node_type if raw_node_type in VALID_NODE_TYPES else ("folder" if children else "case")
        priority = node_data.get("priority") if node_data.get("priority") in VALID_PRIORITIES else "P1"
        title = str(node_data.get("title") or f"未命名节点{index}").strip()[:300] or f"未命名节点{index}"

        precondition = clean_optional_text(node_data.get("precondition"))
        test_steps = clean_optional_text(node_data.get("test_steps"))
        expected_result = clean_optional_text(node_data.get("expected_result"))
        if node_type == "case":
            test_steps = test_steps or "待人工补充测试步骤"
            expected_result = expected_result or "待人工补充预期结果"

        result.append(
            {
                "title": title,
                "node_type": node_type,
                "priority": priority,
                "precondition": precondition,
                "test_steps": test_steps,
                "expected_result": expected_result,
                "children": children,
            }
        )
    return result


def clean_optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_quality_warnings(nodes: list[dict]) -> list[str]:
    warnings = []
    stats = {"case_count": 0, "placeholder_count": 0}

    def walk(items: list[dict]) -> None:
        for item in items:
            if item["node_type"] == "case":
                stats["case_count"] += 1
                if item.get("test_steps", "").startswith("待人工补充") or item.get("expected_result", "").startswith("待人工补充"):
                    stats["placeholder_count"] += 1
            walk(item.get("children") or [])

    walk(nodes)
    if stats["case_count"] == 0:
        warnings.append("生成结果未包含测试用例节点，请人工检查目录结构")
    if stats["placeholder_count"]:
        warnings.append(f"{stats['placeholder_count']}条用例缺少步骤或预期，已标记为待人工补充")
    return warnings


def save_generated_case_set(db: Session, generated_json: dict, created_by: int) -> int:
    case_set = TestCaseSet(
        name=str(generated_json["case_set_name"])[:200],
        description="由AI基于RAG知识库自动生成，待人工审阅后发布",
        source_type="ai_generated",
        status="draft",
        created_by=created_by,
    )
    db.add(case_set)
    db.flush()

    for index, node_data in enumerate(generated_json["nodes"], start=1):
        save_generated_node(
            db=db,
            case_set_id=case_set.case_set_id,
            parent_id=None,
            node_data=node_data,
            created_by=created_by,
            sort_order=index,
        )

    return case_set.case_set_id


def save_generated_node(
    db: Session,
    case_set_id: int,
    parent_id: int | None,
    node_data: dict,
    created_by: int,
    sort_order: int,
) -> None:
    children = node_data.get("children") or []
    node_type = node_data.get("node_type") or ("folder" if children else "case")
    if node_type not in {"folder", "case"}:
        node_type = "case"

    priority = node_data.get("priority") or "P1"
    if priority not in {"P0", "P1", "P2", "P3"}:
        priority = "P1"

    node = TestCaseNode(
        case_set_id=case_set_id,
        parent_id=parent_id,
        node_type=node_type,
        title=str(node_data.get("title") or "未命名用例")[:300],
        precondition=node_data.get("precondition"),
        test_steps=node_data.get("test_steps"),
        expected_result=node_data.get("expected_result"),
        priority=priority,
        sort_order=sort_order,
        created_by=created_by,
    )
    db.add(node)
    db.flush()
    create_node_version(db, node, operation_type="create", operator_id=created_by, change_note="AI生成创建节点")

    for index, child in enumerate(children, start=1):
        save_generated_node(db, case_set_id, node.node_id, child, created_by, index)
