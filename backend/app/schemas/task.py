from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    task_name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    parent_id: int | None = None
    owner_id: int | None = None
    case_set_ids: list[int] = Field(default_factory=list)
    assignee_ids: list[int] = Field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    created_by: int = 1


class TaskOut(BaseModel):
    task_id: int
    parent_id: int | None = None
    task_name: str
    owner_id: int | None = None
    owner_name: str | None = None
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
    executor_name: str | None = None
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


class SubtaskOut(TaskDetailOut):
    parent_id: int | None = None
    parent_name: str | None = None
    owner_id: int | None = None
    owner_name: str | None = None
    assignee_names: list[str] = Field(default_factory=list)


class TaskDirectoryOut(BaseModel):
    task_id: int
    task_name: str
    description: str | None
    status: str
    owner_id: int | None = None
    owner_name: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    subtask_count: int = 0
    total_cases: int = 0
    tested_count: int = 0
    passed_count: int = 0
    pass_rate: float = 0.0


class TaskDirectoryPageOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TaskDirectoryOut]


class SubtasksPageOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[SubtaskOut]


class TaskTreeStatusOut(BaseModel):
    task_id: int
    task_name: str
    parent_id: int | None = None
    parent_name: str | None = None
    assign_status: str | None = None
    assignee_ids: list[int] = Field(default_factory=list)
    assignee_names: list[str] = Field(default_factory=list)
    case_set_ids: list[int] = Field(default_factory=list)
    tree: list[dict] = Field(default_factory=list)
    status_map: dict[str, str] = Field(default_factory=dict)
    total_cases: int = 0
    tested_count: int = 0
    passed_count: int = 0
