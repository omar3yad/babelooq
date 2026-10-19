"""add edge plate-capture columns to parking_sessions

Revision ID: b8e4d2c71f05
Revises: 7f2e1a9d4b83
Create Date: 2026-10-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e4d2c71f05'
down_revision: Union[str, None] = '7f2e1a9d4b83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('parking_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('plate_capture_status', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('plate_capture_requested_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('plate_captured_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('plate_confidence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('plate_image_path', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('plate_capture_error', sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('parking_sessions', schema=None) as batch_op:
        batch_op.drop_column('plate_capture_error')
        batch_op.drop_column('plate_image_path')
        batch_op.drop_column('plate_confidence')
        batch_op.drop_column('plate_captured_at')
        batch_op.drop_column('plate_capture_requested_at')
        batch_op.drop_column('plate_capture_status')
