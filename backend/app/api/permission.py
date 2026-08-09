from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_admin_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, UserPasswordReset
from app.schemas.permission import PermissionUserOut, PermissionUserPageOut, PermissionUserUpdate, RoleOptionOut
from app.services.permission_service import (
    create_permission_user,
    get_permission_user,
    list_permission_users,
    list_role_options,
    reset_user_password,
    update_permission_user,
)

router = APIRouter(prefix="/api/permissions", tags=["权限管理"], dependencies=[Depends(require_admin_user)])


@router.get("/roles", response_model=list[RoleOptionOut])
def api_list_roles():
    return list_role_options()


@router.get("/users", response_model=PermissionUserPageOut)
def api_list_permission_users(
    keyword: str | None = Query(default=None),
    role_code: str | None = Query(default=None),
    is_active: int | None = Query(default=None, ge=0, le=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_permission_users(db, keyword, role_code, is_active, page, page_size)


@router.post("/users", response_model=PermissionUserOut)
def api_create_permission_user(data: UserCreate, db: Session = Depends(get_db)):
    return create_permission_user(db, data)


@router.get("/users/{user_id}", response_model=PermissionUserOut)
def api_get_permission_user(user_id: int, db: Session = Depends(get_db)):
    return get_permission_user(db, user_id)


@router.patch("/users/{user_id}", response_model=PermissionUserOut)
def api_update_permission_user(
    user_id: int,
    data: PermissionUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    return update_permission_user(db, user_id, data, current_user)


@router.post("/users/{user_id}/reset-password")
def api_reset_user_password(
    user_id: int,
    data: UserPasswordReset,
    db: Session = Depends(get_db),
):
    return reset_user_password(db, user_id, data.new_password)
