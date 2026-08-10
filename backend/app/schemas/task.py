from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    task_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    case_set_ids: list[int] = Field(min_length=1)
    assignee_ids: list[int] = Field(min_length=1)
    start_time: datetime | None = None
    end_time: datetime | None = None
    created_by: int = 1


class TaskOut(BaseModel):
    task_id: int
    task_name: str
    description: str | None
    status: str
    start_time: datetime | None
    end_time: datetime | None
    created_by: int
    updated_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskDetailOut(TaskOut):
    case_set_ids: list[int]
    assignee_ids: list[int]
    total_executions: int
    passed_count: int
    failed_count: int
    blocked_count: int
    not_run_count: int


class TaskPageOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TaskOut]


class ExecutionOut(BaseModel):
    execution_id: int
    task_id: int
    case_node_id: int
    case_node_title: str | None = None
    case_node_priority: str | None = None
    case_node_snapshot: dict | None = None
    case_node_deleted: bool | None = None
    executor_id: int
    execution_status: str
    actual_result: str | None
    bug_description: str | None
    sync_status: str
    sync_version: int
    executed_at: datetime | None
    synced_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExecutionUpdate(BaseModel):
    executor_id: int
    execution_status: str
    actual_result: str | None = None
    bug_description: str | None = None
    sync_version: int


class ExecutorTaskOut(BaseModel):
    task: TaskOut
    assign_status: str | None = None
    executions: list[ExecutionOut]
