"""add tiered pricing columns to pricing_rules

Revision ID: 4c91a7e2b109
Revises: 2a316cd66e8b
Create Date: 2026-10-07 18:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c91a7e2b109'
down_revision: Union[str, None] = '2a316cd66e8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('pricing_rules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('first_hour_charge', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('subsequent_hour_charge', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('pricing_rules', schema=None) as batch_op:
        batch_op.drop_column('subsequent_hour_charge')
        batch_op.drop_column('first_hour_charge')
