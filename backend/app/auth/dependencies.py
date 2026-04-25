"""FastAPI dependencies for resolving the current user from a Bearer token."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.db.base import get_db
from app.db.models import User


bearer_scheme = HTTPBearer(auto_error=False)


def _credentials_from_request(
    creds: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if creds is None:
        return None
    if creds.scheme.lower() != "bearer":
        return None
    return creds.credentials


def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = _credentials_from_request(creds)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject"
        )
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad subject")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    request.state.user_id = user.id
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user


def get_optional_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of 401 when no/invalid token."""
    token = _credentials_from_request(creds)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except Exception:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user = db.get(User, int(sub))
    except (TypeError, ValueError):
        return None
    if user is None or not user.is_active:
        return None
    request.state.user_id = user.id
    return user
