from sqlalchemy import Column, Integer, ForeignKey, Enum, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from .enums import InvintationStatus
from ..database import Base

class EventParticipant(Base):
    __tablename__ = "event_participant"
    __table_args__ = (PrimaryKeyConstraint("event_id", "user_id"),)

    event_id = Column(Integer, ForeignKey("event.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    status = Enum(InvintationStatus, default=InvintationStatus.invited)

    event = relationship("Event")
    user = relationship("User")