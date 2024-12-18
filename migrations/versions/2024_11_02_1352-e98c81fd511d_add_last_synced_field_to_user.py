"""add_last_synced_field_to_user

Revision ID: e98c81fd511d
Revises: d22ae315983a
Create Date: 2024-11-02 13:52:53.789429

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'e98c81fd511d'
down_revision: Union[str, None] = 'd22ae315983a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Step 1: Add the new column as nullable=True
    op.add_column('user', sa.Column('last_synced', sa.DateTime(), nullable=True))
    default_value = datetime.now()
    op.execute(f"UPDATE user SET last_synced = '{default_value}'")
    op.alter_column('user', 'last_synced', existing_type=sa.DateTime(), nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # delete the column
    op.drop_column('user', 'last_synced')
    # ### end Alembic commands ###
