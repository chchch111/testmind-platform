from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AiGenerateRequest(BaseModel):
    knowledge_base_id: int
    requirement_text: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    generation_mode: str = "comprehensive"
    score_threshold: float | None = Field(default=None, ge=0, le=1)
    selected_chunk_ids: list[int] | None = None
    created_by: int = 1
    save_to_case_set: bool = True


class AiGenerateOut(BaseModel):
    generation_id: int
    retrieval_id: int | None
    case_set_id: int | None
    generated_json: dict[str, Any]
    generated_text: str
    retrieval_summary: dict[str, Any] | None = None


class AiGenerationRecordOut(BaseModel):
    generation_id: int
    user_id: int
    retrieval_id: int | None
    requirement_text: str
    model_provider: str
    model_name: str
    prompt_template_version: str | None = None
    used_chunk_ids: list | None
    generated_json: dict | None
    case_set_id: int | None
    generation_status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AiGenerationRetrievedItemOut(BaseModel):
    chunk_id: int
    source_id: int
    source_name: str | None = None
    score: float | None = None
    chunk_text: str
    metadata: dict | None = None


class AiGenerationRecordDetailOut(AiGenerationRecordOut):
    knowledge_base_id: int | None = None
    top_k: int | None = None
    score_threshold: float | None = None
    generation_mode: str | None = None
    prompt_variables_json: dict | None = None
    retrieval_summary: dict | None = None
    retrieved_items: list[AiGenerationRetrievedItemOut] = Field(default_factory=list)
