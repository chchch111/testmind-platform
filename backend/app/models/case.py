from sqlalchemy import BigInteger, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class TestCaseSet(Base):
    __tablename__ = "test_case_sets"

    case_set_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    is_deleted: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class TestCaseNode(Base):
    __tablename__ = "test_case_nodes"

    node_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_set_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_case_sets.case_set_id"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("test_case_nodes.node_id"))
    import_batch_id: Mapped[int | None] = mapped_column(BigInteger)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False, default="folder")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    precondition: Mapped[str | None] = mapped_column(Text)
    test_steps: Mapped[str | None] = mapped_column(Text)
    expected_result: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="P1")
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    is_deleted: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class TestCaseNodeVersion(Base):
    __tablename__ = "test_case_node_versions"

    version_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_case_nodes.node_id"), nullable=False)
    version_no: Mapped[int] = mapped_column(nullable=False)
    operation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="update")
    change_note: Mapped[str | None] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    precondition: Mapped[str | None] = mapped_column(Text)
    test_steps: Mapped[str | None] = mapped_column(Text)
    expected_result: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="P1")
    snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    rollback_from_version_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("test_case_node_versions.version_id"))
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
