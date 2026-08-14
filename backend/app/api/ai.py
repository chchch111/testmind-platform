from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.ai import AiGenerateOut, AiGenerateRequest, AiGenerationRecordDetailOut, AiGenerationRecordOut
from app.services.ai_service import (
    generate_test_cases,
    get_generation_progress,
    get_generation_record_detail,
    list_generation_records,
    start_generate_test_cases,
)


router = APIRouter(prefix="/api/ai", tags=["AI自动生成测试用例"])


@router.post("/generate-case-set", response_model=AiGenerateOut)
def api_generate_case_set(
    data: AiGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.created_by = current_user.user_id
    return generate_test_cases(db, data)


@router.post("/generate-case-set-async")
def api_start_generate_case_set(
    data: AiGenerateRequest,
    current_user: User = Depends(get_current_active_user),
):
    return start_generate_test_cases(data, current_user.user_id)


@router.get("/generate-case-set-tasks/{task_id}")
def api_get_generate_case_set_progress(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    return get_generation_progress(task_id)


@router.get("/generation-records", response_model=list[AiGenerationRecordOut])
def api_list_generation_records(db: Session = Depends(get_db)):
    return list_generation_records(db)


@router.get("/generation-records/{generation_id}", response_model=AiGenerationRecordDetailOut)
def api_get_generation_record_detail(generation_id: int, db: Session = Depends(get_db)):
    return get_generation_record_detail(db, generation_id)
