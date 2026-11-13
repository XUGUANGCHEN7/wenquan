import os
from pathlib import Path
import subprocess
import sys

import pytest

from sqlalchemy import create_engine, inspect, text


@pytest.mark.parametrize('partially_created', [False, True])
def test_member_migration_preserves_existing_identity_and_balance(tmp_path, partially_created):
    url = 'sqlite+pysqlite:///' + str(tmp_path / 'migration.sqlite3')
    env = {**os.environ, 'DATABASE_URL': url, 'PYTHONDONTWRITEBYTECODE': '1'}
    root = Path(__file__).resolve().parents[1]

    def migrate(target):
        command = 'downgrade' if target == 'af3dbb89f3d4' else 'upgrade'
        result = subprocess.run([sys.executable, '-B', '-m', 'alembic', command, target],
                                cwd=root, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr

    result = subprocess.run([sys.executable, '-B', '-m', 'alembic', 'upgrade', 'af3dbb89f3d4'],
                            cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO members(id,nickname,created_at) VALUES ('old','老会员',CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO member_accounts(member_id,principal_cents,gift_cents,updated_at) VALUES ('old',2300,200,CURRENT_TIMESTAMP)"))
        conn.execute(text("INSERT INTO member_identities(id,appid,openid,member_id,created_at) VALUES ('old-id','app','openid','old',CURRENT_TIMESTAMP)"))
    if partially_created:
        # Development startup uses create_all: it can create a new table but cannot add member columns.
        from app.modules.identity.models import MemberSession
        MemberSession.__table__.create(engine)
    migrate('head')
    with engine.connect() as conn:
        row = conn.execute(text("SELECT nickname,phone,phone_verified_at,status FROM members WHERE id='old'")).one()
        assert tuple(row) == ('老会员', None, None, 'ACTIVE')
        assert tuple(conn.execute(text("SELECT principal_cents,gift_cents FROM member_accounts WHERE member_id='old'")).one()) == (2300,200)
    assert 'member_sessions' in inspect(engine).get_table_names()
    migrate('af3dbb89f3d4')
    migrate('head')
    with engine.connect() as conn:
        assert conn.execute(text("SELECT member_id FROM member_identities WHERE id='old-id'")).scalar() == 'old'
        assert conn.execute(text("SELECT principal_cents FROM member_accounts WHERE member_id='old'")).scalar() == 2300
    engine.dispose()
