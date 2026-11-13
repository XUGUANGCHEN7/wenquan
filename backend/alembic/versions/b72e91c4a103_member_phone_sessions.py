"""Member verified phone and revocable sessions; retain legacy members and wallets."""
from alembic import op
import sqlalchemy as sa

revision = 'b72e91c4a103'
down_revision = 'af3dbb89f3d4'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing = inspector.has_table('member_sessions')
    if existing:
        expected = {
            'token_hash': ('VARCHAR(64)', False), 'appid': ('VARCHAR(64)', False),
            'openid': ('VARCHAR(128)', False), 'member_id': ('VARCHAR(64)', True),
            'purpose': ('VARCHAR(16)', False), 'expires_at': ('DATETIME', False),
            'created_at': ('DATETIME', False),
        }
        actual = {c['name']: (str(c['type']), c['nullable']) for c in inspector.get_columns('member_sessions')}
        if actual != expected or inspector.get_pk_constraint('member_sessions')['constrained_columns'] != ['token_hash']:
            raise RuntimeError('Existing member_sessions schema differs; inspect before migrating')
    with op.batch_alter_table('members') as batch:
        batch.add_column(sa.Column('phone', sa.String(20), nullable=True))
        batch.add_column(sa.Column('phone_verified_at', sa.DateTime(), nullable=True))
        batch.add_column(sa.Column('status', sa.String(16), nullable=False, server_default='ACTIVE'))
        batch.create_unique_constraint('uq_member_phone', ['phone'])
    if not existing:
        op.create_table('member_sessions',
            sa.Column('token_hash', sa.String(64), primary_key=True),
            sa.Column('appid', sa.String(64), nullable=False),
            sa.Column('openid', sa.String(128), nullable=False),
            sa.Column('member_id', sa.String(64), sa.ForeignKey('members.id'), nullable=True),
            sa.Column('purpose', sa.String(16), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False))
    if not existing or not any(index['name'] == 'ix_member_sessions_expires_at' for index in inspector.get_indexes('member_sessions')):
        op.create_index('ix_member_sessions_expires_at', 'member_sessions', ['expires_at'])


def downgrade():
    op.drop_table('member_sessions')
    with op.batch_alter_table('members') as batch:
        batch.drop_constraint('uq_member_phone', type_='unique')
        batch.drop_column('status')
        batch.drop_column('phone_verified_at')
        batch.drop_column('phone')
