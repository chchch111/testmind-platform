from datetime import datetime

from pydantic import BaseModel, Field


ROLE_OPTIONS = [
    {"label": "管理员", "value": "admin"},
    {"label": "管理人员", "value": "manager"},
    {"label": "测试人员", "value": "tester"},
    {"label": "执行人员", "value": "executor"},
]
VALID_ROLE_CODES = {item["value"] for item in ROLE_OPTIONS}


class RoleOptionOut(BaseModel):
    label: str
    value: str


class PermissionUserOut(BaseModel):
    user_id: int
    username: str
    real_name: str | None
    role_code: str
    email: str | None
    phone: str | None
    is_active: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PermissionUserPageOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PermissionUserOut]


class PermissionUserUpdate(BaseModel):
    role_code: str | None = Field(default=None, max_length=30)
    is_active: int | None = Field(default=None, ge=0, le=1)
