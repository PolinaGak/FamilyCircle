from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List


class MessageBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000, description="Текст сообщения")


class MessageCreate(MessageBase):
    pass


class MessageUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class MessageResponse(MessageBase):
    id: int
    chat_id: int
    sender_user_id: int
    sender_name: Optional[str] = None
    sent_at: datetime
    is_edited: bool
    edited_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
    chat_id: int