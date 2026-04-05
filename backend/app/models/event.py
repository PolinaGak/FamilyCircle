from typing import Optional

from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from ..database import Base


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    chat = relationship("Chat", back_populates="event", uselist=False)

    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")
    family = relationship("Family", foreign_keys=[family_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    albums = relationship("Album", back_populates="event", cascade="all, delete-orphan")

    @property
    def chat_id(self) -> Optional[int]:
        """ID связанного чата, если есть"""
        return self.chat.id if self.chat else None