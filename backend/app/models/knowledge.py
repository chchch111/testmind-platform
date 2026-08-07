from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    product_type: Mapped[str | None] = mapped_column(String(100))
    hardware_module: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    is_deleted: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class FaissIndex(Base):
    __tablename__ = "faiss_indexes"

    faiss_index_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("knowledge_bases.knowledge_base_id"), nullable=False)
    index_name: Mapped[str] = mapped_column(String(100), nullable=False)
    index_dir: Mapped[str] = mapped_column(String(500), nullable=False)
    index_file_path: Mapped[str | None] = mapped_column(String(500))
    docstore_file_path: Mapped[str | None] = mapped_column(String(500))
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, default="bge-small-zh")
    vector_dimension: Mapped[int] = mapped_column(nullable=False, default=512)
    chunk_count: Mapped[int] = mapped_column(nullable=False, default=0)
    vector_count: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    source_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("knowledge_bases.knowledge_base_id"), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(500))
    storage_type: Mapped[str] = mapped_column(String(30), nullable=False, default="local")
    storage_key: Mapped[str | None] = mapped_column(String(500))
    content_text: Mapped[str | None] = mapped_column(Text)
    case_set_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("test_case_sets.case_set_id"))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    is_deleted: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    chunk_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chunk_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    source_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("knowledge_sources.source_id"), nullable=False)
    faiss_index_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("faiss_indexes.faiss_index_id"), nullable=False)
    chunk_no: Mapped[int] = mapped_column(nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str | None] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, default="bge-small-zh")
    faiss_doc_id: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    is_deleted: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
