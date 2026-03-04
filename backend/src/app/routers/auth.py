from datetime import UTC, datetime
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db_session
from app.deps import get_current_user, require_roles
from app.models import RefreshTokenBlacklist, User
from app.schemas.auth import (
    LoginRequest,
    SessionPermissionsResponse,
    SessionStateResponse,
    SessionUserResponse,
    TokenPairResponse,
)
from app.security import (
    decode_token,
    issue_access_token,
    issue_refresh_token,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _build_permissions(role: str) -> dict[str, bool]:
    return {
        "can_upload": True,
        "can_view_versions": True,
        "can_edit_file": True,
        "can_access_admin": role == "admin",
    }


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    same_site = cast(
        Literal["lax", "strict", "none"], settings.refresh_cookie_samesite.lower()
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=settings.refresh_cookie_httponly,
        secure=settings.refresh_cookie_secure,
        samesite=same_site,
        path="/",
    )


def _read_refresh_cookie(request: Request) -> str:
    settings = get_settings()
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )
    return refresh_token


def _assert_refresh_token_not_blacklisted(session: Session, jti: str) -> None:
    is_blacklisted = session.scalar(
        select(RefreshTokenBlacklist).where(RefreshTokenBlacklist.jti == jti)
    )
    if is_blacklisted is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is blacklisted",
        )


def _assert_token_version(user: User, payload: dict[str, object]) -> None:
    token_version = int(str(payload.get("token_version", "-1")))
    if token_version != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Stale token version"
        )


def _blacklist_jti(
    session: Session, *, jti: str, user_id: int, expires_at: datetime
) -> None:
    entry = RefreshTokenBlacklist(jti=jti, user_id=user_id, expires_at=expires_at)
    session.add(entry)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()


@router.post("/login", response_model=TokenPairResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_db_session),
) -> TokenPairResponse:
    user = session.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token = issue_access_token(
        user_id=user.id, role=user.role, token_version=user.token_version
    )
    refresh_token, _, _ = issue_refresh_token(
        user_id=user.id, token_version=user.token_version
    )
    _set_refresh_cookie(response, refresh_token)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(
    request: Request, response: Response, session: Session = Depends(get_db_session)
) -> TokenPairResponse:
    raw_refresh_token = _read_refresh_cookie(request)
    try:
        payload = decode_token(raw_refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )

    jti = str(payload.get("jti", ""))
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token identifier",
        )
    _assert_refresh_token_not_blacklisted(session, jti)

    user_id = int(str(payload.get("sub", "0")))
    user = session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    _assert_token_version(user, payload)

    old_exp = int(str(payload.get("exp", "0")))
    _blacklist_jti(
        session,
        jti=jti,
        user_id=user.id,
        expires_at=datetime.fromtimestamp(old_exp, tz=UTC),
    )

    access_token = issue_access_token(
        user_id=user.id, role=user.role, token_version=user.token_version
    )
    new_refresh_token, _, _ = issue_refresh_token(
        user_id=user.id, token_version=user.token_version
    )
    _set_refresh_cookie(response, new_refresh_token)
    return TokenPairResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout")
def logout(
    request: Request, response: Response, session: Session = Depends(get_db_session)
) -> dict[str, str]:
    raw_refresh_token = _read_refresh_cookie(request)
    try:
        payload = decode_token(raw_refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )

    jti = str(payload.get("jti", ""))
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token identifier",
        )

    user_id = int(str(payload.get("sub", "0")))
    exp = int(str(payload.get("exp", "0")))
    _blacklist_jti(
        session,
        jti=jti,
        user_id=user_id,
        expires_at=datetime.fromtimestamp(exp, tz=UTC),
    )

    settings = get_settings()
    response.delete_cookie(settings.refresh_cookie_name, path="/")
    return {"status": "logged_out"}


@router.get("/session", response_model=SessionStateResponse)
def session_state(user: User = Depends(get_current_user)) -> SessionStateResponse:
    return SessionStateResponse(
        user=SessionUserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            department=user.department,
        ),
        permissions=SessionPermissionsResponse(**_build_permissions(user.role)),
    )


@router.get("/admin-only")
def admin_only(_: User = Depends(require_roles("admin"))) -> dict[str, str]:
    return {"status": "ok"}
