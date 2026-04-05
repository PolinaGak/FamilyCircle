from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Chat(Base):
    __tablename__ = "chat"

    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    is_event = Column(Boolean, nullable=False, default=False, index=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=True, unique=True)
    created_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    title = Column(String, nullable=True)

    family = relationship("Family")
    event = relationship("Event", back_populates="chat")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    members = relationship("ChatMember", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.sent_at.desc()")