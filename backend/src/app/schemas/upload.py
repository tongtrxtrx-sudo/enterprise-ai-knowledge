from pydantic import BaseModel


class UploadSuccessResponse(BaseModel):
    code: str
    upload_id: int
    folder: str
    filename: str
    version: int
    checksum_sha256: str
    object_key: str
    parse_status: str
