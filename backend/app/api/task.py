from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.task import ExecutionOut, ExecutionUpdate, ExecutorTaskOut, TaskCreate, TaskDetailOut, TaskOut
from app.services.task_service import (
    create_task,
    get_executor_tasks,
    get_task_detail,
    list_task_executions,
    list_tasks,
    update_execution,
)


router = APIRouter(prefix="/api", tags=["测试任务管理"])


@router.post("/tasks", response_model=TaskDetailOut)
def api_create_task(data: TaskCreate, db: Session = Depends(get_db)):
    return create_task(db, data)


@router.get("/tasks", response_model=list[TaskOut])
def api_list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_tasks(db, page, page_size)


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
def api_get_task_detail(task_id: int, db: Session = Depends(get_db)):
    return get_task_detail(db, task_id)


@router.get("/tasks/{task_id}/executions", response_model=list[ExecutionOut])
def api_list_task_executions(task_id: int, db: Session = Depends(get_db)):
    return list_task_executions(db, task_id)


@router.get("/executors/{executor_id}/tasks", response_model=list[ExecutorTaskOut])
def api_get_executor_tasks(executor_id: int, db: Session = Depends(get_db)):
    return get_executor_tasks(db, executor_id)


@router.put("/executions/{execution_id}", response_model=ExecutionOut)
def api_update_execution(execution_id: int, data: ExecutionUpdate, db: Session = Depends(get_db)):
    return update_execution(db, execution_id, data)
