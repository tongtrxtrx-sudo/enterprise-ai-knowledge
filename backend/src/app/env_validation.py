import os
from collections.abc import Mapping


REQUIRED_VARS = {
    "backend": [
        "BACKEND_SERVICE_NAME",
        "BACKEND_VERSION",
        "DATABASE_URL",
        "JWT_SECRET",
    ],
    "frontend": ["FRONTEND_PUBLIC_APP_NAME", "FRONTEND_PORT"],
}


PRODUCTION_REQUIRED_VARS = {
    "backend": [
        "POSTGRES_PASSWORD",
        "MINIO_ROOT_PASSWORD",
        "ONLYOFFICE_JWT_ENABLED",
        "ONLYOFFICE_JWT_SECRET",
    ],
    "frontend": [],
}


PRODUCTION_BLOCKED_DEFAULTS = {
    "JWT_SECRET": {"dev-secret-change-me", "onlyoffice-dev-secret"},
    "POSTGRES_PASSWORD": {"kb_dev_password"},
    "MINIO_ROOT_PASSWORD": {"minioadmin"},
    "MINIO_ROOT_USER": {"minioadmin"},
    "ONLYOFFICE_JWT_SECRET": {"onlyoffice-dev-secret", "change-me"},
    "ONLYOFFICE_JWT_ENABLED": {"false"},
}


def is_production_env(environ: Mapping[str, str]) -> bool:
    return environ.get("APP_ENV", "development").strip().lower() == "production"


def validate_environment(
    target: str, environ: Mapping[str, str] | None = None
) -> list[str]:
    effective_env = environ or os.environ
    required = REQUIRED_VARS.get(target)
    if required is None:
        return [f"Unknown target: {target}"]

    errors: list[str] = []
    missing = [key for key in required if not effective_env.get(key)]
    if missing:
        errors.append(
            f"Missing required environment variables for {target}: {', '.join(missing)}"
        )

    if not is_production_env(effective_env):
        return errors

    production_required = PRODUCTION_REQUIRED_VARS.get(target, [])
    production_missing = [
        key for key in production_required if not effective_env.get(key)
    ]
    if production_missing:
        errors.append(
            "Missing production-only environment variables "
            f"for {target}: {', '.join(production_missing)}"
        )

    for key, blocked_values in PRODUCTION_BLOCKED_DEFAULTS.items():
        value = effective_env.get(key)
        if value is None:
            continue
        normalized_value = value.strip().lower()
        normalized_blocked = {blocked.lower() for blocked in blocked_values}
        if normalized_value in normalized_blocked:
            errors.append(
                f"Unsafe default detected in production: {key}={value}. "
                "Set a secure deployment-specific value."
            )

    return errors
