from sqlalchemy import Column, Integer, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from .enums import RelationshipType
from ..database import Base

class Relationship(Base):
    __tablename__ = "relationship"

    id = Column(Integer, primary_key=True)
    from_member_id = Column(Integer, ForeignKey("family_member.id"), nullable=False, index=True)
    to_member_id = Column(Integer, ForeignKey("family_member.id"), nullable=False, index=True)
    relationship_type = Column(Enum(RelationshipType), nullable=False, index=True)

    __table_args__ = (
        Index('ix_relationship_from_member', 'from_member_id'),
        Index('ix_relationship_to_member', 'to_member_id'),
        Index('ix_relationship_type_from', 'relationship_type', 'from_member_id'),
    )

    from_member = relationship("FamilyMember", foreign_keys=[from_member_id], back_populates="outgoing_relationships")
    to_member = relationship("FamilyMember", foreign_keys=[to_member_id], back_populates="incoming_relationships")