from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.case import TestCaseNode, TestCaseSet
from app.models.task import TestExecutionRecord, TestTask, TestTaskAssignee, TestTaskCaseSet
from app.models.user import User
from app.schemas.task import ExecutionUpdate, TaskCreate
from app.services.case_service import ensure_user_exists


VALID_EXECUTION_STATUS = {"not_run", "passed", "failed", "blocked", "skipped"}


def create_task(db: Session, data: TaskCreate) -> dict:
    ensure_user_exists(db, data.created_by)

    owner_id = data.owner_id or data.created_by
    ensure_user_exists(db, owner_id)

    task = TestTask(
        task_name=data.task_name,
        description=data.description,
        parent_id=data.parent_id,
        owner_id=owner_id,
        status="assigned",
        start_time=data.start_time,
        end_time=data.end_time,
        created_by=data.created_by,
    )
    db.add(task)
    db.flush()

    # 目录（不绑定用例集/执行人）只建任务本体，不生成执行记录。
    if not data.case_set_ids:
        task.status = "draft" if data.parent_id else "assigned"
        db.commit()
        return get_task_detail(db, task.task_id)

    case_set_ids = list(dict.fromkeys(data.case_set_ids))
    assignee_ids = list(dict.fromkeys(data.assignee_ids))
    if not assignee_ids:
        raise HTTPException(status_code=400, detail="请至少指定一个执行人")

    for assignee_id in assignee_ids:
        ensure_user_exists(db, assignee_id)

    case_sets = list(
        db.scalars(
            select(TestCaseSet).where(TestCaseSet.case_set_id.in_(case_set_ids), TestCaseSet.is_deleted == 0)
        ).all()
    )
    if len(case_sets) != len(case_set_ids):
        raise HTTPException(status_code=400, detail="存在无效或已删除的用例集")

    case_nodes = list(
        db.scalars(
            select(TestCaseNode).where(
                TestCaseNode.case_set_id.in_(case_set_ids),
                TestCaseNode.node_type == "case",
                TestCaseNode.is_deleted == 0,
            )
        ).all()
    )
    if not case_nodes:
        raise HTTPException(status_code=400, detail="绑定的用例集中没有可执行的用例节点")

    for case_set_id in case_set_ids:
        db.add(TestTaskCaseSet(task_id=task.task_id, case_set_id=case_set_id))

    build_execution_records(db, task.task_id, case_nodes, assignee_ids)

    db.commit()
    return get_task_detail(db, task.task_id)


def build_execution_records(
    db: Session,
    task_id: int,
    case_nodes: list[TestCaseNode],
    assignee_ids: list[int],
) -> None:
    """为每个执行人 × 每个 case 节点生成执行记录（含内容快照）。"""
    for assignee_id in assignee_ids:
        db.add(TestTaskAssignee(task_id=task_id, assignee_id=assignee_id, assign_status="assigned"))
        for node in case_nodes:
            db.add(
                TestExecutionRecord(
                    task_id=task_id,
                    case_node_id=node.node_id,
                    executor_id=assignee_id,
                    execution_status="not_run",
                    sync_status="synced",
                    sync_version=1,
                    case_node_snapshot=build_node_snapshot(node),
                )
            )


def list_tasks(
    db: Session,
    page: int,
    page_size: int,
    keyword: str | None = None,
    status: str | None = None,
) -> dict:
    conditions = [TestTask.is_deleted == 0]
    if keyword and keyword.strip():
        like_keyword = f"%{keyword.strip()}%"
        conditions.append(or_(TestTask.task_name.like(like_keyword), TestTask.description.like(like_keyword)))
    if status:
        conditions.append(TestTask.status == status)

    total = db.scalar(select(func.count()).select_from(TestTask).where(*conditions)) or 0
    statement = (
        select(TestTask)
        .where(*conditions)
        .order_by(TestTask.task_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": list(db.scalars(statement).all()),
    }


def get_task_detail(db: Session, task_id: int) -> dict:
    task = db.get(TestTask, task_id)
    if not task or task.is_deleted == 1:
        raise HTTPException(status_code=404, detail="测试任务不存在")

    case_set_ids = list(
        db.scalars(select(TestTaskCaseSet.case_set_id).where(TestTaskCaseSet.task_id == task_id)).all()
    )
    assignee_ids = list(
        db.scalars(select(TestTaskAssignee.assignee_id).where(TestTaskAssignee.task_id == task_id)).all()
    )

    total_executions = db.scalar(
        select(func.count()).select_from(TestExecutionRecord).where(TestExecutionRecord.task_id == task_id)
    ) or 0
    passed_count = count_execution_status(db, task_id, "passed")
    failed_count = count_execution_status(db, task_id, "failed")
    blocked_count = count_execution_status(db, task_id, "blocked")
    not_run_count = count_execution_status(db, task_id, "not_run")

    return {
        "task_id": task.task_id,
        "task_name": task.task_name,
        "description": task.description,
        "status": task.status,
        "start_time": task.start_time,
        "end_time": task.end_time,
        "created_by": task.created_by,
        "updated_by": task.updated_by,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "case_set_ids": case_set_ids,
        "assignee_ids": assignee_ids,
        "total_executions": total_executions,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "blocked_count": blocked_count,
        "not_run_count": not_run_count,
    }


def get_task_report(db: Session, task_id: int) -> dict:
    """生成任务测试报告：总体通过率、按执行人统计、缺陷清单。"""
    task = db.get(TestTask, task_id)
    if not task or task.is_deleted == 1:
        raise HTTPException(status_code=404, detail="测试任务不存在")

    executions = list(
        db.scalars(
            select(TestExecutionRecord)
            .where(TestExecutionRecord.task_id == task_id)
            .order_by(TestExecutionRecord.executor_id.asc(), TestExecutionRecord.execution_id.asc())
        ).all()
    )
    enriched = enrich_executions(db, executions)

    total = len(executions)
    passed = sum(1 for item in enriched if item["execution_status"] == "passed")
    failed = sum(1 for item in enriched if item["execution_status"] == "failed")
    blocked = sum(1 for item in enriched if item["execution_status"] == "blocked")
    skipped = sum(1 for item in enriched if item["execution_status"] == "skipped")
    not_run = sum(1 for item in enriched if item["execution_status"] == "not_run")

    # 按执行人统计
    per_executor: dict[int, dict] = {}
    for item in enriched:
        executor_id = item["executor_id"]
        stats = per_executor.setdefault(
            executor_id,
            {"executor_id": executor_id, "total": 0, "passed": 0, "failed": 0, "blocked": 0, "skipped": 0, "not_run": 0},
        )
        stats["total"] += 1
        stats[item["execution_status"]] += 1

    # 缺陷清单：failed/blocked 且有关键信息的记录
    defects = [
        {
            "execution_id": item["execution_id"],
            "case_node_id": item["case_node_id"],
            "case_node_title": item["case_node_title"],
            "case_node_priority": item["case_node_priority"],
            "executor_id": item["executor_id"],
            "execution_status": item["execution_status"],
            "actual_result": item["actual_result"],
            "bug_description": item["bug_description"],
            "executed_at": item["executed_at"],
        }
        for item in enriched
        if item["execution_status"] in {"failed", "blocked"}
    ]

    return {
        "task_id": task_id,
        "task_name": task.task_name,
        "task_status": task.status,
        "total": total,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "skipped": skipped,
        "not_run": not_run,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "per_executor": list(per_executor.values()),
        "defects": defects,
    }


def list_task_executions(db: Session, task_id: int) -> list[dict]:
    task = db.get(TestTask, task_id)
    if not task or task.is_deleted == 1:
        raise HTTPException(status_code=404, detail="测试任务不存在")
    statement = (
        select(TestExecutionRecord)
        .where(TestExecutionRecord.task_id == task_id)
        .order_by(TestExecutionRecord.executor_id.asc(), TestExecutionRecord.execution_id.asc())
    )
    executions = list(db.scalars(statement).all())
    return enrich_executions(db, executions)


def get_executor_tasks(db: Session, executor_id: int) -> list[dict]:
    ensure_user_exists(db, executor_id)

    task_ids = list(
        db.scalars(select(TestTaskAssignee.task_id).where(TestTaskAssignee.assignee_id == executor_id)).all()
    )
    if not task_ids:
        return []

    tasks = list(
        db.scalars(select(TestTask).where(TestTask.task_id.in_(task_ids), TestTask.is_deleted == 0)).all()
    )
    active_task_ids = [task.task_id for task in tasks]
    if not active_task_ids:
        return []

    executions = list(
        db.scalars(
            select(TestExecutionRecord)
            .where(TestExecutionRecord.task_id.in_(active_task_ids), TestExecutionRecord.executor_id == executor_id)
            .order_by(TestExecutionRecord.execution_id.asc())
        ).all()
    )

    # 一次 enrich 所有执行记录，避免每个任务单独查询一次节点表。
    all_enriched = enrich_executions(db, executions)
    enriched_by_task: dict[int, list[dict]] = {}
    for item in all_enriched:
        enriched_by_task.setdefault(item["task_id"], []).append(item)

    assignees = list(
        db.scalars(
            select(TestTaskAssignee).where(
                TestTaskAssignee.task_id.in_(active_task_ids),
                TestTaskAssignee.assignee_id == executor_id,
            )
        ).all()
    )
    assign_status_map = {assignee.task_id: assignee.assign_status for assignee in assignees}

    result = []
    for task in tasks:
        result.append({
            "task": task,
            "assign_status": assign_status_map.get(task.task_id, "assigned"),
            "executions": enriched_by_task.get(task.task_id, []),
        })
    return result


def update_execution(db: Session, execution_id: int, data: ExecutionUpdate) -> TestExecutionRecord:
    ensure_user_exists(db, data.executor_id)

    if data.execution_status not in VALID_EXECUTION_STATUS:
        raise HTTPException(status_code=400, detail="execution_status只能是not_run/passed/failed/blocked/skipped")

    execution = db.get(TestExecutionRecord, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    if execution.executor_id != data.executor_id:
        raise HTTPException(status_code=403, detail="只能更新分配给自己的执行记录")

    # 执行人需先认领任务才能提交执行结果。
    assignee = db.scalar(
        select(TestTaskAssignee).where(
            TestTaskAssignee.task_id == execution.task_id,
            TestTaskAssignee.assignee_id == execution.executor_id,
        )
    )
    if not assignee or assignee.assign_status != "accepted":
        raise HTTPException(status_code=403, detail="请先认领任务，再提交执行结果")

    if data.sync_version != execution.sync_version:
        execution.sync_status = "conflict"
        db.commit()
        raise HTTPException(status_code=409, detail="执行记录已被其他请求更新，请重新同步后再提交")

    execution.execution_status = data.execution_status
    execution.actual_result = data.actual_result
    execution.bug_description = data.bug_description
    execution.sync_version += 1
    execution.sync_status = "synced"
    execution.executed_at = datetime.now()
    execution.synced_at = datetime.now()

    db.commit()
    db.refresh(execution)
    refresh_task_status(db, execution.task_id)
    return execution


def refresh_task_status(db: Session, task_id: int) -> None:
    task = db.get(TestTask, task_id)
    if not task:
        return

    not_run_count = count_execution_status(db, task_id, "not_run")
    if not_run_count == 0:
        task.status = "finished"
    else:
        task.status = "running"
    db.commit()


def cancel_task(db: Session, task_id: int, operator_id: int) -> dict:
    ensure_user_exists(db, operator_id)
    task = db.get(TestTask, task_id)
    if not task or task.is_deleted == 1:
        raise HTTPException(status_code=404, detail="测试任务不存在")
    if task.status in {"finished", "cancelled"}:
        raise HTTPException(status_code=400, detail="已完成或已取消的任务不能再次取消")
    task.status = "cancelled"
    task.updated_by = operator_id
    db.commit()
    return {"message": "测试任务已取消", "task_id": task_id}


def delete_task(db: Session, task_id: int, operator_id: int) -> dict:
    ensure_user_exists(db, operator_id)
    task = db.get(TestTask, task_id)
    if not task or task.is_deleted == 1:
        raise HTTPException(status_code=404, detail="测试任务不存在")
    task.is_deleted = 1
    task.status = "cancelled"
    task.updated_by = operator_id
    db.commit()
    return {"message": "测试任务已删除", "task_id": task_id}


def build_node_snapshot(node: TestCaseNode) -> dict:
    """任务下发时固化用例节点内容，避免后续编辑影响执行人看到的内容。"""
    return {
        "title": node.title,
        "node_type": node.node_type,
        "precondition": node.precondition,
        "test_steps": node.test_steps,
        "expected_result": node.expected_result,
        "priority": node.priority,
    }


def assign_task(db: Session, task_id: int, executor_id: int) -> dict:
    """执行人认领任务。认领后 assign_status 从 assigned 变为 accepted。"""
    ensure_user_exists(db, executor_id)
    task = db.get(TestTask, task_id)
    if not task or task.is_deleted == 1:
        raise HTTPException(status_code=404, detail="测试任务不存在")

    assignee = db.scalar(
        select(TestTaskAssignee).where(
            TestTaskAssignee.task_id == task_id,
            TestTaskAssignee.assignee_id == executor_id,
        )
    )
    if not assignee:
        raise HTTPException(status_code=403, detail="你不是该任务的执行人，不能认领")

    assignee.assign_status = "accepted"
    assignee.assigned_at = func.now()
    if task.status == "assigned":
        task.status = "running"
    db.commit()
    return {"message": "任务已认领", "task_id": task_id, "assign_status": "accepted"}


def count_execution_status(db: Session, task_id: int, status: str) -> int:
    return db.scalar(
        select(func.count()).select_from(TestExecutionRecord).where(
            TestExecutionRecord.task_id == task_id,
            TestExecutionRecord.execution_status == status,
        )
    ) or 0


def enrich_executions(db: Session, executions: list[TestExecutionRecord]) -> list[dict]:
    """给执行记录附带用例节点标题与优先级，提升前端可读性。"""
    if not executions:
        return []

    node_ids = list({execution.case_node_id for execution in executions if execution.case_node_id})
    nodes = list(
        db.scalars(select(TestCaseNode).where(TestCaseNode.node_id.in_(node_ids), TestCaseNode.is_deleted == 0)).all()
    )
    node_map = {node.node_id: node for node in nodes}

    result = []
    for execution in executions:
        snapshot = execution.case_node_snapshot or {}
        node = node_map.get(execution.case_node_id)
        # 节点被逻辑删除后 node 查不到；快照仍能展示标题，但标记为已失效。
        case_node_deleted = bool(snapshot) and node is None and execution.case_node_snapshot is not None
        item = {
            "execution_id": execution.execution_id,
            "task_id": execution.task_id,
            "case_node_id": execution.case_node_id,
            "case_node_title": snapshot.get("title") or (node.title if node else None),
            "case_node_priority": snapshot.get("priority") or (node.priority if node else None),
            "case_node_deleted": case_node_deleted,
            "executor_id": execution.executor_id,
            "execution_status": execution.execution_status,
            "actual_result": execution.actual_result,
            "bug_description": execution.bug_description,
            "sync_status": execution.sync_status,
            "sync_version": execution.sync_version,
            "executed_at": execution.executed_at,
            "synced_at": execution.synced_at,
            "created_at": execution.created_at,
            "updated_at": execution.updated_at,
            "case_node_snapshot": snapshot or None,
        }
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# 任务目录 / 子任务 / 执行树
# ---------------------------------------------------------------------------

def _user_name_map(db: Session, user_ids: set[int]) -> dict[int, str]:
    """批量取用户名映射，避免逐个查询。"""
    if not user_ids:
        return {}
    users = list(
        db.scalars(select(User).where(User.user_id.in_(user_ids), User.is_deleted == 0)).all()
    )
    return {user.user_id: user.real_name or user.username for user in users}


def _subtask_ids(db: Session, parent_id: int) -> list[int]:
    return list(
        db.scalars(
            select(TestTask.task_id)
            .where(TestTask.parent_id == parent_id, TestTask.is_deleted == 0)
            .order_by(TestTask.task_id.asc())
        ).all()
    )


def list_task_directories(
    db: Session,
    page: int,
    page_size: int,
    keyword: str | None = None,
) -> dict:
    """任务目录列表：父任务（或独立单层任务），附子任务聚合统计。"""
    # 目录 = parent_id 为空 或 本身是别人的父任务
    sub_parent_ids = list(
        db.scalars(select(TestTask.parent_id).where(TestTask.parent_id.is_not(None), TestTask.is_deleted == 0)).all()
    )
    conditions = [
        TestTask.is_deleted == 0,
        or_(TestTask.parent_id.is_(None), TestTask.task_id.in_(sub_parent_ids)),
    ]
    if keyword and keyword.strip():
        conditions.append(TestTask.task_name.like(f"%{keyword.strip()}%"))

    total = db.scalar(select(func.count()).select_from(TestTask).where(*conditions)) or 0
    directories = list(
        db.scalars(
            select(TestTask)
            .where(*conditions)
            .order_by(TestTask.task_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    if not directories:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    owner_ids = {dir_.owner_id for dir_ in directories if dir_.owner_id}
    name_map = _user_name_map(db, owner_ids)

    items = []
    for directory in directories:
        subtasks = _subtask_ids(db, directory.task_id)
        stats = _aggregate_subtask_stats(db, subtasks)
        items.append({
            "task_id": directory.task_id,
            "task_name": directory.task_name,
            "description": directory.description,
            "status": directory.status,
            "owner_id": directory.owner_id,
            "owner_name": name_map.get(directory.owner_id),
            "created_by": directory.created_by,
            "created_at": directory.created_at,
            "updated_at": directory.updated_at,
            "subtask_count": len(subtasks),
            **stats,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


def _aggregate_subtask_stats(db: Session, subtask_ids: list[int]) -> dict:
    """对一组子任务聚合执行统计：用例总数、已测数、通过数、通过率。"""
    if not subtask_ids:
        return {"total_cases": 0, "tested_count": 0, "passed_count": 0, "pass_rate": 0.0}

    # 每个子任务的独立用例数（case_node_id 去重）
    case_node_ids = set(
        db.scalars(
            select(TestExecutionRecord.case_node_id)
            .where(TestExecutionRecord.task_id.in_(subtask_ids))
            .distinct()
        ).all()
    )
    total_cases = len(case_node_ids)

    executed = list(
        db.scalars(
            select(TestExecutionRecord.execution_status)
            .where(TestExecutionRecord.task_id.in_(subtask_ids), TestExecutionRecord.executed_at.is_not(None))
        ).all()
    )
    tested_count = len(executed)
    passed_count = sum(1 for status in executed if status == "passed")
    pass_rate = round(passed_count / tested_count, 4) if tested_count else 0.0
    return {
        "total_cases": total_cases,
        "tested_count": tested_count,
        "passed_count": passed_count,
        "pass_rate": pass_rate,
    }


def list_subtasks(
    db: Session,
    parent_id: int,
    page: int,
    page_size: int,
    executor_id: int | None = None,
) -> dict:
    """目录下的子任务列表，含各自执行统计与负责人/执行人姓名。"""
    parent = db.get(TestTask, parent_id)
    if not parent or parent.is_deleted == 1:
        raise HTTPException(status_code=404, detail="目录不存在")

    conditions = [TestTask.parent_id == parent_id, TestTask.is_deleted == 0]
    if executor_id is not None:
        conditions.append(TestTask.task_id.in_(
            select(TestTaskAssignee.task_id).where(TestTaskAssignee.assignee_id == executor_id)
        ))

    total = db.scalar(select(func.count()).select_from(TestTask).where(*conditions)) or 0
    subtasks = list(
        db.scalars(
            select(TestTask)
            .where(*conditions)
            .order_by(TestTask.task_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    if not subtasks:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}

    subtask_ids = [t.task_id for t in subtasks]
    owner_ids = {t.owner_id for t in subtasks if t.owner_id}
    name_map = _user_name_map(db, owner_ids)

    # 执行人姓名：查 task→assignee→user
    assignee_rows = list(
        db.scalars(
            select(TestTaskAssignee).where(TestTaskAssignee.task_id.in_(subtask_ids))
        ).all()
    )
    assignee_user_ids = {row.assignee_id for row in assignee_rows}
    assignee_name_map = _user_name_map(db, assignee_user_ids)
    assignee_ids_by_task: dict[int, list[int]] = {}
    for row in assignee_rows:
        assignee_ids_by_task.setdefault(row.task_id, []).append(row.assignee_id)

    items = []
    for task in subtasks:
        stats = _aggregate_subtask_stats(db, [task.task_id])
        items.append({
            "task_id": task.task_id,
            "parent_id": task.parent_id,
            "parent_name": parent.task_name,
            "task_name": task.task_name,
            "description": task.description,
            "status": task.status,
            "owner_id": task.owner_id,
            "owner_name": name_map.get(task.owner_id),
            "start_time": task.start_time,
            "end_time": task.end_time,
            "created_by": task.created_by,
            "updated_by": task.updated_by,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "case_set_ids": list(
                db.scalars(select(TestTaskCaseSet.case_set_id).where(TestTaskCaseSet.task_id == task.task_id)).all()
            ),
            "assignee_ids": assignee_ids_by_task.get(task.task_id, []),
            "assignee_names": [assignee_name_map.get(uid, str(uid)) for uid in assignee_ids_by_task.get(task.task_id, [])],
            "total_executions": 0,
            "passed_count": stats["passed_count"],
            "failed_count": 0,
            "blocked_count": 0,
            "not_run_count": 0,
            **{k: stats[k] for k in ("total_cases", "tested_count", "pass_rate")},
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


def get_subtask_execution_tree(db: Session, task_id: int, executor_id: int) -> dict:
    """子任务的用例树 + 当前执行人的执行状态映射，供思维导图执行页使用。"""
    ensure_user_exists(db, executor_id)
    task = db.get(TestTask, task_id)
    if not task or task.is_deleted == 1:
        raise HTTPException(status_code=404, detail="子任务不存在")

    from app.services.case_service import get_case_tree

    case_set_ids = list(
        db.scalars(select(TestTaskCaseSet.case_set_id).where(TestTaskCaseSet.task_id == task_id)).all()
    )
    tree: list[dict] = []
    for case_set_id in case_set_ids:
        case_set = db.get(TestCaseSet, case_set_id)
        roots = get_case_tree(db, case_set_id)
        if not roots:
            continue
        # 多个用例集时，用一个目录根节点包起来，标明用例集名。
        if len(case_set_ids) > 1 or (case_set and case_set.name):
            tree.append({
                "node_id": -case_set_id,
                "case_set_id": case_set_id,
                "parent_id": None,
                "node_type": "folder",
                "title": case_set.name if case_set else f"用例集#{case_set_id}",
                "precondition": None,
                "test_steps": None,
                "expected_result": None,
                "priority": "P1",
                "sort_order": 0,
                "children": roots,
            })
        else:
            tree.extend(roots)

    executions = list_task_executions(db, task_id)
    my_executions = [item for item in executions if item["executor_id"] == executor_id]
    status_map: dict[str, str] = {
        str(item["case_node_id"]): item["execution_status"] for item in my_executions
    }

    assignee = db.scalar(
        select(TestTaskAssignee).where(
            TestTaskAssignee.task_id == task_id,
            TestTaskAssignee.assignee_id == executor_id,
        )
    )
    assign_status = assignee.assign_status if assignee else "assigned"

    parent_name = None
    if task.parent_id:
        parent = db.get(TestTask, task.parent_id)
        parent_name = parent.task_name if parent else None

    stats = _aggregate_subtask_stats(db, [task_id])
    return {
        "task_id": task_id,
        "task_name": task.task_name,
        "parent_id": task.parent_id,
        "parent_name": parent_name,
        "assign_status": assign_status,
        "case_set_ids": case_set_ids,
        "tree": tree,
        "status_map": status_map,
        "total_cases": stats["total_cases"],
        "tested_count": stats["tested_count"],
        "passed_count": stats["passed_count"],
    }
