from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from app.models.enums import InvitationStatus


class ChatMemberBase(BaseModel):
    user_id: int
    is_admin: bool = False


class ChatMemberAdd(BaseModel):
    user_id: int = Field(..., description="ID пользователя для добавления")


class ChatMemberResponse(BaseModel):
    chat_id: int
    user_id: int
    user_name: Optional[str] = None
    is_admin: bool
    status: InvitationStatus
    joined_at: datetime
    added_by_user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ChatBase(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="Название чата")


class ChatCreate(ChatBase):
    family_id: int = Field(..., description="ID семьи")
    is_event: bool = Field(False, description="Является ли чатом события")
    event_id: Optional[int] = Field(None, description="ID события (если чат события)")


class ChatUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)


class ChatResponse(ChatBase):
    id: int
    family_id: int
    is_event: bool
    event_id: Optional[int]
    created_by_user_id: int
    created_at: datetime
    members_count: int = 0
    is_admin: bool = False

    model_config = ConfigDict(from_attributes=True)


class ChatDetailResponse(ChatResponse):
    members: List[ChatMemberResponse] = []


class ChatListResponse(BaseModel):
    chats: List[ChatResponse]
    total: int


class TransferAdminRequest(BaseModel):
    new_admin_user_id: int = Field(..., description="ID нового администратора")