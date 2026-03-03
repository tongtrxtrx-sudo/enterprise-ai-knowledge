from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, DocChunk, FolderPermission, UploadRecord, User


def _encode_allow(tokens: list[str]) -> str:
    unique = sorted(set(tokens))
    return "".join(f"|{token}|" for token in unique)


def build_upload_read_allow(session: Session, upload: UploadRecord) -> str:
    tokens: list[str] = []

    if upload.owner_id > 0:
        tokens.append(f"owner:{upload.owner_id}")
    if upload.is_public:
        tokens.append("public")

    grantee_ids = session.scalars(
        select(FolderPermission.grantee_user_id).where(
            FolderPermission.folder == upload.folder
        )
    ).all()
    for grantee_id in grantee_ids:
        tokens.append(f"user:{int(grantee_id)}")

    return _encode_allow(tokens)


def sync_upload_read_allow(session: Session, upload: UploadRecord) -> None:
    allow = build_upload_read_allow(session, upload)
    chunk_rows = session.scalars(
        select(DocChunk).where(DocChunk.upload_id == upload.id)
    ).all()
    now = datetime.now(UTC)
    for chunk in chunk_rows:
        chunk.read_allow = allow
        chunk.updated_at = now


def sync_folder_read_allow(session: Session, folder: str) -> None:
    uploads = session.scalars(
        select(UploadRecord).where(UploadRecord.folder == folder)
    ).all()
    for upload in uploads:
        sync_upload_read_allow(session, upload)


def get_retrieval_principals(user: User) -> list[str]:
    return [f"owner:{user.id}", f"user:{user.id}", "public"]


def can_user_view_upload(session: Session, user: User, upload: UploadRecord) -> bool:
    if upload.owner_id == user.id:
        return True
    if upload.is_public:
        return True

    grant = session.scalar(
        select(FolderPermission).where(
            FolderPermission.folder == upload.folder,
            FolderPermission.grantee_user_id == user.id,
        )
    )
    return grant is not None


def list_visible_uploads(
    session: Session, *, user: User, folder: str | None = None
) -> list[UploadRecord]:
    stmt = select(UploadRecord)
    if folder:
        stmt = stmt.where(UploadRecord.folder == folder)

    candidates = session.scalars(stmt.order_by(UploadRecord.id.asc())).all()
    return [row for row in candidates if can_user_view_upload(session, user, row)]


def write_audit_log(
    session: Session,
    *,
    actor_user_id: int | None,
    action: str,
    target_type: str,
    target_id: int | None,
    detail: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )
