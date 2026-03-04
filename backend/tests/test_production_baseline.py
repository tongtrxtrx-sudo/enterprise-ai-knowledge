from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.bootstrap import bootstrap_admin
from app.db import Base
from app.env_validation import validate_environment
from app.models import AuditLog, User
from app.security import hash_password, verify_password


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    return local_session()


def test_production_template_and_runbook_exist_with_secure_guidance() -> None:
    project_root = Path(__file__).resolve().parents[2]
    env_template = (project_root / ".env.production.example").read_text(
        encoding="utf-8"
    )
    runbook = (
        project_root / "docs" / "runbooks" / "pre-launch-checklist.md"
    ).read_text(encoding="utf-8")

    assert "APP_ENV=production" in env_template
    assert "JWT_SECRET=<" in env_template
    assert "POSTGRES_PASSWORD=<" in env_template
    assert "MINIO_ROOT_PASSWORD=<" in env_template
    assert "ONLYOFFICE_JWT_ENABLED=true" in env_template
    assert "kb_dev_password" not in env_template
    assert "minioadmin" not in env_template
    assert "dev-secret-change-me" not in env_template

    assert "bootstrap_admin.py" in runbook
    assert "Rollback Basics" in runbook


def test_validate_environment_rejects_unsafe_production_defaults() -> None:
    env = {
        "APP_ENV": "production",
        "BACKEND_SERVICE_NAME": "kb-backend",
        "BACKEND_VERSION": "2.1.0",
        "DATABASE_URL": "postgresql+psycopg://kb_app:pw@postgres:5432/kb",
        "JWT_SECRET": "dev-secret-change-me",
        "POSTGRES_PASSWORD": "kb_dev_password",
        "MINIO_ROOT_PASSWORD": "minioadmin",
        "MINIO_ROOT_USER": "minioadmin",
        "ONLYOFFICE_JWT_ENABLED": "false",
        "ONLYOFFICE_JWT_SECRET": "onlyoffice-dev-secret",
    }

    errors = validate_environment("backend", env)

    assert any("Unsafe default detected" in error for error in errors)
    assert any("JWT_SECRET" in error for error in errors)
    assert any("POSTGRES_PASSWORD" in error for error in errors)


def test_validate_environment_allows_non_production_defaults() -> None:
    env = {
        "APP_ENV": "development",
        "BACKEND_SERVICE_NAME": "kb-backend",
        "BACKEND_VERSION": "2.1.0",
        "DATABASE_URL": "sqlite:///./auth.db",
        "JWT_SECRET": "dev-secret-change-me",
    }

    errors = validate_environment("backend", env)

    assert errors == []


def test_bootstrap_admin_creates_admin_and_seed_audit() -> None:
    session = _build_session()
    try:
        result = bootstrap_admin(
            session,
            username="admin",
            password="StrongBootstrap#123",
            department="platform",
            rotate_password=False,
        )

        created_user = session.scalar(
            select(User).where(User.id == result.admin_user_id)
        )
        bootstrap_audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "bootstrap_admin_initialized")
        )

        assert result.admin_created is True
        assert result.password_updated is True
        assert result.seed_audit_created is True
        assert created_user is not None
        assert created_user.role == "admin"
        assert bootstrap_audit is not None
    finally:
        session.close()


def test_bootstrap_admin_promotes_existing_user_and_rotates_password() -> None:
    session = _build_session()
    try:
        existing = User(
            username="admin",
            password_hash=hash_password("ExistingPassword#123"),
            role="user",
            department="ops",
            token_version=4,
        )
        session.add(existing)
        session.commit()

        promoted = bootstrap_admin(
            session,
            username="admin",
            password="StrongBootstrap#123",
            department="platform",
            rotate_password=False,
        )
        session.refresh(existing)

        assert promoted.admin_created is False
        assert promoted.password_updated is False
        assert existing.role == "admin"
        assert existing.token_version == 4

        rotated = bootstrap_admin(
            session,
            username="admin",
            password="RotatedPassword#456",
            department="platform",
            rotate_password=True,
        )
        session.refresh(existing)

        assert rotated.password_updated is True
        assert existing.token_version == 5
        assert verify_password("RotatedPassword#456", existing.password_hash)
    finally:
        session.close()
