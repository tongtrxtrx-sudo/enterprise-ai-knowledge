import os
import sys


REQUIRED_VARS = {
    "backend": ["BACKEND_SERVICE_NAME", "BACKEND_VERSION"],
    "frontend": ["FRONTEND_PUBLIC_APP_NAME", "FRONTEND_PORT"],
}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_env.py <backend|frontend>")
        return 2

    target = sys.argv[1]
    required = REQUIRED_VARS.get(target)
    if required is None:
        print(f"Unknown target: {target}")
        return 2

    missing = [key for key in required if not os.getenv(key)]
    if missing:
        print(
            f"Missing required environment variables for {target}: {', '.join(missing)}"
        )
        return 1

    print(f"Environment validated for {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
