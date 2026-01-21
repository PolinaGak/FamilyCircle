from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Chat(Base):
    __tablename__ = "chat"

    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    is_event = Column(Boolean, nullable=False, default=False, index=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    family = relationship("Family")
    event = relationship("Event")
    created_by = relationship("User")