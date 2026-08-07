from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.case import TestCaseNode, TestCaseSet
from app.models.task import TestExecutionRecord, TestTask, TestTaskAssignee, TestTaskCaseSet
from app.schemas.task import ExecutionUpdate, TaskCreate
from app.services.case_service import ensure_user_exists


VALID_EXECUTION_STATUS = {"not_run", "passed", "failed", "blocked"}


def create_task(db: Session, data: TaskCreate) -> dict:
    ensure_user_exists(db, data.created_by)

    case_set_ids = list(dict.fromkeys(data.case_set_ids))
    assignee_ids = list(dict.fromkeys(data.assignee_ids))

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

    task = TestTask(
        task_name=data.task_name,
        description=data.description,
        status="assigned",
        start_time=data.start_time,
        end_time=data.end_time,
        created_by=data.created_by,
    )
    db.add(task)
    db.flush()

    for case_set_id in case_set_ids:
        db.add(TestTaskCaseSet(task_id=task.task_id, case_set_id=case_set_id))

    for assignee_id in assignee_ids:
        db.add(TestTaskAssignee(task_id=task.task_id, assignee_id=assignee_id, assign_status="assigned"))
        for node in case_nodes:
            db.add(
                TestExecutionRecord(
                    task_id=task.task_id,
                    case_node_id=node.node_id,
                    executor_id=assignee_id,
                    execution_status="not_run",
                    sync_status="synced",
                    sync_version=1,
                )
            )

    db.commit()
    return get_task_detail(db, task.task_id)


def list_tasks(db: Session, page: int, page_size: int) -> list[TestTask]:
    statement = (
        select(TestTask)
        .where(TestTask.is_deleted == 0)
        .order_by(TestTask.task_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(statement).all())


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


def list_task_executions(db: Session, task_id: int) -> list[TestExecutionRecord]:
    task = db.get(TestTask, task_id)
    if not task or task.is_deleted == 1:
        raise HTTPException(status_code=404, detail="测试任务不存在")

    statement = (
        select(TestExecutionRecord)
        .where(TestExecutionRecord.task_id == task_id)
        .order_by(TestExecutionRecord.executor_id.asc(), TestExecutionRecord.execution_id.asc())
    )
    return list(db.scalars(statement).all())


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
    result = []
    for task in tasks:
        executions = list(
            db.scalars(
                select(TestExecutionRecord)
                .where(TestExecutionRecord.task_id == task.task_id, TestExecutionRecord.executor_id == executor_id)
                .order_by(TestExecutionRecord.execution_id.asc())
            ).all()
        )
        result.append({"task": task, "executions": executions})
    return result


def update_execution(db: Session, execution_id: int, data: ExecutionUpdate) -> TestExecutionRecord:
    ensure_user_exists(db, data.executor_id)

    if data.execution_status not in VALID_EXECUTION_STATUS:
        raise HTTPException(status_code=400, detail="execution_status只能是not_run/passed/failed/blocked")

    execution = db.get(TestExecutionRecord, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    if execution.executor_id != data.executor_id:
        raise HTTPException(status_code=403, detail="只能更新分配给自己的执行记录")

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


def count_execution_status(db: Session, task_id: int, status: str) -> int:
    return db.scalar(
        select(func.count()).select_from(TestExecutionRecord).where(
            TestExecutionRecord.task_id == task_id,
            TestExecutionRecord.execution_status == status,
        )
    ) or 0
