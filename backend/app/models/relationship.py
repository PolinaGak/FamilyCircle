from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .enums import  RelationshipType
from ..database import Base

class Relationship(Base):
    __tablename__ = "relationship"

    id = Column(Integer, primary_key=True)
    from_member_id = Column(Integer, ForeignKey("family_member.id"), nullable=False)
    to_member_id = Column(Integer, ForeignKey("family_member.id"), nullable=False)
    relationship_type = Enum(RelationshipType)

    from_member = relationship("FamilyMember", foreign_keys=[from_member_id])
    to_member = relationship("FamilyMember", foreign_keys=[to_member_id])