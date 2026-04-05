from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
from .enums import ThemeType

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    is_verified = Column(Boolean, nullable=False, default=False, index=True)
    theme = Column(Enum(ThemeType), default=ThemeType.light, nullable=False)

    album_memberships = relationship("AlbumMember", back_populates="user", foreign_keys="AlbumMember.user_id")
    photos_uploaded = relationship("Photo", back_populates="uploaded_by")
    chat_memberships = relationship("ChatMember", back_populates="user", foreign_keys="ChatMember.user_id")
    messages_sent = relationship("Message", back_populates="sender")
    events_created = relationship("Event", back_populates="created_by")