from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from backend.app.models.enums import InvitationStatus


class EventBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_datetime: datetime
    end_datetime: datetime


class EventCreate(EventBase):
    family_id: int
    create_chat: bool = Field(True, description="Автоматически создать чат для события")
    invite_members: Optional[List[int]] = Field(None, description="ID членов семьи для приглашения")


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    is_active: Optional[bool] = None


class EventParticipantResponse(BaseModel):
    event_id: int
    user_id: int
    status: InvitationStatus
    invited_at: datetime
    responded_at: Optional[datetime] = None
    user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EventResponse(EventBase):
    id: int
    family_id: int
    created_by_user_id: int
    is_active: bool
    created_at: Optional[datetime] = None
    chat_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class EventDetailResponse(EventResponse):
    participants: List[EventParticipantResponse] = []
    is_admin: bool = False
    chat_exists: bool = False


class EventListResponse(BaseModel):
    events: List[EventResponse]
    total: int


class InviteParticipantRequest(BaseModel):
    user_id: int


class RespondToInvitationRequest(BaseModel):
    accept: bool


class CalendarEventResponse(BaseModel):
    """Событие для календаря (только подтвержденные)"""
    id: int
    title: str
    start_datetime: datetime
    end_datetime: datetime
    description: Optional[str] = None
    chat_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)