from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.env_validation import validate_environment


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
