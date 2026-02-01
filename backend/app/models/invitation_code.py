from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class InvitationCode(Base):
    __tablename__ = "invitation_code"

    code = Column(String, primary_key=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    family = relationship("Family")
    created_by = relationship("User", foreign_keys=[created_by_user_id])