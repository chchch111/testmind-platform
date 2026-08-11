from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.xmind import XMindExportIn, XMindImportOut
from app.services.xmind_service import export_case_set_to_xmind, import_xmind_file


router = APIRouter(prefix="/api/xmind", tags=["XMind导入导出"])


@router.post("/import", response_model=XMindImportOut)
def api_import_xmind(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return import_xmind_file(db, file, current_user.user_id)


@router.post("/export/{case_set_id}")
def api_export_xmind_with_tags(
    case_set_id: int,
    data: XMindExportIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    node_tags_map = {
        int(node_id): [tag.text for tag in tags if tag.text.strip()]
        for node_id, tags in data.node_tags_map.items()
        if str(node_id).isdigit()
    }
    export_path = export_case_set_to_xmind(db, case_set_id, current_user.user_id, node_tags_map)
    return FileResponse(
        path=export_path,
        filename=export_path.name,
        media_type="application/vnd.xmind.workbook",
    )
