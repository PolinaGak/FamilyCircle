from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime, timedelta
from typing import Optional
from app.core.config import settings


class InvitationBase(BaseModel):
    """Базовые поля приглашения"""
    family_id: int
    expires_in_days: int = Field(7, ge=1, le=30, description="Срок действия в днях")


class InvitationCreateNewMember(InvitationBase):
    """Приглашение для создания нового члена семьи"""
    invitation_type: str = "new_member"


class InvitationCreateClaimMember(InvitationBase):
    """Приглашение для привязки существующей карточки"""
    member_id: int = Field(..., description="ID карточки родственника")
    invitation_type: str = "claim_member"


class InvitationResponse(BaseModel):
    """Ответ с данными приглашения"""
    id: int
    code: str
    family_id: int
    invitation_type: str
    target_member_id: Optional[int]
    expires_at: datetime
    used_at: Optional[datetime]
    used_by_user_id: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationCode(BaseModel):
    """Ввод кода приглашения"""
    code: str = Field(..., min_length=4, max_length=20, description="Код приглашения")


class ClaimInvitationResponse(BaseModel):
    """Ответ после активации приглашения"""
    success: bool
    message: str
    family_id: int
    family_name: str
    member_id: Optional[int]
    requires_profile_completion: bool = False