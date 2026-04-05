from sqlalchemy import Column, Integer, ForeignKey, Enum, PrimaryKeyConstraint, DateTime, func
from sqlalchemy.orm import relationship
from .enums import InvitationStatus
from ..database import Base

class EventParticipant(Base):
    __tablename__ = "event_participant"
    __table_args__ = (PrimaryKeyConstraint("event_id", "user_id"),)

    event_id = Column(Integer, ForeignKey("event.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    status = Column(Enum(InvitationStatus), default=InvitationStatus.invited)
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)

    event = relationship("Event", back_populates="participants")
    user = relationship("User")