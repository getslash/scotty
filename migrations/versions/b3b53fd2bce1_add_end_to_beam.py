"""add end to beam

Revision ID: b3b53fd2bce1
Revises: 39db79fb7594
Create Date: 2020-04-05 13:23:02.500021

"""

# revision identifiers, used by Alembic.
revision = 'b3b53fd2bce1'
down_revision = '39db79fb7594'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('beam', sa.Column('end', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_beam_end'), 'beam', ['end'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_beam_end'), table_name='beam')
    op.drop_column('beam', 'end')
    # ### end Alembic commands ###
