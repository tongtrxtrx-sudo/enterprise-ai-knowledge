from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.deps import get_current_user
from app.permissions.service import list_visible_uploads
from app.schemas.permissions import VisibleUploadResponse


router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/files", response_model=list[VisibleUploadResponse])
def list_visible_files(
    folder: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    user=Depends(get_current_user),
) -> list[VisibleUploadResponse]:
    rows = list_visible_uploads(session, user=user, folder=folder)
    return [
        VisibleUploadResponse(
            id=row.id,
            folder=row.folder,
            filename=row.filename,
            owner_id=row.owner_id,
            is_public=row.is_public,
            parse_status=row.parse_status,
        )
        for row in rows
    ]
