from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chat.id"), nullable=False)
    sender_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages_sent")