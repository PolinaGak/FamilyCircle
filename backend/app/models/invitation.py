from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum
from .enums import InvitationType
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
import secrets
import string



def generate_invite_code(length: int = 8) -> str:
    """Генерирует случайный код приглашения"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class Invitation(Base):
    __tablename__ = "invitation"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, index=True, nullable=False, default=generate_invite_code)
    family_id = Column(Integer, ForeignKey("family.id"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    invitation_type = Column(Enum(InvitationType), nullable=False, default='new_member')

    target_member_id = Column(Integer, ForeignKey("family_member.id"), nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by_user_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    family = relationship("Family", foreign_keys=[family_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    used_by = relationship("User", foreign_keys=[used_by_user_id])
    target_member = relationship("FamilyMember", foreign_keys=[target_member_id])