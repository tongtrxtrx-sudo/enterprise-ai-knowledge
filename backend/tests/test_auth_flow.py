import importlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture
def auth_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "auth-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-auth-flow-32-bytes")
    monkeypatch.setenv("REFRESH_COOKIE_SECURE", "true")
    monkeypatch.setenv("REFRESH_COOKIE_HTTPONLY", "true")
    monkeypatch.setenv("REFRESH_COOKIE_SAMESITE", "strict")

    config_module = importlib.import_module("app.config")
    db_module = importlib.import_module("app.db")
    security_module = importlib.import_module("app.security")
    models_module = importlib.import_module("app.models")
    main_module = importlib.import_module("app.main")

    config_module.get_settings.cache_clear()
    db_module.get_engine.cache_clear()
    importlib.reload(db_module)
    importlib.reload(models_module)
    importlib.reload(security_module)
    importlib.reload(main_module)

    app = main_module.create_app()
    session_factory = db_module.get_session_factory()
    password_hash = security_module.hash_password("password123")

    with session_factory() as session:
        user = models_module.User(
            username="alice",
            password_hash=password_hash,
            role="user",
            token_version=1,
        )
        admin = models_module.User(
            username="root",
            password_hash=security_module.hash_password("admin123"),
            role="admin",
            token_version=1,
        )
        session.add(user)
        session.add(admin)
        session.commit()

    with TestClient(app) as client:
        yield client, session_factory, models_module, security_module


def test_login_returns_tokens_and_secure_cookie(auth_context) -> None:
    client, _, _, _ = auth_context
    response = client.post(
        "/auth/login", json={"username": "alice", "password": "password123"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]

    set_cookie = response.headers.get("set-cookie", "")
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie


def test_refresh_rejects_blacklisted_jti(auth_context) -> None:
    client, session_factory, models_module, security_module = auth_context
    login = client.post(
        "/auth/login", json={"username": "alice", "password": "password123"}
    )
    refresh_token = login.json()["refresh_token"]
    client.cookies.set("refresh_token", refresh_token)
    payload = security_module.decode_token(refresh_token)

    with session_factory() as session:
        user = session.scalar(
            select(models_module.User).where(models_module.User.username == "alice")
        )
        assert user is not None
        blacklist = models_module.RefreshTokenBlacklist(
            jti=str(payload["jti"]),
            user_id=user.id,
            expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=UTC),
        )
        session.add(blacklist)
        session.commit()

    refresh = client.post("/auth/refresh")
    assert refresh.status_code == 401
    assert refresh.json()["detail"] == "Refresh token is blacklisted"


def test_refresh_rejects_stale_token_version(auth_context) -> None:
    client, session_factory, models_module, _ = auth_context
    login = client.post(
        "/auth/login", json={"username": "alice", "password": "password123"}
    )
    assert login.status_code == 200
    client.cookies.set("refresh_token", login.json()["refresh_token"])

    with session_factory() as session:
        user = session.scalar(
            select(models_module.User).where(models_module.User.username == "alice")
        )
        assert user is not None
        user.token_version += 1
        session.add(user)
        session.commit()

    refresh = client.post("/auth/refresh")
    assert refresh.status_code == 401
    assert refresh.json()["detail"] == "Stale token version"


def test_logout_persists_refresh_jti(auth_context) -> None:
    client, session_factory, models_module, security_module = auth_context
    login = client.post(
        "/auth/login", json={"username": "alice", "password": "password123"}
    )
    refresh_token = login.json()["refresh_token"]
    client.cookies.set("refresh_token", refresh_token)
    refresh_payload = security_module.decode_token(refresh_token)

    logout = client.post("/auth/logout")
    assert logout.status_code == 200

    with session_factory() as session:
        blacklisted = session.scalar(
            select(models_module.RefreshTokenBlacklist).where(
                models_module.RefreshTokenBlacklist.jti == str(refresh_payload["jti"])
            )
        )
        assert blacklisted is not None


def test_role_check_rejects_unauthorized_user_by_default(auth_context) -> None:
    client, _, _, _ = auth_context
    login = client.post(
        "/auth/login", json={"username": "alice", "password": "password123"}
    )
    access_token = login.json()["access_token"]

    forbidden = client.get(
        "/auth/admin-only", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert forbidden.status_code == 403


def test_session_returns_user_and_permission_state(auth_context) -> None:
    client, _, _, _ = auth_context
    login = client.post(
        "/auth/login", json={"username": "root", "password": "admin123"}
    )
    access_token = login.json()["access_token"]

    response = client.get(
        "/auth/session", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["username"] == "root"
    assert payload["user"]["role"] == "admin"
    assert payload["permissions"]["can_access_admin"] is True
