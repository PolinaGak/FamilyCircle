from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from .family_member import FamilyMemberResponse


class FamilyBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Название семьи")


class FamilyCreate(FamilyBase):
    pass


class FamilyResponse(FamilyBase):
    id: int
    admin_user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FamilyDetailResponse(FamilyResponse):
    members: List["FamilyMemberResponse"] = []



FamilyDetailResponse.model_rebuild()