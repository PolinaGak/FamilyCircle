from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class AlbumMemberAdd(BaseModel):
    """Добавление обычного участника (только члены семьи)"""
    user_id: int = Field(..., description="ID пользователя для добавления")


class AlbumAdminAdd(BaseModel):
    """Добавление администратора (только члены семьи)"""
    user_id: int = Field(..., description="ID пользователя для назначения администратором")


class AlbumAdminRemove(BaseModel):
    """Снятие прав администратора"""
    user_id: int = Field(..., description="ID пользователя для снятия прав")


class AlbumMemberResponse(BaseModel):
    album_id: int
    user_id: int
    can_edit: bool
    can_delete: bool
    status: str
    added_by_user_id: int
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlbumAdminResponse(AlbumMemberResponse):
    """Ответ при работе с администраторами"""
    pass