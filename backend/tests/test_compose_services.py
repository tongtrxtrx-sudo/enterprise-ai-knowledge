from pathlib import Path


def test_compose_contains_all_v21_services() -> None:
    compose_path = Path(__file__).resolve().parents[2] / "infra" / "docker-compose.yml"
    assert compose_path.exists(), "compose file must exist"

    content = compose_path.read_text(encoding="utf-8")
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
        assert f"  {service}:" in content, f"missing service: {service}"


def test_compose_declares_services_section() -> None:
    compose_path = Path(__file__).resolve().parents[2] / "infra" / "docker-compose.yml"
    content = compose_path.read_text(encoding="utf-8")
    assert "services:" in content
