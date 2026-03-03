from pydantic import BaseModel


class EditStartResponse(BaseModel):
    file_id: int
    source_version: int
    session_token: str
    editor_config: dict[str, object]


class EditCallbackRequest(BaseModel):
    token: str
    status: int
    content: str
