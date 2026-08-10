from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class CaseNodeMeta(Base):
    __tablename__ = "case_node_metas"

    meta_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_set_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_case_sets.case_set_id"), nullable=False)
    node_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_case_nodes.node_id"), nullable=False)
    meta_type: Mapped[str] = mapped_column(String(30), nullable=False)
    meta_key: Mapped[str | None] = mapped_column(String(50))
    meta_value: Mapped[dict | None] = mapped_column(JSON)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class CaseSetSnapshot(Base):
    __tablename__ = "case_set_snapshots"

    snapshot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_set_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_case_sets.case_set_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    data_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class CaseSetReview(Base):
    __tablename__ = "case_set_reviews"

    review_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    case_set_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_case_sets.case_set_id"), nullable=False)
    reviewer_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    due_at: Mapped[DateTime | None] = mapped_column(DateTime)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="submitted")
    conclusion: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
