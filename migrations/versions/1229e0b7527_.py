"""empty message

Revision ID: 1229e0b7527
Revises: 352114acb70
Create Date: 2015-09-03 15:40:41.361236

"""

# revision identifiers, used by Alembic.
revision = '1229e0b7527'
down_revision = '352114acb70'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('file', sa.Column('checksum', sa.String(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('file', 'checksum')
    ### end Alembic commands ###