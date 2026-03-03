import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select


@pytest.fixture
def editing_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "editing-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "edit-flow-secret-for-tests-32-bytes")

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
        users = {
            "owner": models_module.User(
                username="owner", password_hash="x", role="user", department="eng"
            ),
            "admin": models_module.User(
                username="admin", password_hash="x", role="admin", department="ops"
            ),
            "manager_eng": models_module.User(
                username="manager_eng",
                password_hash="x",
                role="dept_manager",
                department="eng",
            ),
            "manager_sales": models_module.User(
                username="manager_sales",
                password_hash="x",
                role="dept_manager",
                department="sales",
            ),
            "share_user": models_module.User(
                username="share_user",
                password_hash="x",
                role="user",
                department="eng",
            ),
            "outsider": models_module.User(
                username="outsider", password_hash="x", role="user", department="ops"
            ),
        }
        session.add_all(users.values())
        session.commit()
        for user in users.values():
            session.refresh(user)

        file_record = models_module.FileRecord(
            filename="team-plan.docx",
            owner_id=users["owner"].id,
            department="eng",
            current_version=1,
        )
        session.add(file_record)
        session.commit()
        session.refresh(file_record)

        base_version = models_module.FileVersion(
            file_id=file_record.id,
            version_number=1,
            content="base-v1",
            created_by=users["owner"].id,
        )
        session.add(base_version)
        session.commit()

        share = models_module.FileShare(
            file_id=file_record.id,
            grantee_user_id=users["share_user"].id,
            can_edit=True,
        )
        session.add(share)
        session.commit()

    def auth_header(user_key: str) -> dict[str, str]:
        user = users[user_key]
        token = security_module.issue_access_token(
            user_id=user.id, role=user.role, token_version=user.token_version
        )
        return {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        yield client, session_factory, models_module, auth_header


def _start_edit(client: TestClient, file_id: int, headers: dict[str, str]):
    return client.post(f"/files/{file_id}/edit/start", headers=headers)


def _save_callback(
    client: TestClient, file_id: int, token: str, status_code: int, content: str
):
    return client.post(
        f"/files/{file_id}/edit/callback",
        json={"token": token, "status": status_code, "content": content},
    )


def test_edit_start_permissions_allow_owner_admin_manager_and_shared(editing_context):
    client, _, _, auth_header = editing_context

    owner_start = _start_edit(client, 1, auth_header("owner"))
    assert owner_start.status_code == 200

    admin_start = _start_edit(client, 1, auth_header("admin"))
    assert admin_start.status_code == 200

    manager_start = _start_edit(client, 1, auth_header("manager_eng"))
    assert manager_start.status_code == 200

    shared_start = _start_edit(client, 1, auth_header("share_user"))
    assert shared_start.status_code == 200


def test_edit_start_rejects_unauthorized_users(editing_context):
    client, _, _, auth_header = editing_context

    outsider = _start_edit(client, 1, auth_header("outsider"))
    assert outsider.status_code == 403

    wrong_manager = _start_edit(client, 1, auth_header("manager_sales"))
    assert wrong_manager.status_code == 403


def test_callback_rejects_stale_version_tokens(editing_context):
    client, session_factory, models_module, auth_header = editing_context

    start = _start_edit(client, 1, auth_header("owner"))
    assert start.status_code == 200
    token = start.json()["session_token"]

    with session_factory() as session:
        file_row = session.scalar(
            select(models_module.FileRecord).where(models_module.FileRecord.id == 1)
        )
        assert file_row is not None
        file_row.current_version = 2
        session.add(file_row)
        session.commit()

    callback = _save_callback(client, 1, token, 2, "new text from stale session")
    assert callback.status_code == 409
    assert callback.json()["error"] == 1

    with session_factory() as session:
        versions = session.scalar(
            select(func.count())
            .select_from(models_module.FileVersion)
            .where(models_module.FileVersion.file_id == 1)
        )
        assert versions == 1


def test_callback_rejects_duplicate_save_without_duplicate_versions(
    editing_context, monkeypatch
):
    client, session_factory, models_module, auth_header = editing_context
    editing_router = importlib.import_module("app.routers.editing")

    queued: list[tuple[int, int]] = []

    def fake_queue(file_id: int, version_id: int) -> None:
        queued.append((file_id, version_id))

    monkeypatch.setattr(editing_router, "queue_reindex", fake_queue)

    start = _start_edit(client, 1, auth_header("owner"))
    assert start.status_code == 200
    token = start.json()["session_token"]

    first = _save_callback(client, 1, token, 2, "v2 content")
    assert first.status_code == 200
    assert first.json()["error"] == 0

    duplicate = _save_callback(client, 1, token, 2, "v2 content duplicate callback")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == 1

    with session_factory() as session:
        file_row = session.scalar(
            select(models_module.FileRecord).where(models_module.FileRecord.id == 1)
        )
        assert file_row is not None
        assert file_row.current_version == 2

        versions = session.scalars(
            select(models_module.FileVersion)
            .where(models_module.FileVersion.file_id == 1)
            .order_by(models_module.FileVersion.version_number.asc())
        ).all()
        assert len(versions) == 2
        assert versions[-1].content == "v2 content"

    assert queued == [(1, versions[-1].id)]


def test_callback_status6_persists_new_version_and_queues_reindex(
    editing_context, monkeypatch
):
    client, session_factory, models_module, auth_header = editing_context
    editing_router = importlib.import_module("app.routers.editing")

    queued: list[tuple[int, int]] = []

    def fake_queue(file_id: int, version_id: int) -> None:
        queued.append((file_id, version_id))

    monkeypatch.setattr(editing_router, "queue_reindex", fake_queue)

    start = _start_edit(client, 1, auth_header("owner"))
    assert start.status_code == 200
    token = start.json()["session_token"]

    callback = _save_callback(client, 1, token, 6, "v2 from status6")
    assert callback.status_code == 200
    assert callback.json() == {"error": 0}

    with session_factory() as session:
        file_row = session.scalar(
            select(models_module.FileRecord).where(models_module.FileRecord.id == 1)
        )
        assert file_row is not None
        assert file_row.current_version == 2

        latest = session.scalar(
            select(models_module.FileVersion).where(
                models_module.FileVersion.file_id == 1,
                models_module.FileVersion.version_number == 2,
            )
        )
        assert latest is not None
        assert latest.content == "v2 from status6"

    assert len(queued) == 1
    assert queued[0][0] == 1
