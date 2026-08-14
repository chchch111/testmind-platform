from pathlib import Path
import hashlib
import io
import json
import os
import threading
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.knowledge import FaissIndex, KnowledgeBase, KnowledgeChunk, KnowledgeSource
from app.models.case import TestCaseNode, TestCaseSet
from app.schemas.rag import KnowledgeBaseCreate, KnowledgeBaseUpdate, ManualSourceCreate, RagSearchRequest
from app.services.case_service import ensure_user_exists


_embedding_model = None
_faiss_resource_cache = {}
_build_tasks: dict[str, dict] = {}


def create_knowledge_base(db: Session, data: KnowledgeBaseCreate) -> KnowledgeBase:
    ensure_user_exists(db, data.created_by)
    knowledge_base = KnowledgeBase(
        name=data.name,
        description=data.description,
        product_type=data.product_type,
        hardware_module=data.hardware_module,
        status="active",
        created_by=data.created_by,
    )
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def list_knowledge_bases(db: Session) -> list[dict]:
    statement = (
        select(KnowledgeBase)
        .where(KnowledgeBase.is_deleted == 0)
        .order_by(KnowledgeBase.knowledge_base_id.desc())
    )
    knowledge_bases = list(db.scalars(statement).all())
    if not knowledge_bases:
        return []

    knowledge_base_ids = [item.knowledge_base_id for item in knowledge_bases]

    source_counts = dict(
        db.execute(
            select(KnowledgeSource.knowledge_base_id, func.count(KnowledgeSource.source_id))
            .where(
                KnowledgeSource.knowledge_base_id.in_(knowledge_base_ids),
                KnowledgeSource.is_deleted == 0,
            )
            .group_by(KnowledgeSource.knowledge_base_id)
        ).all()
    )

    faiss_indexes = list(
        db.scalars(
            select(FaissIndex).where(FaissIndex.knowledge_base_id.in_(knowledge_base_ids))
        ).all()
    )
    index_status_map: dict[int, str] = {}
    index_chunk_map: dict[int, int] = {}
    for faiss_index in faiss_indexes:
        index_status_map[faiss_index.knowledge_base_id] = faiss_index.status
        index_chunk_map[faiss_index.knowledge_base_id] = faiss_index.chunk_count

    result = []
    for knowledge_base in knowledge_bases:
        result.append(
            {
                "knowledge_base_id": knowledge_base.knowledge_base_id,
                "name": knowledge_base.name,
                "description": knowledge_base.description,
                "product_type": knowledge_base.product_type,
                "hardware_module": knowledge_base.hardware_module,
                "status": knowledge_base.status,
                "created_by": knowledge_base.created_by,
                "updated_by": knowledge_base.updated_by,
                "created_at": knowledge_base.created_at,
                "updated_at": knowledge_base.updated_at,
                "source_count": source_counts.get(knowledge_base.knowledge_base_id, 0),
                "chunk_count": index_chunk_map.get(knowledge_base.knowledge_base_id, 0),
                "index_status": index_status_map.get(knowledge_base.knowledge_base_id, "none"),
            }
        )
    return result


def get_active_knowledge_base(db: Session, knowledge_base_id: int) -> KnowledgeBase:
    knowledge_base = db.get(KnowledgeBase, knowledge_base_id)
    if not knowledge_base or knowledge_base.is_deleted == 1 or knowledge_base.status != "active":
        raise HTTPException(status_code=404, detail="知识库不存在或已停用")
    return knowledge_base


def update_knowledge_base(db: Session, knowledge_base_id: int, data: KnowledgeBaseUpdate, operator_id: int) -> KnowledgeBase:
    ensure_user_exists(db, operator_id)
    knowledge_base = db.get(KnowledgeBase, knowledge_base_id)
    if not knowledge_base or knowledge_base.is_deleted == 1:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if data.name is not None and data.name.strip():
        knowledge_base.name = data.name.strip()
    if data.description is not None:
        knowledge_base.description = data.description.strip() if data.description.strip() else None
    if data.product_type is not None:
        knowledge_base.product_type = data.product_type.strip() if data.product_type.strip() else None
    if data.hardware_module is not None:
        knowledge_base.hardware_module = data.hardware_module.strip() if data.hardware_module.strip() else None
    if data.status is not None and data.status in ("active", "disabled"):
        knowledge_base.status = data.status
    knowledge_base.updated_by = operator_id

    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base


def delete_knowledge_base(db: Session, knowledge_base_id: int, operator_id: int) -> dict:
    ensure_user_exists(db, operator_id)
    knowledge_base = db.get(KnowledgeBase, knowledge_base_id)
    if not knowledge_base or knowledge_base.is_deleted == 1:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 软删来源与切片，物理删除 FAISS 索引文件。
    sources = list(
        db.scalars(
            select(KnowledgeSource).where(KnowledgeSource.knowledge_base_id == knowledge_base_id)
        ).all()
    )
    source_ids = [source.source_id for source in sources]
    if source_ids:
        chunks = list(
            db.scalars(
                select(KnowledgeChunk).where(KnowledgeChunk.source_id.in_(source_ids))
            ).all()
        )
        for chunk in chunks:
            chunk.is_deleted = 1
        for source in sources:
            source.is_deleted = 1
            source.status = "disabled"

    faiss_indexes = list(
        db.scalars(
            select(FaissIndex).where(FaissIndex.knowledge_base_id == knowledge_base_id)
        ).all()
    )
    for faiss_index in faiss_indexes:
        faiss_index.status = "deleted"
        clear_faiss_cache(faiss_index.faiss_index_id)
        index_dir = Path(faiss_index.index_dir or "") if faiss_index.index_dir else None
        if index_dir and index_dir.exists():
            import shutil
            shutil.rmtree(index_dir, ignore_errors=True)

    knowledge_base.is_deleted = 1
    knowledge_base.status = "disabled"
    knowledge_base.updated_by = operator_id
    db.commit()
    return {"message": "知识库已删除", "knowledge_base_id": knowledge_base_id}


def add_manual_source(db: Session, knowledge_base_id: int, data: ManualSourceCreate) -> KnowledgeSource:
    ensure_user_exists(db, data.created_by)
    knowledge_base = get_active_knowledge_base(db, knowledge_base_id)

    source = KnowledgeSource(
        knowledge_base_id=knowledge_base.knowledge_base_id,
        source_name=data.source_name,
        source_type=data.source_type,
        content_text=data.content_text,
        status="active",
        created_by=data.created_by,
    )
    db.add(source)
    mark_index_stale(db, knowledge_base_id)
    db.commit()
    db.refresh(source)
    return source


def list_knowledge_sources(db: Session, knowledge_base_id: int) -> list[KnowledgeSource]:
    get_active_knowledge_base(db, knowledge_base_id)
    statement = (
        select(KnowledgeSource)
        .where(
            KnowledgeSource.knowledge_base_id == knowledge_base_id,
            KnowledgeSource.is_deleted == 0,
        )
        .order_by(KnowledgeSource.source_id.asc())
    )
    return list(db.scalars(statement).all())


def delete_knowledge_source(db: Session, source_id: int, operator_id: int) -> dict:
    ensure_user_exists(db, operator_id)
    source = db.get(KnowledgeSource, source_id)
    if not source or source.is_deleted == 1:
        raise HTTPException(status_code=404, detail="知识来源不存在")
    source.is_deleted = 1
    source.status = "disabled"
    mark_index_stale(db, source.knowledge_base_id)
    db.commit()
    return {"message": "知识来源已删除", "source_id": source_id}


def upload_knowledge_source_file(db: Session, knowledge_base_id: int, file: UploadFile, created_by: int) -> KnowledgeSource:
    """上传 txt/md/xmind 文件作为知识来源，抽取纯文本后保存。"""
    ensure_user_exists(db, created_by)
    get_active_knowledge_base(db, knowledge_base_id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    lower_name = file.filename.lower()
    if not any(lower_name.endswith(ext) for ext in (".txt", ".md", ".xmind")):
        raise HTTPException(status_code=400, detail="只支持上传 .txt、.md 或 .xmind 文件")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(status_code=400, detail=f"文件过大，最大允许 {settings.max_upload_mb}MB")

    if lower_name.endswith(".xmind"):
        content_text = extract_xmind_text(file)
        source_type = "xmind_case"
    else:
        raw = file.file.read()
        try:
            content_text = raw.decode("utf-8")
        except UnicodeDecodeError:
            content_text = raw.decode("gbk", errors="ignore")
        source_type = "history_doc"

    if not content_text.strip():
        raise HTTPException(status_code=400, detail="文件中没有可用的文本内容")

    source = KnowledgeSource(
        knowledge_base_id=knowledge_base_id,
        source_name=file.filename,
        source_type=source_type,
        file_name=file.filename,
        content_text=content_text.strip(),
        status="active",
        created_by=created_by,
    )
    db.add(source)
    mark_index_stale(db, knowledge_base_id)
    db.commit()
    db.refresh(source)
    return source


def import_case_set_as_source(db: Session, knowledge_base_id: int, case_set_id: int, created_by: int) -> KnowledgeSource:
    """把已有用例集的树形节点文本导入为知识来源。"""
    ensure_user_exists(db, created_by)
    get_active_knowledge_base(db, knowledge_base_id)

    case_set = db.get(TestCaseSet, case_set_id)
    if not case_set or case_set.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例集不存在")

    nodes = list(
        db.scalars(
            select(TestCaseNode)
            .where(TestCaseNode.case_set_id == case_set_id, TestCaseNode.is_deleted == 0)
            .order_by(TestCaseNode.parent_id.asc(), TestCaseNode.sort_order.asc(), TestCaseNode.node_id.asc())
        ).all()
    )
    if not nodes:
        raise HTTPException(status_code=400, detail="用例集中没有可导入的节点")

    children_map: dict[int | None, list[TestCaseNode]] = {}
    for node in nodes:
        parent_id = node.parent_id if node.parent_id and any(n.node_id == node.parent_id for n in nodes) else None
        children_map.setdefault(parent_id, []).append(node)

    lines: list[str] = []
    for node in children_map.get(None, []):
        lines.append(format_node_text(node, children_map))

    content_text = "\n".join(line for line in lines if line.strip())
    if not content_text.strip():
        raise HTTPException(status_code=400, detail="用例集文本内容为空")

    source = KnowledgeSource(
        knowledge_base_id=knowledge_base_id,
        source_name=f"用例集#{case_set_id} {case_set.name}",
        source_type="xmind_case",
        case_set_id=case_set_id,
        content_text=content_text.strip(),
        status="active",
        created_by=created_by,
    )
    db.add(source)
    mark_index_stale(db, knowledge_base_id)
    db.commit()
    db.refresh(source)
    return source


def format_node_text(node: TestCaseNode, children_map: dict[int | None, list[TestCaseNode]], depth: int = 0) -> str:
    prefix = "  " * depth
    lines = [f"{prefix}{node.title}"]
    if node.precondition:
        lines.append(f"{prefix}前置条件：{node.precondition}")
    if node.test_steps:
        lines.append(f"{prefix}测试步骤：{node.test_steps}")
    if node.expected_result:
        lines.append(f"{prefix}预期结果：{node.expected_result}")
    for child in children_map.get(node.node_id, []):
        lines.append(format_node_text(child, children_map, depth + 1))
    return "\n".join(lines)


def extract_xmind_text(file: UploadFile) -> str:
    """解析新版 .xmind 的 content.json，把主题标题和备注抽取为纯文本。"""
    import zipfile

    saved_bytes = file.file.read()
    try:
        with zipfile.ZipFile(io.BytesIO(saved_bytes), "r") as xmind_zip:
            if "content.json" not in xmind_zip.namelist():
                raise ValueError("当前仅支持包含content.json的新版XMind文件")
            content_text = xmind_zip.read("content.json").decode("utf-8")
    except zipfile.BadZipFile as error:
        raise HTTPException(status_code=400, detail="上传文件不是有效的XMind压缩包") from error

    try:
        content = json.loads(content_text)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="XMind的content.json解析失败") from error

    if not isinstance(content, list) or not content:
        raise HTTPException(status_code=400, detail="XMind的content.json结构为空")

    root_topic = content[0].get("rootTopic")
    if not root_topic:
        raise HTTPException(status_code=400, detail="XMind的content.json中缺少rootTopic")

    lines: list[str] = []
    collect_xmind_topic_text(root_topic, lines, 0)
    return "\n".join(line for line in lines if line.strip())


def collect_xmind_topic_text(topic: dict, lines: list[str], depth: int) -> None:
    prefix = "  " * depth
    title = str(topic.get("title") or "未命名节点").strip()
    if title:
        lines.append(f"{prefix}{title}")
    notes = topic.get("notes")
    if isinstance(notes, dict):
        plain = notes.get("plain")
        if isinstance(plain, dict) and plain.get("content"):
            lines.append(f"{prefix}备注：{plain['content']}")
    children = topic.get("children") or {}
    attached = children.get("attached") if isinstance(children, dict) else None
    if isinstance(attached, list):
        for child in attached:
            collect_xmind_topic_text(child, lines, depth + 1)


def build_faiss_index(db: Session, knowledge_base_id: int, operator_id: int, progress_callback=None) -> dict:
    ensure_user_exists(db, operator_id)
    if progress_callback:
        progress_callback(5, "准备构建", "正在读取知识来源...")
    knowledge_base = get_active_knowledge_base(db, knowledge_base_id)

    sources = list(
        db.scalars(
            select(KnowledgeSource).where(
                KnowledgeSource.knowledge_base_id == knowledge_base_id,
                KnowledgeSource.status == "active",
                KnowledgeSource.is_deleted == 0,
            )
        ).all()
    )
    if not sources:
        raise HTTPException(status_code=400, detail="知识库中没有可用知识来源")
    if progress_callback:
        progress_callback(15, "读取来源", f"已读取 {len(sources)} 个知识来源")

    faiss_index = get_or_create_faiss_index(db, knowledge_base)
    mark_old_chunks_deleted(db, faiss_index.faiss_index_id)

    chunks = split_sources_to_chunks(sources)
    if not chunks:
        raise HTTPException(status_code=400, detail="知识来源切片结果为空")
    if progress_callback:
        progress_callback(25, "文本切片", f"共切分 {len(chunks)} 个片段")

    try:
        import faiss
        import numpy as np
    except ImportError as error:
        raise HTTPException(status_code=500, detail="缺少FAISS或NumPy依赖，请先安装faiss-cpu和numpy") from error

    # 分批向量化，按批更新真实进度（30% ~ 85%）。
    embedding_batch_size = 32
    embeddings = []
    total_chunks = len(chunks)
    for start in range(0, total_chunks, embedding_batch_size):
        batch = chunks[start:start + embedding_batch_size]
        batch_texts = [item["chunk_text"] for item in batch]
        batch_embeddings = encode_texts(batch_texts)
        embeddings.append(batch_embeddings)
        if progress_callback:
            done = min(start + embedding_batch_size, total_chunks)
            progress = 30 + int((done / total_chunks) * 55)
            progress_callback(progress, "生成向量", f"已向量化 {done}/{total_chunks} 个片段")
    import numpy as np
    vectors = np.asarray(
        np.vstack(embeddings) if embeddings else np.empty((0, 0), dtype="float32"),
        dtype="float32",
    )
    vector_dimension = int(vectors.shape[1])
    index = faiss.IndexFlatIP(vector_dimension)
    index.add(vectors)
    if progress_callback:
        progress_callback(90, "写入索引", "正在写入 FAISS 索引文件...")

    index_dir = Path(settings.faiss_root) / f"kb_{knowledge_base_id}" / "main"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_file_path = index_dir / "index.faiss"
    docstore_file_path = index_dir / "docstore.json"

    chunk_rows = []
    doc_ids = []
    for item in chunks:
        chunk_uuid = str(uuid.uuid4())
        chunk_hash = hashlib.sha256(item["chunk_text"].encode("utf-8")).hexdigest()
        chunk = KnowledgeChunk(
            chunk_uuid=chunk_uuid,
            source_id=item["source_id"],
            faiss_index_id=faiss_index.faiss_index_id,
            chunk_no=item["chunk_no"],
            chunk_text=item["chunk_text"],
            chunk_hash=chunk_hash,
            embedding_model=settings.embedding_model_name,
            faiss_doc_id=chunk_uuid,
            metadata_json=item["metadata"],
        )
        db.add(chunk)
        chunk_rows.append(chunk)
        doc_ids.append({"chunk_id": None, "chunk_uuid": chunk_uuid})

    # 一次 flush 让所有 chunk 拿到自增主键，避免逐个 flush 造成过多往返。
    db.flush()
    for row_index, chunk in enumerate(chunk_rows):
        doc_ids[row_index]["chunk_id"] = chunk.chunk_id

    faiss.write_index(index, str(index_file_path))
    docstore_file_path.write_text(json.dumps({"doc_ids": doc_ids}, ensure_ascii=False, indent=2), encoding="utf-8")

    faiss_index.index_dir = str(index_dir)
    faiss_index.index_file_path = str(index_file_path)
    faiss_index.docstore_file_path = str(docstore_file_path)
    faiss_index.embedding_model = settings.embedding_model_name
    faiss_index.vector_dimension = vector_dimension
    faiss_index.chunk_count = len(chunk_rows)
    faiss_index.vector_count = len(chunk_rows)
    faiss_index.status = "active"

    db.commit()
    clear_faiss_cache(faiss_index.faiss_index_id)
    if progress_callback:
        progress_callback(100, "完成", "FAISS 索引构建成功")

    return {
        "faiss_index_id": faiss_index.faiss_index_id,
        "knowledge_base_id": knowledge_base_id,
        "index_name": faiss_index.index_name,
        "index_file_path": str(index_file_path),
        "docstore_file_path": str(docstore_file_path),
        "chunk_count": len(chunk_rows),
        "vector_count": len(chunk_rows),
        "vector_dimension": vector_dimension,
        "message": "FAISS索引构建成功",
    }


def _run_build_task(task_id: str, knowledge_base_id: int, operator_id: int) -> None:
    """后台线程执行索引构建，更新内存中的进度状态。"""
    def progress_callback(progress: int, stage: str, detail: str) -> None:
        _build_tasks[task_id] = {
            "status": "running",
            "progress": progress,
            "stage": stage,
            "detail": detail,
        }

    try:
        _build_tasks[task_id] = {"status": "running", "progress": 0, "stage": "开始", "detail": "任务已启动"}
        db = SessionLocal()
        try:
            result = build_faiss_index(db, knowledge_base_id, operator_id, progress_callback)
        finally:
            db.close()
        _build_tasks[task_id] = {
            "status": "success",
            "progress": 100,
            "stage": "完成",
            "detail": "FAISS索引构建成功",
            "result": result,
        }
    except HTTPException as error:
        _build_tasks[task_id] = {"status": "error", "progress": _build_tasks.get(task_id, {}).get("progress", 0), "stage": "失败", "detail": str(error.detail)}
    except Exception as error:
        _build_tasks[task_id] = {"status": "error", "progress": _build_tasks.get(task_id, {}).get("progress", 0), "stage": "失败", "detail": f"构建失败：{error}"}


def start_build_faiss_index(knowledge_base_id: int, operator_id: int) -> dict:
    """启动异步索引构建任务，立即返回 task_id。"""
    task_id = str(uuid.uuid4())
    _build_tasks[task_id] = {"status": "pending", "progress": 0, "stage": "等待", "detail": "任务排队中"}
    thread = threading.Thread(target=_run_build_task, args=(task_id, knowledge_base_id, operator_id), daemon=True)
    thread.start()
    return {"task_id": task_id, "status": "running", "knowledge_base_id": knowledge_base_id}


def get_build_progress(task_id: str) -> dict:
    task = _build_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="构建任务不存在")
    return task


def search_knowledge_base(db: Session, knowledge_base_id: int, data: RagSearchRequest) -> dict:
    get_active_knowledge_base(db, knowledge_base_id)
    faiss_index = db.scalar(
        select(FaissIndex).where(
            FaissIndex.knowledge_base_id == knowledge_base_id,
            FaissIndex.index_name == "main",
            FaissIndex.status == "active",
        )
    )
    if not faiss_index or not faiss_index.index_file_path or not faiss_index.docstore_file_path:
        raise HTTPException(status_code=400, detail="当前知识库还没有可用FAISS索引，请先构建索引")

    try:
        import faiss
        import numpy as np
    except ImportError as error:
        raise HTTPException(status_code=500, detail="缺少FAISS或NumPy依赖，请先安装faiss-cpu和numpy") from error

    index, doc_ids = load_cached_faiss_resources(faiss_index)

    query_vector = np.asarray(encode_texts([data.query_text]), dtype="float32")
    top_k = min(data.top_k, index.ntotal)
    scores, positions = index.search(query_vector, top_k)

    items = []
    chunks = []
    for score, position in zip(scores[0], positions[0]):
        if position < 0 or position >= len(doc_ids):
            continue
        chunk_id = doc_ids[position]["chunk_id"]
        chunk = db.get(KnowledgeChunk, chunk_id)
        if not chunk or chunk.is_deleted == 1:
            continue
        chunks.append((chunk, float(score)))

    source_names = {}
    if chunks:
        source_ids = list({chunk.source_id for chunk, _ in chunks})
        sources = list(
            db.scalars(select(KnowledgeSource).where(KnowledgeSource.source_id.in_(source_ids))).all()
        )
        source_names = {source.source_id: source.source_name for source in sources}

    for chunk, score in chunks:
        if data.score_threshold is not None and score < data.score_threshold:
            continue
        items.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_id": chunk.source_id,
                "source_name": source_names.get(chunk.source_id),
                "score": score,
                "chunk_text": chunk.chunk_text,
                "metadata": chunk.metadata_json,
            }
        )

    return {
        "knowledge_base_id": knowledge_base_id,
        "faiss_index_id": faiss_index.faiss_index_id,
        "query_text": data.query_text,
        "items": items,
    }


def list_knowledge_chunks(db: Session, knowledge_base_id: int) -> list[dict]:
    get_active_knowledge_base(db, knowledge_base_id)
    faiss_index = db.scalar(
        select(FaissIndex).where(
            FaissIndex.knowledge_base_id == knowledge_base_id,
            FaissIndex.index_name == "main",
            FaissIndex.status == "active",
        )
    )
    if not faiss_index:
        return []

    chunks = list(
        db.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.faiss_index_id == faiss_index.faiss_index_id, KnowledgeChunk.is_deleted == 0)
            .order_by(KnowledgeChunk.source_id.asc(), KnowledgeChunk.chunk_no.asc(), KnowledgeChunk.chunk_id.asc())
        ).all()
    )
    if not chunks:
        return []

    source_ids = list({chunk.source_id for chunk in chunks})
    sources = list(db.scalars(select(KnowledgeSource).where(KnowledgeSource.source_id.in_(source_ids))).all())
    source_map = {source.source_id: source for source in sources}
    return [
        {
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "source_name": source_map.get(chunk.source_id).source_name if source_map.get(chunk.source_id) else None,
            "source_type": source_map.get(chunk.source_id).source_type if source_map.get(chunk.source_id) else None,
            "chunk_no": chunk.chunk_no,
            "chunk_text": chunk.chunk_text,
            "chunk_length": len(chunk.chunk_text or ""),
            "metadata": chunk.metadata_json,
            "created_at": chunk.created_at,
        }
        for chunk in chunks
    ]


def load_cached_faiss_resources(faiss_index: FaissIndex):
    index_path = Path(faiss_index.index_file_path or "")
    docstore_path = Path(faiss_index.docstore_file_path or "")
    if not index_path.exists():
        raise HTTPException(status_code=400, detail="FAISS索引文件不存在，请重新构建索引")
    if not docstore_path.exists():
        raise HTTPException(status_code=400, detail="FAISS文档映射文件不存在，请重新构建索引")

    index_mtime = index_path.stat().st_mtime
    docstore_mtime = docstore_path.stat().st_mtime
    cache_key = faiss_index.faiss_index_id
    cached = _faiss_resource_cache.get(cache_key)
    if cached and cached["index_path"] == str(index_path) and cached["docstore_path"] == str(docstore_path) and cached["index_mtime"] == index_mtime and cached["docstore_mtime"] == docstore_mtime:
        return cached["index"], cached["doc_ids"]

    try:
        import faiss
        index = faiss.read_index(str(index_path))
    except Exception as error:
        raise HTTPException(status_code=400, detail="FAISS索引读取失败，请重新构建索引") from error

    try:
        docstore = json.loads(docstore_path.read_text(encoding="utf-8"))
        doc_ids = docstore.get("doc_ids", [])
    except Exception as error:
        raise HTTPException(status_code=400, detail="FAISS文档映射读取失败，请重新构建索引") from error

    _faiss_resource_cache[cache_key] = {
        "index_path": str(index_path),
        "docstore_path": str(docstore_path),
        "index_mtime": index_mtime,
        "docstore_mtime": docstore_mtime,
        "index": index,
        "doc_ids": doc_ids,
    }
    return index, doc_ids


def clear_faiss_cache(faiss_index_id: int | None = None) -> None:
    if faiss_index_id is None:
        _faiss_resource_cache.clear()
        return
    _faiss_resource_cache.pop(faiss_index_id, None)


def mark_index_stale(db: Session, knowledge_base_id: int) -> None:
    """知识来源变更后标记现有索引过期，提醒用户重新构建。"""
    faiss_indexes = list(
        db.scalars(
            select(FaissIndex).where(
                FaissIndex.knowledge_base_id == knowledge_base_id,
                FaissIndex.status == "active",
            )
        ).all()
    )
    for faiss_index in faiss_indexes:
        faiss_index.status = "stale"
        clear_faiss_cache(faiss_index.faiss_index_id)
    if faiss_indexes:
        db.flush()


def get_or_create_faiss_index(db: Session, knowledge_base: KnowledgeBase) -> FaissIndex:
    faiss_index = db.scalar(
        select(FaissIndex).where(
            FaissIndex.knowledge_base_id == knowledge_base.knowledge_base_id,
            FaissIndex.index_name == "main",
        )
    )
    if faiss_index:
        faiss_index.status = "rebuilding"
        db.flush()
        return faiss_index

    index_dir = Path(settings.faiss_root) / f"kb_{knowledge_base.knowledge_base_id}" / "main"
    faiss_index = FaissIndex(
        knowledge_base_id=knowledge_base.knowledge_base_id,
        index_name="main",
        index_dir=str(index_dir),
        embedding_model=settings.embedding_model_name,
        status="rebuilding",
    )
    db.add(faiss_index)
    db.flush()
    return faiss_index


def mark_old_chunks_deleted(db: Session, faiss_index_id: int) -> None:
    old_chunks = db.scalars(
        select(KnowledgeChunk).where(KnowledgeChunk.faiss_index_id == faiss_index_id, KnowledgeChunk.is_deleted == 0)
    ).all()
    for chunk in old_chunks:
        chunk.is_deleted = 1
    db.flush()


def split_sources_to_chunks(sources: list[KnowledgeSource]) -> list[dict]:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as error:
        raise HTTPException(status_code=500, detail="缺少LangChain切片依赖，请先安装langchain-text-splitters") from error

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],
    )

    chunks = []
    for source in sources:
        if not source.content_text:
            continue
        texts = splitter.split_text(source.content_text)
        for index, text in enumerate(texts, start=1):
            clean_text = text.strip()
            if not clean_text:
                continue
            chunks.append(
                {
                    "source_id": source.source_id,
                    "chunk_no": index,
                    "chunk_text": clean_text,
                    "metadata": {
                        "source_id": source.source_id,
                        "source_name": source.source_name,
                        "source_type": source.source_type,
                        "chunk_no": index,
                    },
                }
            )
    return chunks


def encode_texts(texts: list[str]):
    global _embedding_model

    os.environ.setdefault("HF_HOME", settings.hf_home_dir)
    os.environ.setdefault("TRANSFORMERS_CACHE", settings.hf_home_dir)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise HTTPException(status_code=500, detail="缺少Embedding依赖，请先安装sentence-transformers") from error

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.embedding_model_name)

    return _embedding_model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
