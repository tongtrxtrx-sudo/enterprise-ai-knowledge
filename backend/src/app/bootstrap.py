from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.security import hash_password


@dataclass
class BootstrapResult:
    admin_user_id: int
    admin_created: bool
    password_updated: bool
    seed_audit_created: bool


def validate_admin_password(password: str) -> None:
    if len(password) < 14:
        raise ValueError("Admin password must be at least 14 characters long")

    has_upper = any(char.isupper() for char in password)
    has_lower = any(char.islower() for char in password)
    has_digit = any(char.isdigit() for char in password)
    has_symbol = any(not char.isalnum() for char in password)
    if not (has_upper and has_lower and has_digit and has_symbol):
        raise ValueError(
            "Admin password must include uppercase, lowercase, digit, and symbol"
        )


def bootstrap_admin(
    session: Session,
    *,
    username: str,
    password: str,
    department: str,
    rotate_password: bool,
) -> BootstrapResult:
    normalized_username = username.strip()
    normalized_department = department.strip() or "platform"
    if not normalized_username:
        raise ValueError("Admin username must not be empty")
    validate_admin_password(password)

    existing_user = session.scalar(
        select(User).where(User.username == normalized_username)
    )

    admin_created = False
    password_updated = False
    if existing_user is None:
        user = User(
            username=normalized_username,
            password_hash=hash_password(password),
            role="admin",
            department=normalized_department,
        )
        session.add(user)
        session.flush()
        admin_user = user
        admin_created = True
        password_updated = True
    else:
        admin_user = existing_user
        if admin_user.role != "admin":
            admin_user.role = "admin"
        if admin_user.department != normalized_department:
            admin_user.department = normalized_department
        if rotate_password:
            admin_user.password_hash = hash_password(password)
            admin_user.token_version = admin_user.token_version + 1
            password_updated = True

    existing_seed = session.scalar(
        select(AuditLog).where(
            AuditLog.action == "bootstrap_admin_initialized",
            AuditLog.actor_user_id == admin_user.id,
        )
    )
    seed_audit_created = False
    if existing_seed is None:
        session.add(
            AuditLog(
                actor_user_id=admin_user.id,
                action="bootstrap_admin_initialized",
                target_type="user",
                target_id=admin_user.id,
                detail={
                    "username": admin_user.username,
                    "department": admin_user.department,
                },
            )
        )
        seed_audit_created = True

    session.commit()
    return BootstrapResult(
        admin_user_id=admin_user.id,
        admin_created=admin_created,
        password_updated=password_updated,
        seed_audit_created=seed_audit_created,
    )
