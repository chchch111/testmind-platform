from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.canvas import CaseNodeMeta, CaseSetReview, CaseSetSnapshot
from app.models.case import TestCaseSet
from app.schemas.canvas import CaseSetMetaSaveRequest, ReviewCreate, ReviewUpdate, SnapshotCreate
from app.services.case_service import ensure_user_exists

VALID_META_TYPES = {"tag", "note", "link", "image", "review"}


def get_active_case_set(db: Session, case_set_id: int) -> TestCaseSet:
    case_set = db.get(TestCaseSet, case_set_id)
    if not case_set or case_set.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例集不存在")
    return case_set


def list_node_metas(db: Session, case_set_id: int) -> list[dict]:
    get_active_case_set(db, case_set_id)
    rows = list(
        db.scalars(
            select(CaseNodeMeta)
            .where(CaseNodeMeta.case_set_id == case_set_id)
            .order_by(CaseNodeMeta.meta_id.asc())
        ).all()
    )
    return [
        {
            "node_id": row.node_id,
            "meta_type": row.meta_type,
            "meta_key": row.meta_key,
            "meta_value": row.meta_value,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


def replace_node_metas(db: Session, data: CaseSetMetaSaveRequest, operator_id: int) -> dict:
    """整包替换一个用例集的节点元数据，用于前端统一保存。"""
    ensure_user_exists(db, operator_id)
    get_active_case_set(db, data.case_set_id)

    # 简单校验 meta_type，避免脏数据。
    for item in data.items:
        if item.meta_type not in VALID_META_TYPES:
            raise HTTPException(status_code=400, detail=f"meta_type只能是{'/'.join(sorted(VALID_META_TYPES))}")

    db.execute(delete(CaseNodeMeta).where(CaseNodeMeta.case_set_id == data.case_set_id))
    for item in data.items:
        db.add(
            CaseNodeMeta(
                case_set_id=data.case_set_id,
                node_id=item.node_id,
                meta_type=item.meta_type,
                meta_key=item.meta_key,
                meta_value=item.meta_value,
                created_by=operator_id,
                updated_by=operator_id,
            )
        )
    db.commit()
    return {"message": "节点元数据已保存", "case_set_id": data.case_set_id, "count": len(data.items)}


def create_snapshot(db: Session, data: SnapshotCreate, operator_id: int) -> CaseSetSnapshot:
    ensure_user_exists(db, operator_id)
    get_active_case_set(db, data.case_set_id)
    snapshot = CaseSetSnapshot(
        case_set_id=data.case_set_id,
        name=data.name,
        data_json=data.data,
        created_by=operator_id,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_snapshots(db: Session, case_set_id: int) -> list[CaseSetSnapshot]:
    get_active_case_set(db, case_set_id)
    statement = (
        select(CaseSetSnapshot)
        .where(CaseSetSnapshot.case_set_id == case_set_id)
        .order_by(CaseSetSnapshot.snapshot_id.desc())
        .limit(50)
    )
    return list(db.scalars(statement).all())


def delete_snapshot(db: Session, snapshot_id: int, operator_id: int) -> dict:
    ensure_user_exists(db, operator_id)
    snapshot = db.get(CaseSetSnapshot, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="快照不存在")
    db.delete(snapshot)
    db.commit()
    return {"message": "快照已删除", "snapshot_id": snapshot_id}


def create_review(db: Session, data: ReviewCreate, operator_id: int) -> CaseSetReview:
    ensure_user_exists(db, operator_id)
    get_active_case_set(db, data.case_set_id)
    for reviewer_id in data.reviewer_ids:
        ensure_user_exists(db, reviewer_id)
    review = CaseSetReview(
        case_set_id=data.case_set_id,
        reviewer_ids=data.reviewer_ids,
        due_at=data.due_at,
        note=data.note,
        status="submitted",
        created_by=operator_id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_reviews(db: Session, case_set_id: int) -> list[CaseSetReview]:
    get_active_case_set(db, case_set_id)
    statement = (
        select(CaseSetReview)
        .where(CaseSetReview.case_set_id == case_set_id)
        .order_by(CaseSetReview.review_id.desc())
        .limit(50)
    )
    return list(db.scalars(statement).all())


def update_review(db: Session, review_id: int, data: ReviewUpdate, operator_id: int) -> CaseSetReview:
    ensure_user_exists(db, operator_id)
    review = db.get(CaseSetReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="评审记录不存在")

    if data.status is not None:
        review.status = data.status
    if data.conclusion is not None:
        review.conclusion = data.conclusion

    db.commit()
    db.refresh(review)
    return review
