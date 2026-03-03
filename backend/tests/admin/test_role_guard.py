import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_guard_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "admin-guard.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "admin-guard-secret-32-bytes-long")

    config_module = importlib.import_module("app.config")
    db_module = importlib.import_module("app.db")
    models_module = importlib.import_module("app.models")
    security_module = importlib.import_module("app.security")
    main_module = importlib.import_module("app.main")

    config_module.get_settings.cache_clear()
    db_module.get_engine.cache_clear()
    importlib.reload(db_module)
    importlib.reload(models_module)
    importlib.reload(security_module)
    importlib.reload(main_module)

    app = main_module.create_app()
    session_factory = db_module.get_session_factory()

    with session_factory() as session:
        user = models_module.User(username="alice", password_hash="x", role="user")
        admin = models_module.User(username="root", password_hash="x", role="admin")
        session.add_all([user, admin])
        session.commit()
        session.refresh(user)
        session.refresh(admin)

    with TestClient(app) as client:
        yield client, models_module, security_module


def test_admin_folder_permission_api_rejects_non_admin(admin_guard_context) -> None:
    client, _, security_module = admin_guard_context
    token = security_module.issue_access_token(user_id=1, role="user", token_version=0)

    response = client.post(
        "/admin/folder-permissions",
        json={"folder": "team-a", "grantee_user_id": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
