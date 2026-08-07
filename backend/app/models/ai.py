from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class RagRetrievalRecord(Base):
    __tablename__ = "rag_retrieval_records"

    retrieval_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    knowledge_base_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("knowledge_bases.knowledge_base_id"), nullable=False)
    faiss_index_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("faiss_indexes.faiss_index_id"), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, default="bge-small-zh")
    top_k: Mapped[int] = mapped_column(nullable=False, default=5)
    retrieved_chunk_ids: Mapped[list | None] = mapped_column(JSON)
    retrieved_scores: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class AiGenerationRecord(Base):
    __tablename__ = "ai_generation_records"

    generation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    retrieval_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("rag_retrieval_records.retrieval_id"))
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="DeepSeek")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="deepseek-v4-flash")
    prompt_template_version: Mapped[str | None] = mapped_column(String(50))
    prompt_variables_json: Mapped[dict | None] = mapped_column(JSON)
    used_chunk_ids: Mapped[list | None] = mapped_column(JSON)
    generated_text: Mapped[str] = mapped_column(Text, nullable=False)
    generated_json: Mapped[dict | None] = mapped_column(JSON)
    case_set_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("test_case_sets.case_set_id"))
    generation_status: Mapped[str] = mapped_column(String(30), nullable=False, default="success")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
