from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.deps import require_roles
from app.models import AuditLog, FolderPermission, UploadRecord, User
from app.permissions.service import (
    sync_folder_read_allow,
    sync_upload_read_allow,
    write_audit_log,
)
from app.schemas.admin import (
    AdminUserResponse,
    AuditStateResponse,
    DepartmentStateResponse,
)
from app.schemas.permissions import (
    FolderPermissionCreateRequest,
    FolderPermissionResponse,
    FolderPermissionUpdateRequest,
    VisibilityUpdateRequest,
)


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserResponse])
def list_admin_users(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_roles("admin")),
) -> list[AdminUserResponse]:
    rows = session.scalars(select(User).order_by(User.id.asc())).all()
    return [
        AdminUserResponse(
            id=row.id,
            username=row.username,
            role=row.role,
            department=row.department,
            status="active",
        )
        for row in rows
    ]


@router.get("/departments", response_model=list[DepartmentStateResponse])
def list_departments(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_roles("admin")),
) -> list[DepartmentStateResponse]:
    department_counts = session.execute(
        select(User.department, func.count(User.id)).group_by(User.department)
    ).all()

    manager_by_department = {
        row.department: row.id
        for row in session.scalars(
            select(User)
            .where(User.role == "dept_manager")
            .order_by(User.department.asc(), User.id.asc())
        )
    }

    return [
        DepartmentStateResponse(
            name=str(department),
            manager_user_id=manager_by_department.get(str(department), 0),
            member_count=int(member_count),
        )
        for department, member_count in sorted(
            department_counts, key=lambda item: item[0]
        )
    ]


@router.get("/audit-states", response_model=list[AuditStateResponse])
def list_audit_states(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_roles("admin")),
) -> list[AuditStateResponse]:
    rows = session.scalars(select(AuditLog).order_by(AuditLog.id.desc())).all()
    return [
        AuditStateResponse(
            id=row.id,
            actor_user_id=row.actor_user_id,
            action=row.action,
            target_type=row.target_type,
            target_id=row.target_id,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@router.post(
    "/folder-permissions",
    response_model=FolderPermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_folder_permission(
    payload: FolderPermissionCreateRequest,
    session: Session = Depends(get_db_session),
    admin: User = Depends(require_roles("admin")),
) -> FolderPermissionResponse:
    now = datetime.now(UTC)
    permission = session.scalar(
        select(FolderPermission).where(
            FolderPermission.folder == payload.folder,
            FolderPermission.grantee_user_id == payload.grantee_user_id,
        )
    )

    if permission is None:
        permission = FolderPermission(
            folder=payload.folder,
            grantee_user_id=payload.grantee_user_id,
            can_edit=payload.can_edit,
            created_at=now,
            updated_at=now,
        )
        session.add(permission)
        action = "folder_permission_created"
    else:
        permission.can_edit = payload.can_edit
        permission.updated_at = now
        action = "folder_permission_updated"

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder permission payload",
        ) from exc

    sync_folder_read_allow(session, payload.folder)
    write_audit_log(
        session,
        actor_user_id=admin.id,
        action=action,
        target_type="folder_permission",
        target_id=permission.id,
        detail={
            "folder": payload.folder,
            "grantee_user_id": payload.grantee_user_id,
            "can_edit": payload.can_edit,
        },
    )
    session.commit()
    session.refresh(permission)

    return FolderPermissionResponse(
        id=permission.id,
        folder=permission.folder,
        grantee_user_id=permission.grantee_user_id,
        can_edit=permission.can_edit,
    )


@router.get("/folder-permissions", response_model=list[FolderPermissionResponse])
def list_folder_permissions(
    folder: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    _: User = Depends(require_roles("admin")),
) -> list[FolderPermissionResponse]:
    stmt = select(FolderPermission).order_by(FolderPermission.id.asc())
    if folder:
        stmt = stmt.where(FolderPermission.folder == folder)

    rows = session.scalars(stmt).all()
    return [
        FolderPermissionResponse(
            id=row.id,
            folder=row.folder,
            grantee_user_id=row.grantee_user_id,
            can_edit=row.can_edit,
        )
        for row in rows
    ]


@router.patch(
    "/folder-permissions/{permission_id}", response_model=FolderPermissionResponse
)
def update_folder_permission(
    permission_id: int,
    payload: FolderPermissionUpdateRequest,
    session: Session = Depends(get_db_session),
    admin: User = Depends(require_roles("admin")),
) -> FolderPermissionResponse:
    permission = session.scalar(
        select(FolderPermission).where(FolderPermission.id == permission_id)
    )
    if permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    permission.can_edit = payload.can_edit
    permission.updated_at = datetime.now(UTC)
    sync_folder_read_allow(session, permission.folder)
    write_audit_log(
        session,
        actor_user_id=admin.id,
        action="folder_permission_updated",
        target_type="folder_permission",
        target_id=permission.id,
        detail={
            "folder": permission.folder,
            "grantee_user_id": permission.grantee_user_id,
            "can_edit": permission.can_edit,
        },
    )
    session.commit()
    session.refresh(permission)

    return FolderPermissionResponse(
        id=permission.id,
        folder=permission.folder,
        grantee_user_id=permission.grantee_user_id,
        can_edit=permission.can_edit,
    )


@router.delete("/folder-permissions/{permission_id}")
def delete_folder_permission(
    permission_id: int,
    session: Session = Depends(get_db_session),
    admin: User = Depends(require_roles("admin")),
) -> dict[str, str]:
    permission = session.scalar(
        select(FolderPermission).where(FolderPermission.id == permission_id)
    )
    if permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    folder = permission.folder
    grantee_user_id = permission.grantee_user_id
    session.delete(permission)
    session.flush()
    sync_folder_read_allow(session, folder)
    write_audit_log(
        session,
        actor_user_id=admin.id,
        action="folder_permission_deleted",
        target_type="folder_permission",
        target_id=permission_id,
        detail={"folder": folder, "grantee_user_id": grantee_user_id},
    )
    session.commit()
    return {"status": "deleted"}


@router.patch("/uploads/{upload_id}/visibility")
def update_upload_visibility(
    upload_id: int,
    payload: VisibilityUpdateRequest,
    session: Session = Depends(get_db_session),
    admin: User = Depends(require_roles("admin")),
) -> dict[str, object]:
    upload = session.scalar(select(UploadRecord).where(UploadRecord.id == upload_id))
    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    upload.is_public = payload.is_public
    sync_upload_read_allow(session, upload)
    write_audit_log(
        session,
        actor_user_id=admin.id,
        action="upload_visibility_updated",
        target_type="upload",
        target_id=upload.id,
        detail={"is_public": upload.is_public, "folder": upload.folder},
    )
    session.commit()
    return {"id": upload.id, "is_public": upload.is_public}
