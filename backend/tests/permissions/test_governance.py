import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture
def governance_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "governance-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("JWT_SECRET", "governance-secret-with-32-byte-length")

    config_module = importlib.import_module("app.config")
    db_module = importlib.import_module("app.db")
    models_module = importlib.import_module("app.models")
    security_module = importlib.import_module("app.security")
    main_module = importlib.import_module("app.main")
    retrieval_module = importlib.import_module("app.indexing.retrieval")
    permission_service = importlib.import_module("app.permissions.service")

    config_module.get_settings.cache_clear()
    db_module.get_engine.cache_clear()
    importlib.reload(db_module)
    importlib.reload(models_module)
    importlib.reload(security_module)
    importlib.reload(retrieval_module)
    importlib.reload(permission_service)
    importlib.reload(main_module)

    app = main_module.create_app()
    session_factory = db_module.get_session_factory()

    with session_factory() as session:
        admin = models_module.User(username="admin", password_hash="x", role="admin")
        owner = models_module.User(username="owner", password_hash="x", role="user")
        granted = models_module.User(username="granted", password_hash="x", role="user")
        outsider = models_module.User(
            username="outsider", password_hash="x", role="user"
        )
        session.add_all([admin, owner, granted, outsider])
        session.commit()
        session.refresh(admin)
        session.refresh(owner)
        session.refresh(granted)
        session.refresh(outsider)

        upload_owned = models_module.UploadRecord(
            folder="owned-folder",
            owner_id=owner.id,
            is_public=False,
            filename="owned.txt",
            version=1,
            checksum_sha256="a" * 64,
            object_key="owned/a/v1/owned.txt",
            size_bytes=1,
            parse_status="normal",
            source_text="owned source",
        )
        upload_grant = models_module.UploadRecord(
            folder="grant-folder",
            owner_id=outsider.id,
            is_public=False,
            filename="granted.txt",
            version=1,
            checksum_sha256="b" * 64,
            object_key="grant/b/v1/granted.txt",
            size_bytes=1,
            parse_status="normal",
            source_text="granted source",
        )
        upload_public = models_module.UploadRecord(
            folder="public-folder",
            owner_id=outsider.id,
            is_public=True,
            filename="public.txt",
            version=1,
            checksum_sha256="c" * 64,
            object_key="public/c/v1/public.txt",
            size_bytes=1,
            parse_status="normal",
            source_text="public source",
        )
        upload_hidden = models_module.UploadRecord(
            folder="hidden-folder",
            owner_id=outsider.id,
            is_public=False,
            filename="hidden.txt",
            version=1,
            checksum_sha256="d" * 64,
            object_key="hidden/d/v1/hidden.txt",
            size_bytes=1,
            parse_status="normal",
            source_text="hidden source",
        )
        session.add_all([upload_owned, upload_grant, upload_public, upload_hidden])
        session.commit()
        session.refresh(upload_owned)
        session.refresh(upload_grant)
        session.refresh(upload_public)
        session.refresh(upload_hidden)

        session.add_all(
            [
                models_module.DocChunk(
                    upload_id=upload_owned.id,
                    chunk_index=0,
                    content="alpha owned",
                    content_tsv="alpha owned",
                    content_vector=[0.1, 0.0],
                    vector_ready=True,
                    read_allow="",
                ),
                models_module.DocChunk(
                    upload_id=upload_grant.id,
                    chunk_index=0,
                    content="alpha granted",
                    content_tsv="alpha granted",
                    content_vector=[0.1, 0.0],
                    vector_ready=True,
                    read_allow="",
                ),
                models_module.DocChunk(
                    upload_id=upload_public.id,
                    chunk_index=0,
                    content="alpha public",
                    content_tsv="alpha public",
                    content_vector=[0.1, 0.0],
                    vector_ready=True,
                    read_allow="",
                ),
                models_module.DocChunk(
                    upload_id=upload_hidden.id,
                    chunk_index=0,
                    content="alpha hidden",
                    content_tsv="alpha hidden",
                    content_vector=[0.1, 0.0],
                    vector_ready=True,
                    read_allow="",
                ),
            ]
        )
        session.commit()

    def token_for(user_id: int, role: str) -> str:
        return security_module.issue_access_token(
            user_id=user_id, role=role, token_version=0
        )

    with TestClient(app) as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "models": models_module,
            "retrieval": retrieval_module,
            "permission_service": permission_service,
            "tokens": {
                "admin": token_for(1, "admin"),
                "owner": token_for(2, "user"),
                "granted": token_for(3, "user"),
                "outsider": token_for(4, "user"),
            },
        }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_default_share_can_edit_true_unless_explicit_false(governance_context) -> None:
    client = governance_context["client"]
    tokens = governance_context["tokens"]

    default_response = client.post(
        "/admin/folder-permissions",
        json={"folder": "grant-folder", "grantee_user_id": 3},
        headers=_auth(tokens["admin"]),
    )
    assert default_response.status_code == 201
    assert default_response.json()["can_edit"] is True

    explicit_false = client.post(
        "/admin/folder-permissions",
        json={"folder": "hidden-folder", "grantee_user_id": 3, "can_edit": False},
        headers=_auth(tokens["admin"]),
    )
    assert explicit_false.status_code == 201
    assert explicit_false.json()["can_edit"] is False


def test_folder_listing_and_retrieval_only_expose_owned_granted_or_public(
    governance_context,
) -> None:
    client = governance_context["client"]
    session_factory = governance_context["session_factory"]
    models_module = governance_context["models"]
    retrieval_module = governance_context["retrieval"]
    permission_service = governance_context["permission_service"]
    tokens = governance_context["tokens"]

    grant_response = client.post(
        "/admin/folder-permissions",
        json={"folder": "grant-folder", "grantee_user_id": 3},
        headers=_auth(tokens["admin"]),
    )
    assert grant_response.status_code == 201

    with session_factory() as session:
        for folder in [
            "owned-folder",
            "grant-folder",
            "public-folder",
            "hidden-folder",
        ]:
            permission_service.sync_folder_read_allow(session, folder)
        session.commit()

        granted_user = session.scalar(
            select(models_module.User).where(models_module.User.username == "granted")
        )
        assert granted_user is not None
        principals = permission_service.get_retrieval_principals(granted_user)

        result = retrieval_module.hybrid_rrf_search(
            session,
            query_text="alpha",
            query_vector=[0.1, 0.0],
            principals=principals,
            limit=10,
        )
        upload_ids = {item["upload_id"] for item in result}

        uploads = session.scalars(select(models_module.UploadRecord)).all()
        upload_by_name = {row.filename: row.id for row in uploads}

        assert upload_by_name["owned.txt"] not in upload_ids
        assert upload_by_name["granted.txt"] in upload_ids
        assert upload_by_name["public.txt"] in upload_ids
        assert upload_by_name["hidden.txt"] not in upload_ids

    listing = client.get("/permissions/files", headers=_auth(tokens["granted"]))
    assert listing.status_code == 200
    names = {row["filename"] for row in listing.json()}
    assert names == {"granted.txt", "public.txt"}


def test_permission_mutations_sync_chunks_and_create_audit_logs(
    governance_context,
) -> None:
    client = governance_context["client"]
    session_factory = governance_context["session_factory"]
    models_module = governance_context["models"]
    tokens = governance_context["tokens"]

    create_resp = client.post(
        "/admin/folder-permissions",
        json={"folder": "grant-folder", "grantee_user_id": 3},
        headers=_auth(tokens["admin"]),
    )
    assert create_resp.status_code == 201
    permission_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/admin/folder-permissions/{permission_id}",
        json={"can_edit": False},
        headers=_auth(tokens["admin"]),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["can_edit"] is False

    delete_resp = client.delete(
        f"/admin/folder-permissions/{permission_id}",
        headers=_auth(tokens["admin"]),
    )
    assert delete_resp.status_code == 200

    with session_factory() as session:
        grant_upload = session.scalar(
            select(models_module.UploadRecord).where(
                models_module.UploadRecord.filename == "granted.txt"
            )
        )
        assert grant_upload is not None
        chunk = session.scalar(
            select(models_module.DocChunk).where(
                models_module.DocChunk.upload_id == grant_upload.id,
                models_module.DocChunk.chunk_index == 0,
            )
        )
        assert chunk is not None
        assert "|owner:4|" in chunk.read_allow
        assert "|user:3|" not in chunk.read_allow

        audit_actions = session.scalars(
            select(models_module.AuditLog.action).order_by(
                models_module.AuditLog.id.asc()
            )
        ).all()
        assert "folder_permission_created" in audit_actions
        assert "folder_permission_updated" in audit_actions
        assert "folder_permission_deleted" in audit_actions
