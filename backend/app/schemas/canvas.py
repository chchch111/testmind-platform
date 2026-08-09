from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NodeMetaValue(BaseModel):
    """单个节点的元数据条目（tag/note/link/image/review）。"""

    node_id: int
    meta_type: str = Field(pattern="^(tag|note|link|image|review)$")
    meta_key: str | None = None
    meta_value: dict[str, Any] | None = None


class CaseSetMetaSaveRequest(BaseModel):
    """保存一个用例集的全部节点元数据（前端整包替换）。"""

    case_set_id: int | None = None
    items: list[NodeMetaValue] = Field(default_factory=list)


class CaseSetMetaOut(BaseModel):
    case_set_id: int
    items: list[dict[str, Any]]


class SnapshotCreate(BaseModel):
    case_set_id: int | None = None
    name: str = Field(min_length=1, max_length=200)
    data: dict[str, Any]


class SnapshotOut(BaseModel):
    snapshot_id: int
    case_set_id: int
    name: str
    data_json: dict[str, Any]
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    case_set_id: int | None = None
    reviewer_ids: list[int] = Field(min_length=1)
    due_at: datetime | None = None
    note: str | None = None


class ReviewOut(BaseModel):
    review_id: int
    case_set_id: int
    reviewer_ids: list[int]
    due_at: datetime | None
    note: str | None
    status: str
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}
