from pydantic import BaseModel, Field


class FolderPermissionCreateRequest(BaseModel):
    folder: str
    grantee_user_id: int
    can_edit: bool = True


class FolderPermissionUpdateRequest(BaseModel):
    can_edit: bool


class FolderPermissionResponse(BaseModel):
    id: int
    folder: str
    grantee_user_id: int
    can_edit: bool


class VisibleUploadResponse(BaseModel):
    id: int
    folder: str
    filename: str
    owner_id: int
    is_public: bool
    parse_status: str


class VisibilityUpdateRequest(BaseModel):
    is_public: bool = Field(default=False)
