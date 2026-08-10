from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.ai import AiGenerationRecord
from app.models.canvas import CaseNodeMeta, CaseSetReview, CaseSetSnapshot
from app.models.case import TestCaseNode, TestCaseNodeVersion, TestCaseSet
from app.models.user import User
from app.schemas.case import CaseNodeCreate, CaseNodeUpdate, CaseSetCreate


VALID_NODE_TYPES = {"folder", "case"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}


def ensure_user_exists(db: Session, user_id: int) -> None:
    user = db.get(User, user_id)
    if not user or user.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用户不存在，请先创建用户或使用已有用户ID")


def create_case_set(db: Session, data: CaseSetCreate) -> TestCaseSet:
    ensure_user_exists(db, data.created_by)
    case_set = TestCaseSet(
        name=data.name,
        description=data.description,
        source_type="manual",
        status="active",
        created_by=data.created_by,
    )
    db.add(case_set)
    db.commit()
    db.refresh(case_set)
    return case_set


def list_case_sets(
    db: Session,
    page: int,
    page_size: int,
    keyword: str | None = None,
    source_type: str | None = None,
    status: str | None = None,
) -> dict:
    conditions = [TestCaseSet.is_deleted == 0]
    if keyword and keyword.strip():
        like_keyword = f"%{keyword.strip()}%"
        conditions.append(or_(TestCaseSet.name.like(like_keyword), TestCaseSet.description.like(like_keyword)))
    if source_type:
        conditions.append(TestCaseSet.source_type == source_type)
    if status:
        conditions.append(TestCaseSet.status == status)

    total = db.scalar(select(func.count()).select_from(TestCaseSet).where(*conditions)) or 0
    statement = (
        select(TestCaseSet)
        .where(*conditions)
        .order_by(TestCaseSet.case_set_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.scalars(statement).all())
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": enrich_case_sets(db, items),
    }


def enrich_case_sets(db: Session, items: list[TestCaseSet]) -> list[dict]:
    """给 AI 生成的用例集附带来源需求与生成记录，实现需求→用例追溯。"""
    if not items:
        return []

    ai_case_set_ids = [item.case_set_id for item in items if item.source_type == "ai_generated"]
    record_map = {}
    if ai_case_set_ids:
        records = list(
            db.scalars(
                select(AiGenerationRecord).where(AiGenerationRecord.case_set_id.in_(ai_case_set_ids))
            ).all()
        )
        record_map = {record.case_set_id: record for record in records}

    result = []
    for item in items:
        case_set_dict = {
            "case_set_id": item.case_set_id,
            "name": item.name,
            "description": item.description,
            "source_type": item.source_type,
            "status": item.status,
            "created_by": item.created_by,
            "updated_by": item.updated_by,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        record = record_map.get(item.case_set_id)
        if record:
            case_set_dict["generation_id"] = record.generation_id
            case_set_dict["requirement_text"] = record.requirement_text
        result.append(case_set_dict)
    return result


def get_case_node(db: Session, node_id: int) -> TestCaseNode:
    node = db.get(TestCaseNode, node_id)
    if not node or node.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例节点不存在")
    return node


def create_case_node(db: Session, data: CaseNodeCreate) -> TestCaseNode:
    ensure_user_exists(db, data.created_by)

    if data.node_type not in VALID_NODE_TYPES:
        raise HTTPException(status_code=400, detail="node_type只能是folder或case")

    if data.priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="priority只能是P0/P1/P2/P3")

    case_set = db.get(TestCaseSet, data.case_set_id)
    if not case_set or case_set.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例集不存在")

    if data.parent_id is not None:
        parent = db.get(TestCaseNode, data.parent_id)
        if not parent or parent.is_deleted == 1 or parent.case_set_id != data.case_set_id:
            raise HTTPException(status_code=400, detail="父节点不存在或不属于当前用例集")

    node = TestCaseNode(**data.model_dump())
    db.add(node)
    db.flush()
    create_node_version(db, node, operation_type="create", operator_id=data.created_by, change_note="创建节点")
    db.commit()
    db.refresh(node)
    return node


def get_case_tree(db: Session, case_set_id: int) -> list[dict]:
    statement = (
        select(TestCaseNode)
        .where(TestCaseNode.case_set_id == case_set_id, TestCaseNode.is_deleted == 0)
        .order_by(TestCaseNode.parent_id.asc(), TestCaseNode.sort_order.asc(), TestCaseNode.node_id.asc())
    )
    nodes = list(db.scalars(statement).all())
    node_map = {node.node_id: node_to_tree_dict(node) | {"children": []} for node in nodes}
    roots = []

    for node in nodes:
        item = node_map[node.node_id]
        if node.parent_id and node.parent_id in node_map:
            node_map[node.parent_id]["children"].append(item)
        else:
            roots.append(item)

    return roots


def node_to_tree_dict(node: TestCaseNode) -> dict:
    """树接口专用序列化，去掉前端不用的审计字段，降低大树负载。"""
    return {
        "node_id": node.node_id,
        "case_set_id": node.case_set_id,
        "parent_id": node.parent_id,
        "node_type": node.node_type,
        "title": node.title,
        "precondition": node.precondition,
        "test_steps": node.test_steps,
        "expected_result": node.expected_result,
        "priority": node.priority,
        "sort_order": node.sort_order,
    }


def update_case_node(db: Session, node_id: int, data: CaseNodeUpdate) -> TestCaseNode:
    ensure_user_exists(db, data.updated_by)

    node = db.get(TestCaseNode, node_id)
    if not node or node.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例节点不存在")

    update_data = data.model_dump(exclude_unset=True, exclude={"change_note"})

    if "node_type" in update_data and update_data["node_type"] not in VALID_NODE_TYPES:
        raise HTTPException(status_code=400, detail="node_type只能是folder或case")

    if "priority" in update_data and update_data["priority"] not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail="priority只能是P0/P1/P2/P3")

    if "parent_id" in update_data:
        validate_parent_change(db, node, update_data["parent_id"])

    for field, value in update_data.items():
        setattr(node, field, value)

    create_node_version(
        db,
        node,
        operation_type="update",
        operator_id=data.updated_by,
        change_note=data.change_note,
    )
    db.commit()
    db.refresh(node)
    return node


def validate_parent_change(db: Session, node: TestCaseNode, parent_id: int | None) -> None:
    if parent_id is None:
        return

    if parent_id == node.node_id:
        raise HTTPException(status_code=400, detail="不能将节点移动到自身下面")

    parent = db.get(TestCaseNode, parent_id)
    if not parent or parent.is_deleted == 1 or parent.case_set_id != node.case_set_id:
        raise HTTPException(status_code=400, detail="父节点不存在或不属于当前用例集")

    current = parent
    while current.parent_id is not None:
        if current.parent_id == node.node_id:
            raise HTTPException(status_code=400, detail="不能将节点移动到自己的子节点下面")
        current = db.get(TestCaseNode, current.parent_id)
        if not current or current.is_deleted == 1:
            break


def list_node_versions(db: Session, node_id: int) -> list[TestCaseNodeVersion]:
    statement = (
        select(TestCaseNodeVersion)
        .where(TestCaseNodeVersion.node_id == node_id)
        .order_by(TestCaseNodeVersion.version_no.desc())
    )
    return list(db.scalars(statement).all())


def rollback_node(db: Session, node_id: int, version_id: int, operator_id: int, change_note: str | None) -> TestCaseNode:
    ensure_user_exists(db, operator_id)

    node = db.get(TestCaseNode, node_id)
    if not node or node.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例节点不存在")

    version = db.get(TestCaseNodeVersion, version_id)
    if not version or version.node_id != node_id:
        raise HTTPException(status_code=404, detail="历史版本不存在")

    node.title = version.title
    node.node_type = version.node_type
    node.precondition = version.precondition
    node.test_steps = version.test_steps
    node.expected_result = version.expected_result
    node.priority = version.priority
    node.updated_by = operator_id

    create_node_version(
        db,
        node,
        operation_type="rollback",
        operator_id=operator_id,
        change_note=change_note,
        rollback_from_version_id=version_id,
    )
    db.commit()
    db.refresh(node)
    return node


def delete_case_set(db: Session, case_set_id: int, operator_id: int) -> dict:
    ensure_user_exists(db, operator_id)

    case_set = db.get(TestCaseSet, case_set_id)
    if not case_set or case_set.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例集不存在")

    case_set.is_deleted = 1
    case_set.status = "disabled"
    case_set.updated_by = operator_id

    nodes = db.scalars(select(TestCaseNode).where(TestCaseNode.case_set_id == case_set_id, TestCaseNode.is_deleted == 0)).all()
    for node in nodes:
        node.is_deleted = 1
        node.updated_by = operator_id

    # 级联清理脑图元数据、快照、评审记录（纯展示数据，物理删除避免遗留垃圾）。
    db.execute(delete(CaseNodeMeta).where(CaseNodeMeta.case_set_id == case_set_id))
    db.execute(delete(CaseSetSnapshot).where(CaseSetSnapshot.case_set_id == case_set_id))
    db.execute(delete(CaseSetReview).where(CaseSetReview.case_set_id == case_set_id))

    db.commit()
    return {"message": "用例集删除成功", "case_set_id": case_set_id, "deleted_nodes": len(nodes)}


def publish_case_set(db: Session, case_set_id: int, operator_id: int) -> TestCaseSet:
    """把 AI 生成或草稿状态的用例集发布为正式可用（active）。"""
    ensure_user_exists(db, operator_id)
    case_set = db.get(TestCaseSet, case_set_id)
    if not case_set or case_set.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例集不存在")
    if case_set.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿状态的用例集可以发布")
    case_set.status = "active"
    case_set.updated_by = operator_id
    db.commit()
    db.refresh(case_set)
    return case_set


def delete_case_node(db: Session, node_id: int, operator_id: int) -> dict:
    ensure_user_exists(db, operator_id)

    node = db.get(TestCaseNode, node_id)
    if not node or node.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用例节点不存在")

    all_nodes = db.scalars(
        select(TestCaseNode).where(TestCaseNode.case_set_id == node.case_set_id, TestCaseNode.is_deleted == 0)
    ).all()
    children_map: dict[int | None, list[TestCaseNode]] = {}
    for item in all_nodes:
        children_map.setdefault(item.parent_id, []).append(item)

    target_nodes = []
    stack = [node]
    while stack:
        current = stack.pop()
        target_nodes.append(current)
        stack.extend(children_map.get(current.node_id, []))

    for item in target_nodes:
        item.is_deleted = 1
        item.updated_by = operator_id
        create_node_version(
            db,
            item,
            operation_type="delete",
            operator_id=operator_id,
            change_note="逻辑删除节点",
        )

    db.commit()
    return {"message": "用例节点删除成功", "node_id": node_id, "deleted_nodes": len(target_nodes)}


def create_node_version(
    db: Session,
    node: TestCaseNode,
    operation_type: str,
    operator_id: int,
    change_note: str | None,
    rollback_from_version_id: int | None = None,
) -> TestCaseNodeVersion:
    latest_version_no = db.scalar(
        select(func.max(TestCaseNodeVersion.version_no)).where(TestCaseNodeVersion.node_id == node.node_id)
    )
    next_version_no = (latest_version_no or 0) + 1
    snapshot = node_to_dict(node)

    version = TestCaseNodeVersion(
        node_id=node.node_id,
        version_no=next_version_no,
        operation_type=operation_type,
        change_note=change_note,
        title=node.title,
        node_type=node.node_type,
        precondition=node.precondition,
        test_steps=node.test_steps,
        expected_result=node.expected_result,
        priority=node.priority,
        snapshot_json=snapshot,
        rollback_from_version_id=rollback_from_version_id,
        created_by=operator_id,
    )
    db.add(version)
    return version


def node_to_dict(node: TestCaseNode) -> dict:
    return {
        "node_id": node.node_id,
        "case_set_id": node.case_set_id,
        "parent_id": node.parent_id,
        "node_type": node.node_type,
        "title": node.title,
        "precondition": node.precondition,
        "test_steps": node.test_steps,
        "expected_result": node.expected_result,
        "priority": node.priority,
        "sort_order": node.sort_order,
        "created_by": node.created_by,
        "updated_by": node.updated_by,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
    }
