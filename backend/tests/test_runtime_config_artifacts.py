from pathlib import Path


def test_nginx_config_exists_with_proxy_contract() -> None:
    nginx_conf = Path(__file__).resolve().parents[2] / "infra" / "nginx" / "nginx.conf"
    assert nginx_conf.exists(), "nginx config must exist"

    content = nginx_conf.read_text(encoding="utf-8")
    assert "upstream backend" in content
    assert "upstream frontend" in content
    assert "location /health" in content


def test_env_example_exists_for_runtime_scaffold() -> None:
    env_example = Path(__file__).resolve().parents[2] / ".env.example"
    assert env_example.exists(), ".env.example must exist"

    content = env_example.read_text(encoding="utf-8")
    assert "BACKEND_SERVICE_NAME=" in content
    assert "BACKEND_VERSION=" in content
    assert "FRONTEND_PUBLIC_APP_NAME=" in content
