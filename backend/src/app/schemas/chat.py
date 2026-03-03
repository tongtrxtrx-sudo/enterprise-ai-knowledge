from pydantic import BaseModel, Field


class ChatStreamRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    folder: str | None = None
    public_query: bool = False
