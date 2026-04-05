from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List


class PhotoBase(BaseModel):
    description: Optional[str] = Field(None, max_length=500, description="Описание фотографии")


class PhotoCreate(PhotoBase):
    album_id: int = Field(..., description="ID альбома")


class PhotoUpdate(PhotoBase):
    pass


class PhotoResponse(PhotoBase):
    id: int
    album_id: int
    uploaded_by_user_id: int
    file_path: str
    original_filename: str
    file_size: int
    mime_type: str
    width: Optional[int]
    height: Optional[int]
    uploaded_at: datetime

    url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PhotoUploadResponse(BaseModel):
    success: bool
    photo: PhotoResponse
    message: str


class PhotoListResponse(BaseModel):
    photos: List[PhotoResponse]
    total: int
    album_id: int