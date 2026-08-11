from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    product_type: str | None = None
    hardware_module: str | None = None
    created_by: int = 1


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    product_type: str | None = None
    hardware_module: str | None = None
    status: str | None = None


class KnowledgeBaseOut(BaseModel):
    knowledge_base_id: int
    name: str
    description: str | None
    product_type: str | None
    hardware_module: str | None
    status: str
    created_by: int
    updated_by: int | None
    created_at: datetime
    updated_at: datetime
    source_count: int = 0
    chunk_count: int = 0
    index_status: str = "none"

    model_config = {"from_attributes": True}


class ManualSourceCreate(BaseModel):
    source_name: str = Field(min_length=1, max_length=255)
    content_text: str = Field(min_length=1)
    source_type: str = "manual_text"
    created_by: int = 1


class KnowledgeSourceOut(BaseModel):
    source_id: int
    knowledge_base_id: int
    source_name: str
    source_type: str
    status: str
    created_by: int
    file_name: str | None = None
    content_text: str | None = None
    case_set_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BuildIndexOut(BaseModel):
    faiss_index_id: int
    knowledge_base_id: int
    index_name: str
    index_file_path: str
    docstore_file_path: str
    chunk_count: int
    vector_count: int
    vector_dimension: int
    message: str


class RagSearchRequest(BaseModel):
    query_text: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RagSearchItem(BaseModel):
    chunk_id: int
    source_id: int
    source_name: str | None = None
    score: float
    chunk_text: str
    metadata: dict | None


class RagSearchOut(BaseModel):
    knowledge_base_id: int
    faiss_index_id: int
    query_text: str
    items: list[RagSearchItem]
