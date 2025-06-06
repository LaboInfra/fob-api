"""add dns check for proxy

Revision ID: 02add4ad2566
Revises: f781a477bf65
Create Date: 2025-05-29 16:28:41.980348

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '02add4ad2566'
down_revision: Union[str, None] = 'f781a477bf65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('proxy_service_map', sa.Column('latest_dns_check', sa.DateTime(), nullable=True))
    op.add_column('proxy_service_map', sa.Column('latest_dns_check_result', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('proxy_service_map', 'latest_dns_check_result')
    op.drop_column('proxy_service_map', 'latest_dns_check')
    # ### end Alembic commands ###
