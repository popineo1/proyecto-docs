"""add_stripe_billing_to_tenants

Revision ID: d1e2f3a4b5c6
Revises: c3f7890abc12
Create Date: 2026-05-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c3f7890abc12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('tenants', sa.Column('stripe_subscription_id', sa.String(255), nullable=True))
    op.add_column('tenants', sa.Column('subscription_status', sa.String(50), nullable=True))
    op.add_column('tenants', sa.Column('subscription_plan', sa.String(100), nullable=True))
    op.add_column('tenants', sa.Column('subscription_period_end', sa.DateTime(), nullable=True))

    op.create_index('ix_tenants_stripe_customer_id', 'tenants', ['stripe_customer_id'], unique=True)
    op.create_unique_constraint('uq_tenants_stripe_subscription_id', 'tenants', ['stripe_subscription_id'])


def downgrade() -> None:
    op.drop_constraint('uq_tenants_stripe_subscription_id', 'tenants', type_='unique')
    op.drop_index('ix_tenants_stripe_customer_id', table_name='tenants')
    op.drop_column('tenants', 'subscription_period_end')
    op.drop_column('tenants', 'subscription_plan')
    op.drop_column('tenants', 'subscription_status')
    op.drop_column('tenants', 'stripe_subscription_id')
    op.drop_column('tenants', 'stripe_customer_id')
