from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_token


def get_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="请先登录")
    return token.strip()


def get_current_active_user(token: str = Depends(get_bearer_token), db: Session = Depends(get_db)) -> User:
    return get_user_by_token(db, token)


def require_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role_code != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可访问")
    return current_user
