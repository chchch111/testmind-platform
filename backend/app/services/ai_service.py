import json
import re
import urllib.error
import urllib.request

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai import AiGenerationRecord, RagRetrievalRecord
from app.models.case import TestCaseNode, TestCaseSet
from app.models.knowledge import FaissIndex
from app.schemas.ai import AiGenerateRequest
from app.schemas.rag import RagSearchRequest
from app.services.case_service import create_node_version, ensure_user_exists
from app.services.rag_service import search_knowledge_base


PROMPT_TEMPLATE_VERSION = "v1"


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


def generate_test_cases(db: Session, data: AiGenerateRequest) -> dict:
    ensure_user_exists(db, data.created_by)

    search_result = search_knowledge_base(
        db,
        data.knowledge_base_id,
        RagSearchRequest(query_text=data.requirement_text, top_k=data.top_k),
    )
    retrieved_items = search_result["items"]
    if not retrieved_items:
        raise HTTPException(status_code=400, detail="RAG没有检索到可用上下文，请先补充知识库资料")

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
    }
    user_prompt = build_user_prompt(data.requirement_text, retrieved_items)

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
        generated_text = call_deepseek(user_prompt)
        generated_json = parse_generated_json(generated_text)
        case_set_id = save_generated_case_set(db, generated_json, data.created_by) if data.save_to_case_set else None

        generation_record.generated_text = generated_text
        generation_record.generated_json = generated_json
        generation_record.case_set_id = case_set_id
        generation_record.generation_status = "success"
        db.commit()
        db.refresh(generation_record)

        return {
            "generation_id": generation_record.generation_id,
            "retrieval_id": retrieval_record.retrieval_id,
            "case_set_id": case_set_id,
            "generated_json": generated_json,
            "generated_text": generated_text,
        }
    except Exception as error:
        generation_record.generated_text = generation_record.generated_text or ""
        generation_record.generation_status = "failed"
        generation_record.error_message = str(error)
        db.commit()
        raise HTTPException(status_code=500, detail=f"AI生成失败：{error}") from error


def list_generation_records(db: Session) -> list[AiGenerationRecord]:
    statement = select(AiGenerationRecord).order_by(AiGenerationRecord.generation_id.desc()).limit(50)
    return list(db.scalars(statement).all())


def build_user_prompt(requirement_text: str, retrieved_items: list[dict]) -> str:
    context_text = "\n\n".join(
        f"【知识片段{i}】\n{item['chunk_text']}" for i, item in enumerate(retrieved_items, start=1)
    )
    return f"""
请根据下面的RAG知识库上下文和用户测试需求，生成硬件测试用例思维导图结构。

【RAG知识库上下文】
{context_text}

【用户测试需求】
{requirement_text}

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
        error_body = error.read().decode("utf-8", errors="replace")
        raise ValueError(f"DeepSeek接口请求失败：HTTP {error.code} {error_body}") from error

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
    return parsed


def save_generated_case_set(db: Session, generated_json: dict, created_by: int) -> int:
    case_set = TestCaseSet(
        name=str(generated_json["case_set_name"])[:200],
        description="由AI基于RAG知识库自动生成",
        source_type="ai_generated",
        status="active",
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
