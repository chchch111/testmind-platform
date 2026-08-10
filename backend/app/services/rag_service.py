from pathlib import Path
import hashlib
import io
import json
import os
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge import FaissIndex, KnowledgeBase, KnowledgeChunk, KnowledgeSource
from app.models.case import TestCaseNode, TestCaseSet
from app.schemas.rag import KnowledgeBaseCreate, ManualSourceCreate, RagSearchRequest
from app.services.case_service import ensure_user_exists


_embedding_model = None
_faiss_resource_cache = {}


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


def list_knowledge_bases(db: Session) -> list[KnowledgeBase]:
    statement = (
        select(KnowledgeBase)
        .where(KnowledgeBase.is_deleted == 0)
        .order_by(KnowledgeBase.knowledge_base_id.desc())
    )
    return list(db.scalars(statement).all())


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


def build_faiss_index(db: Session, knowledge_base_id: int, operator_id: int) -> dict:
    ensure_user_exists(db, operator_id)
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

    faiss_index = get_or_create_faiss_index(db, knowledge_base)
    mark_old_chunks_deleted(db, faiss_index.faiss_index_id)

    chunks = split_sources_to_chunks(sources)
    if not chunks:
        raise HTTPException(status_code=400, detail="知识来源切片结果为空")

    texts = [item["chunk_text"] for item in chunks]
    embeddings = encode_texts(texts)

    try:
        import faiss
        import numpy as np
    except ImportError as error:
        raise HTTPException(status_code=500, detail="缺少FAISS或NumPy依赖，请先安装faiss-cpu和numpy") from error

    vectors = np.asarray(embeddings, dtype="float32")
    vector_dimension = int(vectors.shape[1])
    index = faiss.IndexFlatIP(vector_dimension)
    index.add(vectors)

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
    for score, position in zip(scores[0], positions[0]):
        if position < 0 or position >= len(doc_ids):
            continue
        chunk_id = doc_ids[position]["chunk_id"]
        chunk = db.get(KnowledgeChunk, chunk_id)
        if not chunk or chunk.is_deleted == 1:
            continue
        items.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_id": chunk.source_id,
                "score": float(score),
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


def get_active_knowledge_base(db: Session, knowledge_base_id: int) -> KnowledgeBase:
    knowledge_base = db.get(KnowledgeBase, knowledge_base_id)
    if not knowledge_base or knowledge_base.is_deleted == 1 or knowledge_base.status != "active":
        raise HTTPException(status_code=404, detail="知识库不存在或已停用")
    return knowledge_base


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
