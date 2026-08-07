from pathlib import Path
import hashlib
import json
import os
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge import FaissIndex, KnowledgeBase, KnowledgeChunk, KnowledgeSource
from app.schemas.rag import KnowledgeBaseCreate, ManualSourceCreate, RagSearchRequest
from app.services.case_service import ensure_user_exists


_embedding_model = None


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

    index_dir = Path(settings.faiss_root_dir) / f"kb_{knowledge_base_id}" / "main"
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
        db.flush()
        chunk_rows.append(chunk)
        doc_ids.append({"chunk_id": chunk.chunk_id, "chunk_uuid": chunk_uuid})

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

    index = faiss.read_index(faiss_index.index_file_path)
    docstore = json.loads(Path(faiss_index.docstore_file_path).read_text(encoding="utf-8"))
    doc_ids = docstore.get("doc_ids", [])

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

    index_dir = Path(settings.faiss_root_dir) / f"kb_{knowledge_base.knowledge_base_id}" / "main"
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

    os.environ.setdefault("HF_HOME", settings.hf_home)
    os.environ.setdefault("TRANSFORMERS_CACHE", settings.hf_home)

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
