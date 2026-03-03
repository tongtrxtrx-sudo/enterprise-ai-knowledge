from pathlib import Path


def _extract_service_block(compose_content: str, service_name: str) -> str:
    lines = compose_content.splitlines()
    start_token = f"  {service_name}:"
    start_index = -1

    for index, line in enumerate(lines):
        if line == start_token:
            start_index = index
            break

    assert start_index >= 0, f"service block not found: {service_name}"

    block_lines: list[str] = []
    for line in lines[start_index + 1 :]:
        if line.startswith("  ") and not line.startswith("    "):
            break
        block_lines.append(line)

    return "\n".join(block_lines)


def test_compose_has_healthchecks_for_all_seven_services() -> None:
    compose_path = Path(__file__).resolve().parents[2] / "infra" / "docker-compose.yml"
    compose_content = compose_path.read_text(encoding="utf-8")

    required_services = [
        "nginx",
        "frontend",
        "backend",
        "postgres",
        "redis",
        "minio",
        "onlyoffice",
    ]

    for service in required_services:
        service_block = _extract_service_block(compose_content, service)
        assert "healthcheck:" in service_block, f"healthcheck missing for {service}"


def test_compose_uses_health_gated_startup_dependencies() -> None:
    compose_path = Path(__file__).resolve().parents[2] / "infra" / "docker-compose.yml"
    compose_content = compose_path.read_text(encoding="utf-8")

    nginx_block = _extract_service_block(compose_content, "nginx")
    backend_block = _extract_service_block(compose_content, "backend")
    frontend_block = _extract_service_block(compose_content, "frontend")
    onlyoffice_block = _extract_service_block(compose_content, "onlyoffice")

    assert "condition: service_healthy" in nginx_block
    assert "condition: service_healthy" in backend_block
    assert "condition: service_healthy" in frontend_block
    assert "condition: service_healthy" in onlyoffice_block


def test_backup_restore_scripts_cover_postgres_redis_and_minio() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    backup_script = (root_dir / "infra" / "scripts" / "backup_stack.sh").read_text(
        encoding="utf-8"
    )
    restore_script = (root_dir / "infra" / "scripts" / "restore_stack.sh").read_text(
        encoding="utf-8"
    )

    assert "pg_dump" in backup_script
    assert "redis-cli --rdb" in backup_script
    assert "minio:/data/." in backup_script

    assert "pg_restore" in restore_script
    assert "redis-cli FLUSHALL" in restore_script
    assert "minio-data/." in restore_script


def test_runbooks_include_rollbacks_for_indexing_and_editor_callback() -> None:
    root_dir = Path(__file__).resolve().parents[2]
    deployment_runbook = (
        root_dir / "docs" / "runbooks" / "deployment-v2.1.md"
    ).read_text(encoding="utf-8")
    incident_runbook = (
        root_dir / "docs" / "runbooks" / "incident-response.md"
    ).read_text(encoding="utf-8")

    assert "## Rollback" in deployment_runbook
    assert "Failed Indexing" in incident_runbook
    assert "Editor Callback" in incident_runbook
    assert "Rollback for Failed Indexing" in incident_runbook
    assert "Rollback for Editor Callback Incident" in incident_runbook
