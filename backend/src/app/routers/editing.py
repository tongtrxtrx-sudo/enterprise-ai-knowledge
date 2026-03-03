from datetime import UTC, datetime
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.deps import get_current_user
from app.models import (
    DocEditSession,
    FileRecord,
    FileShare,
    FileVersion,
    ReindexJob,
    User,
)
from app.schemas.editing import EditCallbackRequest, EditStartResponse


router = APIRouter(prefix="/files", tags=["editing"])


def _has_edit_permission(session: Session, user: User, file_row: FileRecord) -> bool:
    if user.role == "admin":
        return True
    if file_row.owner_id == user.id:
        return True
    if user.role == "dept_manager" and user.department == file_row.department:
        return True

    shared = session.scalar(
        select(FileShare).where(
            FileShare.file_id == file_row.id,
            FileShare.grantee_user_id == user.id,
            FileShare.can_edit.is_(True),
        )
    )
    return shared is not None


def queue_reindex(file_id: int, version_id: int) -> ReindexJob:
    return ReindexJob(file_id=file_id, file_version_id=version_id, status="queued")


@router.post("/{file_id}/edit/start", response_model=EditStartResponse)
def start_edit_session(
    file_id: int,
    session: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> EditStartResponse:
    file_row = session.scalar(select(FileRecord).where(FileRecord.id == file_id))
    if file_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    if not _has_edit_permission(session, user, file_row):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    now = datetime.now(UTC)
    token = token_urlsafe(32)
    edit_session = DocEditSession(
        file_id=file_row.id,
        user_id=user.id,
        source_version=file_row.current_version,
        token=token,
        status="active",
        updated_at=now,
    )
    session.add(edit_session)
    session.commit()

    return EditStartResponse(
        file_id=file_row.id,
        source_version=file_row.current_version,
        session_token=token,
        editor_config={
            "document": {
                "fileType": file_row.filename.split(".")[-1].lower()
                if "." in file_row.filename
                else "txt",
                "title": file_row.filename,
            },
            "permissions": {"edit": True},
            "callbackUrl": f"/files/{file_row.id}/edit/callback",
        },
    )


@router.post("/{file_id}/edit/callback")
def handle_edit_callback(
    file_id: int,
    payload: EditCallbackRequest,
    session: Session = Depends(get_db_session),
) -> dict[str, int]:
    edit_session = session.scalar(
        select(DocEditSession).where(
            DocEditSession.file_id == file_id,
            DocEditSession.token == payload.token,
        )
    )
    if edit_session is None:
        return {"error": 1}

    if payload.status not in (2, 6):
        return {"error": 0}

    file_row = session.scalar(select(FileRecord).where(FileRecord.id == file_id))
    if file_row is None:
        return {"error": 1}

    if edit_session.status != "active":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": 1, "code": "duplicate_callback"},
        )

    if edit_session.source_version != file_row.current_version:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": 1, "code": "stale_edit_session_version"},
        )

    next_version = file_row.current_version + 1
    version = FileVersion(
        file_id=file_id,
        version_number=next_version,
        content=payload.content,
        created_by=edit_session.user_id,
    )
    session.add(version)
    session.flush()

    file_row.current_version = next_version
    file_row.parse_status = "processing"
    file_row.updated_at = datetime.now(UTC)
    session.add(file_row)

    edit_session.status = "saved"
    edit_session.save_version_id = version.id
    edit_session.updated_at = datetime.now(UTC)
    session.add(edit_session)

    reindex_job = queue_reindex(file_id, version.id)
    if reindex_job is not None:
        session.add(reindex_job)
    session.commit()
    return {"error": 0}
