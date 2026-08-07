from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.xmind import XMindExportIn, XMindImportOut
from app.services.xmind_service import export_case_set_to_xmind, import_xmind_file


router = APIRouter(prefix="/api/xmind", tags=["XMind导入导出"])


@router.post("/import", response_model=XMindImportOut)
def api_import_xmind(
    file: UploadFile = File(...),
    created_by: int = Query(default=1),
    db: Session = Depends(get_db),
):
    return import_xmind_file(db, file, created_by)


@router.get("/export/{case_set_id}")
def api_export_xmind(
    case_set_id: int,
    operator_id: int = Query(default=1),
    db: Session = Depends(get_db),
):
    export_path = export_case_set_to_xmind(db, case_set_id, operator_id)
    return FileResponse(
        path=export_path,
        filename=export_path.name,
        media_type="application/vnd.xmind.workbook",
    )


@router.post("/export/{case_set_id}")
def api_export_xmind_with_tags(
    case_set_id: int,
    data: XMindExportIn,
    db: Session = Depends(get_db),
):
    node_tags_map = {
        int(node_id): [tag.text for tag in tags if tag.text.strip()]
        for node_id, tags in data.node_tags_map.items()
        if str(node_id).isdigit()
    }
    export_path = export_case_set_to_xmind(db, case_set_id, data.operator_id, node_tags_map)
    return FileResponse(
        path=export_path,
        filename=export_path.name,
        media_type="application/vnd.xmind.workbook",
    )
