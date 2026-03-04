from pydantic import BaseModel


class AdminUserResponse(BaseModel):
    id: int
    username: str
    role: str
    department: str
    status: str


class DepartmentStateResponse(BaseModel):
    name: str
    manager_user_id: int
    member_count: int


class AuditStateResponse(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    target_type: str
    target_id: int | None
    created_at: str
