from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID

class UploadBase(BaseModel):
    filename: str
    file_size_bytes: int
    mime_type: str
    status: str

class UploadResponse(UploadBase):
    id: UUID
    user_id: UUID
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
