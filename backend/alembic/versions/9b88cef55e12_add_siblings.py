"""add siblings to relationshiptype

Revision ID: 9b88cef55e12
Revises: ab94bbf88c3a
Create Date: 2026-04-05 22:35:10.658484

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9b88cef55e12'
down_revision: Union[str, Sequence[str], None] = 'ab94bbf88c3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Добавляем новые значения в существующий ENUM
    op.execute("ALTER TYPE relationshiptype ADD VALUE IF NOT EXISTS 'brother'")
    op.execute("ALTER TYPE relationshiptype ADD VALUE IF NOT EXISTS 'sister'")

def downgrade() -> None:
    pass