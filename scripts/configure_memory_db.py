"""Initialize project-local database credentials without printing them."""
from pathlib import Path
import re
import secrets
from dotenv import dotenv_values

root = Path(__file__).resolve().parent.parent
path = root / '.env'
if not path.exists(): path.write_text((root / '.env.example').read_text())
values = dotenv_values(path)
password = values.get('POSTGRES_PASSWORD') or secrets.token_urlsafe(32)
url = values.get('MEMORY_DATABASE_URL')
if url and not url.startswith(('sqlite:', 'postgresql+psycopg://persona:')):
    raise SystemExit('已有自定义数据库配置；未覆盖。请手动检查本地 MEMORY_DATABASE_URL。')
changes = {'POSTGRES_PASSWORD':password,
           'MEMORY_DATABASE_URL':f'postgresql+psycopg://persona:{password}@127.0.0.1:54329/persona'}
content=path.read_text()
for key,value in changes.items():
    if re.search(r'(?m)^'+key+'=',content):content=re.sub(r'(?m)^'+key+'=.*$',key+'='+value,content)
    else:content+='\n'+key+'='+value+'\n'
path.write_text(content)
path.chmod(0o600)
print('本地数据库配置已就绪；凭据未显示，也不会提交。')
