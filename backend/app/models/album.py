from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
from ..database import Base


class Album(Base):
    __tablename__ = "album"

    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=True)
    deletion_notified_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_album_expires_at', 'expires_at'),
        Index('ix_album_family_id', 'family_id'),
        Index('ix_album_event_id', 'event_id'),
        Index('ix_album_is_deleted', 'is_deleted'),
    )

    family = relationship("Family", back_populates="albums")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    event = relationship("Event", back_populates="albums")
    members = relationship("AlbumMember", back_populates="album", cascade="all, delete-orphan")
    photos = relationship("Photo", back_populates="album", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    @property
    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires

    @property
    def hours_until_deletion(self) -> int:
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        delta = expires - now
        if delta.total_seconds() < 0:
            return 0
        return int(delta.total_seconds() // 3600)

    @property
    def should_notify_deletion(self) -> bool:
        if self.is_expired or self.is_deleted:
            return False
        hours_left = self.hours_until_deletion
        return hours_left <= 24 and self.deletion_notified_at is None