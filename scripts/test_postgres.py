"""Run memory/weather integration tests in a fresh disposable PostgreSQL database."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
from dotenv import dotenv_values
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

root=Path(__file__).resolve().parent.parent
url=make_url(dotenv_values(root / '.env').get('MEMORY_DATABASE_URL',''))
if url.get_backend_name()!='postgresql':raise SystemExit('请先运行 scripts/setup-memory-db.sh')
name='persona_test_'+secrets.token_hex(6)
connection=psycopg.connect(host=url.host,port=url.port,user=url.username,password=url.password,dbname='postgres',autocommit=True)
try:
    connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    child={**os.environ,'TEST_POSTGRES_URL':url.set(database=name).render_as_string(hide_password=False)}
    result=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_memory.py','tests/test_weather.py'],cwd=root,env=child)
finally:
    connection.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
    connection.close()
raise SystemExit(result.returncode)
