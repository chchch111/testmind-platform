from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.case import (
    CaseNodeCreate,
    CaseNodeOut,
    CaseNodeTreeOut,
    CaseNodeUpdate,
    CaseNodeVersionOut,
    CaseSetCreate,
    CaseSetOut,
    CaseSetPageOut,
    DeleteRequest,
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
    rollback_node,
    update_case_node,
)


router = APIRouter(prefix="/api", tags=["思维导图用例管理"])


@router.post("/case-sets", response_model=CaseSetOut)
def api_create_case_set(data: CaseSetCreate, db: Session = Depends(get_db)):
    return create_case_set(db, data)


@router.get("/case-sets", response_model=CaseSetPageOut)
def api_list_case_sets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_case_sets(db, page, page_size)


@router.delete("/case-sets/{case_set_id}")
def api_delete_case_set(case_set_id: int, data: DeleteRequest, db: Session = Depends(get_db)):
    return delete_case_set(db, case_set_id, data.operator_id)


@router.post("/case-nodes", response_model=CaseNodeOut)
def api_create_case_node(data: CaseNodeCreate, db: Session = Depends(get_db)):
    return create_case_node(db, data)


@router.get("/case-sets/{case_set_id}/tree", response_model=list[CaseNodeTreeOut])
def api_get_case_tree(case_set_id: int, db: Session = Depends(get_db)):
    return get_case_tree(db, case_set_id)


@router.get("/case-nodes/{node_id}", response_model=CaseNodeOut)
def api_get_case_node(node_id: int, db: Session = Depends(get_db)):
    return get_case_node(db, node_id)


@router.put("/case-nodes/{node_id}", response_model=CaseNodeOut)
def api_update_case_node(node_id: int, data: CaseNodeUpdate, db: Session = Depends(get_db)):
    return update_case_node(db, node_id, data)


@router.delete("/case-nodes/{node_id}")
def api_delete_case_node(node_id: int, data: DeleteRequest, db: Session = Depends(get_db)):
    return delete_case_node(db, node_id, data.operator_id)


@router.get("/case-nodes/{node_id}/versions", response_model=list[CaseNodeVersionOut])
def api_list_node_versions(node_id: int, db: Session = Depends(get_db)):
    return list_node_versions(db, node_id)


@router.post("/case-nodes/{node_id}/rollback/{version_id}", response_model=CaseNodeOut)
def api_rollback_node(node_id: int, version_id: int, data: RollbackRequest, db: Session = Depends(get_db)):
    return rollback_node(db, node_id, version_id, data.operator_id, data.change_note)
