from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SessionPermissionsResponse(BaseModel):
    can_upload: bool
    can_view_versions: bool
    can_edit_file: bool
    can_access_admin: bool


class SessionUserResponse(BaseModel):
    id: int
    username: str
    role: str
    department: str


class SessionStateResponse(BaseModel):
    user: SessionUserResponse
    permissions: SessionPermissionsResponse
