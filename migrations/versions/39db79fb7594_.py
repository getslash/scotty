"""empty message

Revision ID: 39db79fb7594
Revises: 985b368eb54f
Create Date: 2016-09-08 14:07:39.963767

"""

# revision identifiers, used by Alembic.
revision = '39db79fb7594'
down_revision = '985b368eb54f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('key',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('key', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('description')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('key')
    ### end Alembic commands ###
