"""add columns with enums

Revision ID: c01b970f6d49
Revises: 43b965ce2bfb
Create Date: 2026-02-02 20:11:50.704970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.enums import ThemeType, RelationshipType, InvitationStatus

# revision identifiers, used by Alembic.
revision: str = 'c01b970f6d49'
down_revision: Union[str, Sequence[str], None] = '43b965ce2bfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("DROP TYPE IF EXISTS invintationstatus CASCADE")
    op.execute("CREATE TYPE themetype AS ENUM ('light', 'dark')")
    op.execute("CREATE TYPE relationshiptype AS ENUM ('son', 'daughter', 'mother', 'father', 'spouse', 'partner')")
    op.execute("CREATE TYPE invitationstatus AS ENUM ('invited', 'accepted', 'declined')")

    op.add_column('user', sa.Column('theme', sa.Enum('light', 'dark', name='themetype'), nullable=False, server_default='light'))
    op.add_column('relationship', sa.Column('relationship_type', sa.Enum('son', 'daughter', 'mother', 'father', 'spouse', 'partner', name='relationshiptype'), nullable=True))
    op.add_column('chat_member', sa.Column('status', sa.Enum('invited', 'accepted', 'declined', name='invitationstatus'), nullable=True))
    op.add_column('event_participant', sa.Column('status', sa.Enum('invited', 'accepted', 'declined', name='invitationstatus'), nullable=True))

    op.create_index(op.f('ix_user_is_verified'), 'user', ['is_verified'], unique=False)

    op.execute("UPDATE relationship SET relationship_type = 'spouse' WHERE relationship_type IS NULL")
    op.execute("ALTER TABLE relationship ALTER COLUMN relationship_type SET NOT NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_is_verified'), table_name='user')

    # 2. Удаление колонок
    op.drop_column('user', 'theme')
    op.drop_column('relationship', 'relationship_type')
    op.drop_column('event_participant', 'status')
    op.drop_column('chat_member', 'status')

    op.execute("DROP TYPE IF EXISTS themetype")
    op.execute("DROP TYPE IF EXISTS relationshiptype")
    op.execute("DROP TYPE IF EXISTS invitationstatus")