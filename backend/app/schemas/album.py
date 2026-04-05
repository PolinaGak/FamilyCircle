from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from .photo import PhotoResponse


class AlbumBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200, description="Название альбома")
    description: Optional[str] = Field(None, max_length=1000, description="Описание альбома")


class AlbumCreate(AlbumBase):
    family_id: int = Field(..., description="ID семьи")
    event_id: Optional[int] = Field(None, description="ID события (опционально)")


class AlbumUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class AlbumMemberInfo(BaseModel):
    user_id: int
    can_edit: bool
    can_delete: bool
    status: str
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlbumResponse(AlbumBase):
    id: int
    family_id: int
    created_by_user_id: int
    event_id: Optional[int]
    created_at: datetime
    expires_at: datetime
    is_deleted: bool
    hours_until_deletion: float
    photos_count: int = 0
    members_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AlbumDetailResponse(AlbumResponse):
    members: List[AlbumMemberInfo] = []
    photos: List[PhotoResponse] = []
    is_admin: bool = False


class AlbumListResponse(BaseModel):
    albums: List[AlbumResponse]
    total: int