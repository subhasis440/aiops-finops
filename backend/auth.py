import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import db

JWT_ALGORITHM = "HS256"
_bearer = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "local-dev-secret")


def _jwt_exp_hours() -> int:
    raw = os.getenv("JWT_EXP_HOURS", "24")
    try:
        return max(1, int(raw))
    except ValueError:
        return 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, email: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_jwt_exp_hours())
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expires_at,
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        decoded = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please login again.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        ) from exc

    if not isinstance(decoded, dict) or "sub" not in decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )
    return decoded


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token.",
        )

    payload = decode_access_token(credentials.credentials)
    user_id = str(payload.get("sub"))
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for token.",
        )
    return user


async def get_current_user_from_token(token: str) -> dict[str, Any]:
    payload = decode_access_token(token)
    user_id = str(payload.get("sub"))
    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for token.",
        )
    return user
