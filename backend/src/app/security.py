import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings


def hash_password(password: str, *, salt: str | None = None) -> str:
    effective_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), effective_salt.encode("utf-8"), 120_000
    )
    return f"{effective_salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split("$", 1)
    except ValueError:
        return False
    calculated = hash_password(password, salt=salt).split("$", 1)[1]
    return hmac.compare_digest(calculated, expected)


def issue_access_token(*, user_id: int, role: str, token_version: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "token_version": token_version,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def issue_refresh_token(
    *, user_id: int, token_version: int, jti: str | None = None
) -> tuple[str, str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    token_jti = jti or secrets.token_hex(16)
    expires_at = now + timedelta(seconds=settings.refresh_token_ttl_seconds)
    payload = {
        "sub": str(user_id),
        "token_version": token_version,
        "type": "refresh",
        "jti": token_jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded, token_jti, expires_at


def decode_token(token: str) -> dict[str, object]:
    settings = get_settings()
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    return dict(payload)
