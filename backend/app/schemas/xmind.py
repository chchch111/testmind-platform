from datetime import datetime

from pydantic import BaseModel


class XMindImportOut(BaseModel):
    case_set_id: int
    xmind_file_id: int
    import_batch_id: int
    node_count: int
    message: str


class XMindNodeTagIn(BaseModel):
    text: str
    color: str | None = None


class XMindExportIn(BaseModel):
    operator_id: int = 1
    node_tags_map: dict[str, list[XMindNodeTagIn]] = {}


class XMindFileOut(BaseModel):
    xmind_file_id: int
    case_set_id: int | None
    file_name: str
    file_path: str
    file_type: str
    file_size: int | None
    process_status: str
    error_message: str | None
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class XMindBatchOut(BaseModel):
    import_batch_id: int
    batch_uuid: str
    xmind_file_id: int
    case_set_id: int
    node_count: int
    import_status: str
    error_message: str | None
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}
