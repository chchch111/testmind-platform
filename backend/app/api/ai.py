from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.ai import AiGenerateOut, AiGenerateRequest, AiGenerationRecordOut
from app.services.ai_service import generate_test_cases, list_generation_records


router = APIRouter(prefix="/api/ai", tags=["AI自动生成测试用例"])


@router.post("/generate-case-set", response_model=AiGenerateOut)
def api_generate_case_set(
    data: AiGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data.created_by = current_user.user_id
    return generate_test_cases(db, data)


@router.get("/generation-records", response_model=list[AiGenerationRecordOut])
def api_list_generation_records(db: Session = Depends(get_db)):
    return list_generation_records(db)
