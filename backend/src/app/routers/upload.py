from datetime import UTC, datetime
from hashlib import sha256

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db_session
from app.deps import get_current_user
from app.indexing.tasks import run_parse_pipeline
from app.models import FileRecord, FileVersion, UploadRecord, User
from app.permissions.service import can_user_view_upload
from app.schemas.upload import UploadSuccessResponse, UploadVersionResponse
from app.upload_validation import has_executable_signature, is_safe_filename


router = APIRouter(prefix="/uploads", tags=["uploads"])


def schedule_parse_task(upload_id: int, object_key: str) -> None:
    _ = object_key
    run_parse_pipeline(upload_id=upload_id)


def _build_object_key(
    folder: str, checksum_sha256: str, version: int, filename: str
) -> str:
    return f"{folder}/{checksum_sha256}/v{version}/{filename}"


@router.post(
    "", response_model=UploadSuccessResponse, status_code=status.HTTP_201_CREATED
)
async def create_upload(
    background_tasks: BackgroundTasks,
    folder: str = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> UploadSuccessResponse:
    settings = get_settings()
    content = await file.read()
    size_bytes = len(content)

    if size_bytes > settings.max_upload_size_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"code": "file_too_large", "detail": "File size exceeds 10MB"},
        )

    if not is_safe_filename(filename):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": "unsafe_filename",
                "detail": "Filename contains unsafe characters",
            },
        )

    if has_executable_signature(content):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": "executable_signature",
                "detail": "Executable files are not allowed",
            },
        )

    checksum_sha256 = sha256(content).hexdigest()

    duplicate = session.scalar(
        select(UploadRecord).where(
            UploadRecord.folder == folder,
            UploadRecord.checksum_sha256 == checksum_sha256,
        )
    )
    if duplicate is not None:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": "duplicate_checksum",
                "detail": "Identical file already exists in this folder",
            },
        )

    latest_version = session.scalar(
        select(func.max(UploadRecord.version)).where(
            UploadRecord.folder == folder,
            UploadRecord.filename == filename,
        )
    )
    version = 1 if latest_version is None else int(latest_version) + 1
    object_key = _build_object_key(folder, checksum_sha256, version, filename)

    record = UploadRecord(
        folder=folder,
        owner_id=user.id,
        filename=filename,
        version=version,
        checksum_sha256=checksum_sha256,
        object_key=object_key,
        size_bytes=size_bytes,
        parse_status="processing",
        source_text=content.decode("utf-8", errors="replace"),
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    # Keep editing flow compatible with file-manager IDs by creating a
    # corresponding file and initial version keyed by upload id.
    now = datetime.now(UTC)
    file_row = FileRecord(
        id=record.id,
        filename=record.filename,
        owner_id=user.id,
        department=user.department,
        current_version=1,
        parse_status="processing",
        created_at=now,
        updated_at=now,
    )
    session.add(file_row)
    session.flush()
    session.add(
        FileVersion(
            file_id=file_row.id,
            version_number=1,
            content=record.source_text,
            created_by=user.id,
        )
    )
    session.commit()

    background_tasks.add_task(schedule_parse_task, record.id, record.object_key)

    return UploadSuccessResponse(
        code="uploaded",
        upload_id=record.id,
        folder=record.folder,
        filename=record.filename,
        version=record.version,
        checksum_sha256=record.checksum_sha256,
        object_key=record.object_key,
        parse_status=record.parse_status,
    )


@router.get("/{upload_id}/versions", response_model=list[UploadVersionResponse])
def list_upload_versions(
    upload_id: int,
    session: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> list[UploadVersionResponse]:
    upload = session.scalar(select(UploadRecord).where(UploadRecord.id == upload_id))
    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if not can_user_view_upload(session, user, upload):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    rows = session.scalars(
        select(UploadRecord)
        .where(
            UploadRecord.folder == upload.folder,
            UploadRecord.filename == upload.filename,
        )
        .order_by(UploadRecord.version.desc())
    ).all()
    return [
        UploadVersionResponse(
            version_number=row.version,
            created_by=row.owner_id,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
