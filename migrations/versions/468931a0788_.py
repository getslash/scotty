"""empty message

Revision ID: 468931a0788
Revises: 2abcb206208
Create Date: 2015-05-05 15:36:33.473255

"""

# revision identifiers, used by Alembic.
revision = '468931a0788'
down_revision = '2abcb206208'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tag',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('beam_id', sa.Integer(), nullable=True),
    sa.Column('tag', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['beam_id'], ['beam.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('beam_id', 'tag', name='uix_beam_tag')
    )
    op.drop_table('alias')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('alias',
    sa.Column('id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('beam_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['beam_id'], ['beam.id'], name='alias_beam_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='alias_pkey')
    )
    op.drop_table('tag')
    ### end Alembic commands ###
