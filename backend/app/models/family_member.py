from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
from .enums import Gender

class FamilyMember(Base):
    __tablename__ = "family_member"

    id = Column(Integer, primary_key=True)
    is_admin = Column(Boolean, nullable=False, default=False, index=True)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    patronymic = Column(String)
    gender = Column(Enum(Gender),default=Gender.female, nullable=False)
    birth_date = Column(DateTime(timezone=True), nullable=False)
    death_date = Column(DateTime(timezone=True))
    phone = Column(String)
    workplace = Column(String)
    residence = Column(String)
    is_active = Column(Boolean, default=False)
    created_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    family = relationship("Family", foreign_keys=[family_id])
    user = relationship("User", foreign_keys=[user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    outgoing_relationships = relationship("Relationship", foreign_keys="Relationship.from_member_id",
                                          back_populates="from_member", cascade="all, delete-orphan")
    incoming_relationships = relationship("Relationship", foreign_keys="Relationship.to_member_id",
                                          back_populates="to_member", cascade="all, delete-orphan")