from sqlalchemy import Column, Integer, ForeignKey, PrimaryKeyConstraint, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .enums import InvitationStatus
from ..database import Base


class AlbumMember(Base):
    __tablename__ = "album_member"

    album_id = Column(Integer, ForeignKey("album.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)

    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)

    status = Column(Enum(InvitationStatus), default=InvitationStatus.accepted)

    added_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    album = relationship("Album", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="album_memberships")
    added_by = relationship("User", foreign_keys=[added_by_user_id])

    def is_admin(self) -> bool:
        """Является ли пользователь администратором альбома"""
        return self.can_edit and self.can_delete