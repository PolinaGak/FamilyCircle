from sqlalchemy import Column, Integer, ForeignKey, PrimaryKeyConstraint, Boolean, Enum
from .enums import InvintationStatus
from ..database import Base

class AlbumMember(Base):
    __tablename__ = "album_member"
    __table_args__ = (PrimaryKeyConstraint("album_id", "user_id"),)

    album_id = Column(Integer, ForeignKey("album.id"))
    user_id = Column(Integer, ForeignKey("user.id"))
    can_edit = Column(Boolean, default=False)
    status = Column(Enum(InvintationStatus), default=InvintationStatus.invited)
