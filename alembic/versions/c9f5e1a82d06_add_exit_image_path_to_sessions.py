"""add exit_image_path to parking_sessions

Revision ID: c9f5e1a82d06
Revises: b8e4d2c71f05
Create Date: 2026-10-20 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9f5e1a82d06'
down_revision: Union[str, None] = 'b8e4d2c71f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('parking_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('exit_image_path', sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('parking_sessions', schema=None) as batch_op:
        batch_op.drop_column('exit_image_path')
