import os
import sys


REQUIRED_VARS = {
    "frontend": ["FRONTEND_PUBLIC_APP_NAME", "FRONTEND_PORT"],
}


def validate_environment(target: str) -> list[str]:
    required = REQUIRED_VARS.get(target)
    if required is None:
        return [f"Unknown target: {target}"]

    missing = [key for key in required if not os.getenv(key)]
    if missing:
        return [
            f"Missing required environment variables for {target}: {', '.join(missing)}"
        ]

    if os.getenv("APP_ENV", "development").strip().lower() == "production":
        app_name = os.getenv("FRONTEND_PUBLIC_APP_NAME", "").strip().lower()
        if app_name in {"kb-frontend", "demo-app", "change-me"}:
            return [
                "Unsafe frontend app name detected in production. "
                "Set FRONTEND_PUBLIC_APP_NAME to your deployment-specific value."
            ]

    return []


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_env.py <backend|frontend>")
        return 2

    target = sys.argv[1]
    errors = validate_environment(target)
    if errors and errors[0].startswith("Unknown target:"):
        print(errors[0])
        return 2

    if errors:
        for error in errors:
            print(error)
        return 1

    print(f"Environment validated for {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
