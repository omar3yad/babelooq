"""add company_name and card_code to subscribers

Revision ID: 7f2e1a9d4b83
Revises: 4c91a7e2b109
Create Date: 2026-10-07 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f2e1a9d4b83'
down_revision: Union[str, None] = '4c91a7e2b109'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('subscribers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('card_code', sa.String(length=50), nullable=True))

    # Create index for card_code after adding column
    with op.batch_alter_table('subscribers', schema=None) as batch_op:
        batch_op.create_index('ix_subscribers_card_code', ['card_code'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('subscribers', schema=None) as batch_op:
        batch_op.drop_index('ix_subscribers_card_code')
        batch_op.drop_column('card_code')
        batch_op.drop_column('company_name')
