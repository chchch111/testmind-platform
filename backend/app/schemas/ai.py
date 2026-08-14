from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AiGenerateRequest(BaseModel):
    knowledge_base_id: int
    requirement_text: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    selected_chunk_ids: list[int] | None = None
    created_by: int = 1
    save_to_case_set: bool = True


class AiGenerateOut(BaseModel):
    generation_id: int
    retrieval_id: int | None
    case_set_id: int | None
    generated_json: dict[str, Any]
    generated_text: str


class AiGenerationRecordOut(BaseModel):
    generation_id: int
    user_id: int
    retrieval_id: int | None
    requirement_text: str
    model_provider: str
    model_name: str
    used_chunk_ids: list | None
    generated_json: dict | None
    case_set_id: int | None
    generation_status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
