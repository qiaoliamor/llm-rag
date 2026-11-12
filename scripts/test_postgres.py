"""Run memory/weather integration tests in a fresh disposable PostgreSQL database."""
import os
import argparse
from pathlib import Path
import secrets
import subprocess
import sys
from dotenv import dotenv_values
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

parser=argparse.ArgumentParser(description=__doc__)
group=parser.add_mutually_exclusive_group()
group.add_argument('--growth-only',action='store_true',help='Only run the growth/account suite in the disposable database')
group.add_argument('--semantic-memory',action='store_true',help='Run memory, growth and multilingual semantic memory in the disposable database')
group.add_argument('--semantic-weather',action='store_true',help='Run weather, growth and multilingual semantic weather in the disposable database')
group.add_argument('--semantic-emotion',action='store_true',help='Run emotion, growth and multilingual emotion in the disposable database')
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
url=make_url(dotenv_values(root / '.env').get('MEMORY_DATABASE_URL',''))
if url.get_backend_name()!='postgresql':raise SystemExit('请先运行 scripts/setup-memory-db.sh')
name='persona_test_'+secrets.token_hex(6)
connection=psycopg.connect(host=url.host,port=url.port,user=url.username,password=url.password,dbname='postgres',autocommit=True)
try:
    connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    child={**os.environ,'TEST_POSTGRES_URL':url.set(database=name).render_as_string(hide_password=False)}
    paths = (['tests/growth/test_progression.py'] if args.growth_only else
             ['tests/test_emotion.py','tests/growth/test_progression.py','tests/multilingual_emotion'] if args.semantic_emotion else
             ['tests/test_weather.py','tests/growth/test_progression.py','tests/multilingual_weather'] if args.semantic_weather else
             ['tests/test_memory.py','tests/growth/test_progression.py','tests/multilingual_memory'] if args.semantic_memory else
             ['tests/test_memory.py','tests/test_weather.py','tests/test_emotion.py','tests/growth/test_progression.py','tests/multilingual_memory','tests/multilingual_weather','tests/multilingual_emotion'])
    result=subprocess.run([sys.executable,'-m','pytest','-q',*paths],cwd=root,env=child)
finally:
    connection.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
    connection.close()
raise SystemExit(result.returncode)
