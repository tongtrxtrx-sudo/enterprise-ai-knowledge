import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def admin_state_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "admin-state-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "admin-state-secret-with-32-byte-length")

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
        admin = models_module.User(
            username="admin", password_hash="x", role="admin", department="knowledge"
        )
        manager = models_module.User(
            username="manager", password_hash="x", role="dept_manager", department="ops"
        )
        member = models_module.User(
            username="member", password_hash="x", role="user", department="ops"
        )
        session.add_all([admin, manager, member])
        session.flush()

        session.add_all(
            [
                models_module.AuditLog(
                    actor_user_id=admin.id,
                    action="folder_permission_updated",
                    target_type="folder_permission",
                    target_id=10,
                ),
                models_module.AuditLog(
                    actor_user_id=admin.id,
                    action="upload_visibility_updated",
                    target_type="upload",
                    target_id=20,
                ),
            ]
        )
        session.commit()

    def auth_header(role: str, user_id: int) -> dict[str, str]:
        token = security_module.issue_access_token(
            user_id=user_id, role=role, token_version=0
        )
        return {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        yield {
            "client": client,
            "admin_headers": auth_header("admin", 1),
            "user_headers": auth_header("user", 3),
        }


def test_admin_state_endpoints_return_backend_data(admin_state_context) -> None:
    client = admin_state_context["client"]
    headers = admin_state_context["admin_headers"]

    users_response = client.get("/admin/users", headers=headers)
    assert users_response.status_code == 200
    users = users_response.json()
    assert [row["username"] for row in users] == ["admin", "manager", "member"]
    assert all(row["status"] == "active" for row in users)

    departments_response = client.get("/admin/departments", headers=headers)
    assert departments_response.status_code == 200
    departments = {row["name"]: row for row in departments_response.json()}
    assert departments["knowledge"]["member_count"] == 1
    assert departments["ops"]["member_count"] == 2
    assert departments["ops"]["manager_user_id"] == 2

    audits_response = client.get("/admin/audit-states", headers=headers)
    assert audits_response.status_code == 200
    audits = audits_response.json()
    assert audits[0]["action"] == "upload_visibility_updated"
    assert audits[1]["action"] == "folder_permission_updated"


def test_admin_state_endpoints_reject_non_admin(admin_state_context) -> None:
    client = admin_state_context["client"]
    user_headers = admin_state_context["user_headers"]

    assert client.get("/admin/users", headers=user_headers).status_code == 403
    assert client.get("/admin/departments", headers=user_headers).status_code == 403
    assert client.get("/admin/audit-states", headers=user_headers).status_code == 403
