"""empty message

Revision ID: 3a91facdf84
Revises: 14bbb53415d
Create Date: 2015-11-24 15:58:15.340702

"""

# revision identifiers, used by Alembic.
revision = '3a91facdf84'
down_revision = '14bbb53415d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('file', sa.Column('mtime', sa.DateTime(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('file', 'mtime')
    ### end Alembic commands ###
