from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class XMindFile(Base):
    __tablename__ = "xmind_files"

    xmind_file_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_set_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("test_case_sets.case_set_id"))
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_type: Mapped[str] = mapped_column(String(30), nullable=False, default="local")
    storage_key: Mapped[str | None] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    process_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    is_deleted: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class XMindImportBatch(Base):
    __tablename__ = "xmind_import_batches"

    import_batch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    xmind_file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("xmind_files.xmind_file_id"), nullable=False)
    case_set_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_case_sets.case_set_id"), nullable=False)
    node_count: Mapped[int] = mapped_column(nullable=False, default=0)
    import_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
