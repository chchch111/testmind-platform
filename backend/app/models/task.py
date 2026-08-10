from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class TestTask(Base):
    __tablename__ = "test_tasks"

    task_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    start_time: Mapped[DateTime | None] = mapped_column(DateTime)
    end_time: Mapped[DateTime | None] = mapped_column(DateTime)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    is_deleted: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class TestTaskCaseSet(Base):
    __tablename__ = "test_task_case_sets"

    task_case_set_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_tasks.task_id"), nullable=False)
    case_set_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_case_sets.case_set_id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class TestTaskAssignee(Base):
    __tablename__ = "test_task_assignees"

    task_assignee_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_tasks.task_id"), nullable=False)
    assignee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    assign_status: Mapped[str] = mapped_column(String(30), nullable=False, default="assigned")
    assigned_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class TestExecutionRecord(Base):
    __tablename__ = "test_execution_records"

    execution_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_tasks.task_id"), nullable=False)
    case_node_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_case_nodes.node_id"), nullable=False)
    executor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_run")
    actual_result: Mapped[str | None] = mapped_column(Text)
    bug_description: Mapped[str | None] = mapped_column(Text)
    case_node_snapshot: Mapped[dict | None] = mapped_column(JSON)
    sync_status: Mapped[str] = mapped_column(String(30), nullable=False, default="synced")
    sync_version: Mapped[int] = mapped_column(nullable=False, default=1)
    executed_at: Mapped[DateTime | None] = mapped_column(DateTime)
    synced_at: Mapped[DateTime | None] = mapped_column(DateTime)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
