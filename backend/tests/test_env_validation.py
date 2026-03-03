from pathlib import Path


def test_backend_start_command_includes_env_validation() -> None:
    compose_path = Path(__file__).resolve().parents[2] / "infra" / "docker-compose.yml"
    content = compose_path.read_text(encoding="utf-8")

    assert "backend:" in content
    assert "python /app/scripts/validate_env.py backend" in content


def test_frontend_start_command_includes_env_validation() -> None:
    compose_path = Path(__file__).resolve().parents[2] / "infra" / "docker-compose.yml"
    content = compose_path.read_text(encoding="utf-8")

    assert "frontend:" in content
    assert "python /app/scripts/validate_env.py frontend" in content


def test_env_schema_defines_required_frontend_backend_keys() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "infra" / "env.schema.json"
    assert schema_path.exists(), "env schema file must exist"

    content = schema_path.read_text(encoding="utf-8")
    assert "BACKEND_SERVICE_NAME" in content
    assert "BACKEND_VERSION" in content
    assert "FRONTEND_PUBLIC_APP_NAME" in content
    assert "FRONTEND_PORT" in content
