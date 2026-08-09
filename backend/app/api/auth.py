from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserInfoOut
from app.services.auth_service import authenticate_user, create_access_token, to_user_info

router = APIRouter(prefix="/api/auth", tags=["登录认证"])


@router.post("/login", response_model=LoginResponse)
def api_login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.username, data.password)
    access_token, expires_at = create_access_token(user)
    return LoginResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=to_user_info(user),
    )


@router.get("/me", response_model=UserInfoOut)
def api_get_me(current_user: User = Depends(get_current_active_user)):
    return to_user_info(current_user)


@router.post("/logout")
def api_logout():
    return {"message": "已退出登录"}
