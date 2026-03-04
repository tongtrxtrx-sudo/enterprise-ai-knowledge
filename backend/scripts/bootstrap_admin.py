import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.bootstrap import bootstrap_admin
from app.db import Base, get_engine, get_session_factory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or update the first admin account for production bootstrap"
    )
    parser.add_argument(
        "--username",
        default=os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin"),
        help="Admin username, defaults to BOOTSTRAP_ADMIN_USERNAME or 'admin'",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("BOOTSTRAP_ADMIN_PASSWORD"),
        help="Admin password, defaults to BOOTSTRAP_ADMIN_PASSWORD",
    )
    parser.add_argument(
        "--department",
        default=os.getenv("BOOTSTRAP_ADMIN_DEPARTMENT", "platform"),
        help="Admin department, defaults to BOOTSTRAP_ADMIN_DEPARTMENT or 'platform'",
    )
    parser.add_argument(
        "--rotate-password",
        action="store_true",
        help="Rotate password for existing user and revoke old tokens",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.password:
        print("Missing admin password. Provide --password or BOOTSTRAP_ADMIN_PASSWORD.")
        return 2

    Base.metadata.create_all(bind=get_engine())
    session = get_session_factory()()
    try:
        result = bootstrap_admin(
            session,
            username=args.username,
            password=args.password,
            department=args.department,
            rotate_password=args.rotate_password,
        )
    except ValueError as exc:
        session.rollback()
        print(f"Bootstrap failed: {exc}")
        return 1
    finally:
        session.close()

    print("Bootstrap admin completed")
    print(f"admin_user_id={result.admin_user_id}")
    print(f"admin_created={str(result.admin_created).lower()}")
    print(f"password_updated={str(result.password_updated).lower()}")
    print(f"seed_audit_created={str(result.seed_audit_created).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
