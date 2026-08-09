from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CaseSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    created_by: int = 1


class CaseSetOut(BaseModel):
    case_set_id: int
    name: str
    description: str | None
    source_type: str
    status: str
    created_by: int
    updated_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseNodeCreate(BaseModel):
    case_set_id: int
    parent_id: int | None = None
    node_type: str = "folder"
    title: str = Field(min_length=1, max_length=300)
    precondition: str | None = None
    test_steps: str | None = None
    expected_result: str | None = None
    priority: str = "P1"
    sort_order: int = 0
    created_by: int = 1


class CaseNodeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    parent_id: int | None = None
    node_type: str | None = None
    precondition: str | None = None
    test_steps: str | None = None
    expected_result: str | None = None
    priority: str | None = None
    sort_order: int | None = None
    updated_by: int = 1
    change_note: str | None = None


class CaseNodeOut(BaseModel):
    node_id: int
    case_set_id: int
    parent_id: int | None
    node_type: str
    title: str
    precondition: str | None
    test_steps: str | None
    expected_result: str | None
    priority: str
    sort_order: int
    created_by: int
    updated_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseNodeTreeOut(CaseNodeOut):
    children: list["CaseNodeTreeOut"] = Field(default_factory=list)


class CaseSetPageOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CaseSetOut]


class DeleteRequest(BaseModel):
    pass


class CaseNodeVersionOut(BaseModel):
    version_id: int
    node_id: int
    version_no: int
    operation_type: str
    change_note: str | None
    title: str
    node_type: str
    precondition: str | None
    test_steps: str | None
    expected_result: str | None
    priority: str
    snapshot_json: dict[str, Any] | None
    rollback_from_version_id: int | None
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RollbackRequest(BaseModel):
    change_note: str | None = "回退历史版本"
