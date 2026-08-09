import bcrypt
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import UserCreate
from app.schemas.permission import ROLE_OPTIONS, VALID_ROLE_CODES, PermissionUserUpdate


def list_role_options() -> list[dict[str, str]]:
    return ROLE_OPTIONS


def list_permission_users(
    db: Session,
    keyword: str | None,
    role_code: str | None,
    is_active: int | None,
    page: int,
    page_size: int,
) -> dict:
    conditions = [User.is_deleted == 0]
    if keyword:
        like_keyword = f"%{keyword.strip()}%"
        conditions.append(
            or_(
                User.username.like(like_keyword),
                User.real_name.like(like_keyword),
                User.email.like(like_keyword),
                User.phone.like(like_keyword),
            )
        )
    if role_code:
        if role_code not in VALID_ROLE_CODES:
            raise HTTPException(status_code=400, detail="角色编码不合法")
        conditions.append(User.role_code == role_code)
    if is_active is not None:
        conditions.append(User.is_active == is_active)

    total = db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    statement = (
        select(User)
        .where(*conditions)
        .order_by(User.user_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": list(db.scalars(statement).all()),
    }


def get_permission_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user or user.is_deleted == 1:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def update_permission_user(db: Session, user_id: int, data: PermissionUserUpdate, operator: User) -> User:
    user = get_permission_user(db, user_id)
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return user

    role_code = update_data.get("role_code")
    if role_code is not None:
        if role_code not in VALID_ROLE_CODES:
            raise HTTPException(status_code=400, detail="角色编码不合法")
        if user.user_id == operator.user_id and role_code != "admin":
            raise HTTPException(status_code=400, detail="不能移除当前登录用户的管理员角色")
        user.role_code = role_code

    is_active = update_data.get("is_active")
    if is_active is not None:
        if user.user_id == operator.user_id and is_active != 1:
            raise HTTPException(status_code=400, detail="不能禁用当前登录用户")
        user.is_active = is_active

    db.commit()
    db.refresh(user)
    return user


def create_permission_user(db: Session, data: UserCreate) -> User:
    if data.role_code not in VALID_ROLE_CODES:
        raise HTTPException(status_code=400, detail="角色编码不合法")

    existing = db.scalar(select(User).where(User.username == data.username))
    if existing and existing.is_deleted == 0:
        raise HTTPException(status_code=400, detail="用户名已存在")

    password_hash = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        username=data.username,
        password_hash=password_hash,
        real_name=data.real_name,
        role_code=data.role_code,
        email=data.email,
        phone=data.phone,
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(db: Session, user_id: int, new_password: str) -> dict:
    user = get_permission_user(db, user_id)
    user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.commit()
    return {"message": "密码已重置", "user_id": user_id, "username": user.username}
