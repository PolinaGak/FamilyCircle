from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime, PrimaryKeyConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .enums import InvitationStatus
from ..database import Base

class ChatMember(Base):
    __tablename__ = "chat_member"
    __table_args__ = (PrimaryKeyConstraint("chat_id", "user_id"),)

    chat_id = Column(Integer, ForeignKey("chat.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    is_admin = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(InvitationStatus), default=InvitationStatus.invited)
    added_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    chat = relationship("Chat", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="chat_memberships")
    added_by = relationship("User", foreign_keys=[added_by_user_id])