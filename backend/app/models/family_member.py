from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from ..database import Base

class FamilyMember(Base):
    __tablename__ = "family_member"

    id = Column(Integer, primary_key=True)
    is_admin = Column(Boolean, nullable=False, default=False, index=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    patronymic = Column(String)
    birth_date = Column(DateTime(timezone=True), nullable=False)
    death_date = Column(DateTime(timezone=True))
    phone = Column(String)
    workplace = Column(String)
    residence = Column(String)
    is_active = Column(Boolean, default=True)
    created_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    approved = Column(Boolean, default=False)

    family = relationship("Family", foreign_keys=[family_id])
    user = relationship("User", foreign_keys=[user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])