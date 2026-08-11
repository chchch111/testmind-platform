from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.task import (
    ExecutionOut,
    ExecutionUpdate,
    ExecutorTaskOut,
    SubtasksPageOut,
    SubtaskOut,
    TaskCreate,
    TaskDetailOut,
    TaskDirectoryPageOut,
    TaskPageOut,
    TaskTreeStatusOut,
)
from app.services.task_service import (
    assign_task,
    cancel_task,
    create_task,
    delete_task,
    get_executor_tasks,
    get_subtask_execution_tree,
    get_task_detail,
    get_task_report,
    list_subtasks,
    list_task_directories,
    list_task_executions,
    list_tasks,
    update_execution,
)


router = APIRouter(prefix="/api", tags=["测试任务管理"])


@router.post("/tasks", response_model=TaskDetailOut)
def api_create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.created_by = current_user.user_id
    return create_task(db, data)


@router.get("/tasks", response_model=TaskPageOut)
def api_list_tasks(
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_tasks(db, page, page_size, keyword, status)


@router.get("/tasks/directories", response_model=TaskDirectoryPageOut)
def api_list_task_directories(
    keyword: str | None = Query(default=None),
    owner_id: int | None = Query(default=None),
    assignee_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_task_directories(db, page, page_size, keyword, owner_id, assignee_id, status)


@router.get("/tasks/{parent_id}/subtasks", response_model=SubtasksPageOut)
def api_list_subtasks(
    parent_id: int,
    executor_id: int | None = Query(default=None),
    owner_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_subtasks(db, parent_id, page, page_size, executor_id, owner_id, status)


@router.get("/tasks/{task_id}/execution-tree", response_model=TaskTreeStatusOut)
def api_get_task_execution_tree(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return get_subtask_execution_tree(db, task_id, current_user.user_id)


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
def api_get_task_detail(task_id: int, db: Session = Depends(get_db)):
    return get_task_detail(db, task_id)


@router.post("/tasks/{task_id}/cancel")
def api_cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return cancel_task(db, task_id, current_user.user_id)


@router.post("/tasks/{task_id}/assign")
def api_assign_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return assign_task(db, task_id, current_user.user_id)


@router.delete("/tasks/{task_id}")
def api_delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return delete_task(db, task_id, current_user.user_id)


@router.get("/tasks/{task_id}/executions", response_model=list[ExecutionOut])
def api_list_task_executions(task_id: int, db: Session = Depends(get_db)):
    return list_task_executions(db, task_id)


@router.get("/tasks/{task_id}/report")
def api_get_task_report(task_id: int, db: Session = Depends(get_db)):
    return get_task_report(db, task_id)


@router.get("/executors/{executor_id}/tasks", response_model=list[ExecutorTaskOut])
def api_get_executor_tasks(
    executor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role_code != "admin" and executor_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="只能同步自己的执行任务")
    return get_executor_tasks(db, executor_id)


@router.put("/executions/{execution_id}", response_model=ExecutionOut)
def api_update_execution(
    execution_id: int,
    data: ExecutionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role_code != "admin":
        data.executor_id = current_user.user_id
    return update_execution(db, execution_id, data)
