import base64
import hashlib
import hmac
import json
import time

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserInfoOut


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username, User.is_deleted == 0))
    if not user or user.is_active != 1:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return user


def create_access_token(user: User) -> tuple[str, int]:
    expires_at = int(time.time()) + settings.auth_token_expire_minutes * 60
    payload = {
        "user_id": user.user_id,
        "username": user.username,
        "role_code": user.role_code,
        "exp": expires_at,
    }
    payload_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_part = base64_url_encode(payload_text.encode("utf-8"))
    signature = sign_token_payload(payload_part)
    return f"{payload_part}.{signature}", expires_at


def parse_access_token(token: str) -> dict:
    try:
        payload_part, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录") from exc

    expected_signature = sign_token_payload(payload_part)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")

    try:
        payload = json.loads(base64_url_decode(payload_part).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录") from exc

    if int(payload.get("exp") or 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="登录状态已过期，请重新登录")
    return payload


def get_user_by_token(db: Session, token: str) -> User:
    payload = parse_access_token(token)
    user = db.get(User, payload.get("user_id"))
    if not user or user.is_deleted == 1 or user.is_active != 1:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    return user


def to_user_info(user: User) -> UserInfoOut:
    return UserInfoOut(
        user_id=user.user_id,
        username=user.username,
        real_name=user.real_name,
        role_code=user.role_code,
    )


def sign_token_payload(payload_part: str) -> str:
    digest = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        payload_part.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64_url_encode(digest)


def base64_url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def base64_url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
