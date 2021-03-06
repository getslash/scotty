"""empty message

Revision ID: e3f9f9c13c
Revises: 52b884ded89
Create Date: 2015-11-02 13:56:17.387911

"""

# revision identifiers, used by Alembic.
revision = 'e3f9f9c13c'
down_revision = '52b884ded89'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_file_beam_id'), 'file', ['beam_id'], unique=False)
    op.create_index(op.f('ix_pin_beam_id'), 'pin', ['beam_id'], unique=False)
    op.drop_constraint('roles_users_role_id_fkey', 'roles_users', type_='foreignkey')
    op.drop_constraint('roles_users_user_id_fkey', 'roles_users', type_='foreignkey')
    op.create_foreign_key(None, 'roles_users', 'user', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'roles_users', 'role', ['role_id'], ['id'], ondelete='CASCADE')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'roles_users', type_='foreignkey')
    op.drop_constraint(None, 'roles_users', type_='foreignkey')
    op.create_foreign_key('roles_users_user_id_fkey', 'roles_users', 'user', ['user_id'], ['id'])
    op.create_foreign_key('roles_users_role_id_fkey', 'roles_users', 'role', ['role_id'], ['id'])
    op.drop_index(op.f('ix_pin_beam_id'), table_name='pin')
    op.drop_index(op.f('ix_file_beam_id'), table_name='file')
    ### end Alembic commands ###
