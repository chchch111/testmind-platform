from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.canvas import (
    CaseSetMetaOut,
    CaseSetMetaSaveRequest,
    ReviewCreate,
    ReviewOut,
    SnapshotCreate,
    SnapshotOut,
)
from app.services.canvas_service import (
    create_review,
    create_snapshot,
    delete_snapshot,
    list_node_metas,
    list_reviews,
    list_snapshots,
    replace_node_metas,
)

router = APIRouter(prefix="/api/case-sets", tags=["脑图数据"])


@router.get("/{case_set_id}/metas", response_model=CaseSetMetaOut)
def api_get_case_set_metas(case_set_id: int, db: Session = Depends(get_db)):
    return CaseSetMetaOut(case_set_id=case_set_id, items=list_node_metas(db, case_set_id))


@router.put("/{case_set_id}/metas")
def api_save_case_set_metas(
    case_set_id: int,
    data: CaseSetMetaSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.case_set_id = case_set_id
    return replace_node_metas(db, data, current_user.user_id)


@router.post("/{case_set_id}/snapshots", response_model=SnapshotOut)
def api_create_snapshot(
    case_set_id: int,
    data: SnapshotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.case_set_id = case_set_id
    return create_snapshot(db, data, current_user.user_id)


@router.get("/{case_set_id}/snapshots", response_model=list[SnapshotOut])
def api_list_snapshots(case_set_id: int, db: Session = Depends(get_db)):
    return list_snapshots(db, case_set_id)


@router.delete("/{case_set_id}/snapshots/{snapshot_id}")
def api_delete_snapshot(
    case_set_id: int,
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return delete_snapshot(db, snapshot_id, current_user.user_id)


@router.post("/{case_set_id}/reviews", response_model=ReviewOut)
def api_create_review(
    case_set_id: int,
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.case_set_id = case_set_id
    return create_review(db, data, current_user.user_id)


@router.get("/{case_set_id}/reviews", response_model=list[ReviewOut])
def api_list_reviews(case_set_id: int, db: Session = Depends(get_db)):
    return list_reviews(db, case_set_id)
