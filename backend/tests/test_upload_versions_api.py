import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def upload_versions_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "upload-versions-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "upload-versions-secret-with-32-bytes")

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
        owner = models_module.User(
            username="owner", password_hash="x", role="user", department="eng"
        )
        grantee = models_module.User(
            username="grantee", password_hash="x", role="user", department="ops"
        )
        outsider = models_module.User(
            username="outsider", password_hash="x", role="user", department="ops"
        )
        session.add_all([owner, grantee, outsider])
        session.flush()

        session.add(
            models_module.FolderPermission(
                folder="/knowledge", grantee_user_id=grantee.id, can_edit=False
            )
        )
        session.add_all(
            [
                models_module.UploadRecord(
                    folder="/knowledge",
                    owner_id=owner.id,
                    is_public=False,
                    filename="guide.md",
                    version=1,
                    checksum_sha256="a" * 64,
                    object_key="k/a/v1/guide.md",
                    size_bytes=3,
                    parse_status="normal",
                    source_text="v1",
                ),
                models_module.UploadRecord(
                    folder="/knowledge",
                    owner_id=owner.id,
                    is_public=False,
                    filename="guide.md",
                    version=2,
                    checksum_sha256="b" * 64,
                    object_key="k/b/v2/guide.md",
                    size_bytes=3,
                    parse_status="normal",
                    source_text="v2",
                ),
            ]
        )
        session.commit()

    def auth_header(user_id: int, role: str) -> dict[str, str]:
        token = security_module.issue_access_token(
            user_id=user_id, role=role, token_version=0
        )
        return {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        yield {
            "client": client,
            "owner_headers": auth_header(1, "user"),
            "grantee_headers": auth_header(2, "user"),
            "outsider_headers": auth_header(3, "user"),
        }


def test_upload_versions_loaded_from_backend(upload_versions_context) -> None:
    client = upload_versions_context["client"]

    owner_response = client.get(
        "/uploads/2/versions", headers=upload_versions_context["owner_headers"]
    )
    assert owner_response.status_code == 200
    owner_versions = owner_response.json()
    assert [row["version_number"] for row in owner_versions] == [2, 1]

    grantee_response = client.get(
        "/uploads/2/versions", headers=upload_versions_context["grantee_headers"]
    )
    assert grantee_response.status_code == 200
    assert [row["version_number"] for row in grantee_response.json()] == [2, 1]


def test_upload_versions_reject_unauthorized_user(upload_versions_context) -> None:
    client = upload_versions_context["client"]

    forbidden = client.get(
        "/uploads/2/versions", headers=upload_versions_context["outsider_headers"]
    )
    assert forbidden.status_code == 403

    missing = client.get(
        "/uploads/999/versions", headers=upload_versions_context["owner_headers"]
    )
    assert missing.status_code == 404
