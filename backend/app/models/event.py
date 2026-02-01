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

    family = relationship("Family", foreign_keys=[family_id])
    created_by = relationship("User")