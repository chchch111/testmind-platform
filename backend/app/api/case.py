from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.db.deps import get_db
from app.models.case import TestCaseSet
from app.models.user import User
from app.schemas.case import (
    CaseNodeCreate,
    CaseNodeOut,
    CaseNodeTreeOut,
    CaseNodeUpdate,
    CaseNodeVersionOut,
    CaseSetCreate,
    CaseSetOut,
    CaseSetPageOut,
    RollbackRequest,
)
from app.services.case_service import (
    create_case_node,
    create_case_set,
    delete_case_node,
    delete_case_set,
    get_case_node,
    get_case_tree,
    list_case_sets,
    list_node_versions,
    publish_case_set,
    rollback_node,
    update_case_node,
)


router = APIRouter(prefix="/api", tags=["思维导图用例管理"])


@router.post("/case-sets", response_model=CaseSetOut)
def api_create_case_set(
    data: CaseSetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.created_by = current_user.user_id
    return create_case_set(db, data)


@router.get("/case-sets", response_model=CaseSetPageOut)
def api_list_case_sets(
    keyword: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_case_sets(db, page, page_size, keyword, source_type, status)


@router.delete("/case-sets/{case_set_id}")
def api_delete_case_set(
    case_set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return delete_case_set(db, case_set_id, current_user.user_id)


@router.post("/case-sets/{case_set_id}/publish", response_model=CaseSetOut)
def api_publish_case_set(
    case_set_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return publish_case_set(db, case_set_id, current_user.user_id)


@router.post("/case-nodes", response_model=CaseNodeOut)
def api_create_case_node(
    data: CaseNodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.created_by = current_user.user_id
    return create_case_node(db, data)


@router.get("/case-sets/{case_set_id}/tree", response_model=list[CaseNodeTreeOut])
def api_get_case_tree(case_set_id: int, db: Session = Depends(get_db)):
    return get_case_tree(db, case_set_id)


@router.get("/case-sets/{case_set_id}/export-json")
def api_export_case_set_json(case_set_id: int, db: Session = Depends(get_db)):
    """导出用例集树为 JSON，便于备份或迁移。"""
    from fastapi.responses import JSONResponse

    case_set = db.get(TestCaseSet, case_set_id)
    if not case_set or case_set.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例集不存在")

    payload = {
        "case_set": {
            "case_set_id": case_set.case_set_id,
            "name": case_set.name,
            "description": case_set.description,
            "source_type": case_set.source_type,
            "status": case_set.status,
            "created_at": case_set.created_at.isoformat() if case_set.created_at else None,
            "updated_at": case_set.updated_at.isoformat() if case_set.updated_at else None,
        },
        "tree": get_case_tree(db, case_set_id),
    }
    filename = f"case_set_{case_set_id}.json"
    return JSONResponse(content=payload, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/case-nodes/{node_id}", response_model=CaseNodeOut)
def api_get_case_node(node_id: int, db: Session = Depends(get_db)):
    return get_case_node(db, node_id)


@router.put("/case-nodes/{node_id}", response_model=CaseNodeOut)
def api_update_case_node(
    node_id: int,
    data: CaseNodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.updated_by = current_user.user_id
    return update_case_node(db, node_id, data)


@router.delete("/case-nodes/{node_id}")
def api_delete_case_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return delete_case_node(db, node_id, current_user.user_id)


@router.get("/case-nodes/{node_id}/versions", response_model=list[CaseNodeVersionOut])
def api_list_node_versions(node_id: int, db: Session = Depends(get_db)):
    return list_node_versions(db, node_id)


@router.post("/case-nodes/{node_id}/rollback/{version_id}", response_model=CaseNodeOut)
def api_rollback_node(
    node_id: int,
    version_id: int,
    data: RollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return rollback_node(db, node_id, version_id, current_user.user_id, data.change_note)
