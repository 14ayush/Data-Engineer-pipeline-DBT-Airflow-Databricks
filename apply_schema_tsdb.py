from pathlib import Path
import pg8000
import ssl
from urllib.parse import urlparse

# Load connection string from .env file
env_path = Path(__file__).with_name('.env')
if not env_path.exists():
    raise FileNotFoundError('.env file not found')

conn_str = None
for line in env_path.read_text().splitlines():
    if line.strip().startswith('POSTGRE_CONNECTION_KEY='):
        conn_str = line.split('=', 1)[1].strip()
        break

if not conn_str:
    raise ValueError('POSTGRE_CONNECTION_KEY not found in .env')

url = urlparse(conn_str)
params = {
    'host': url.hostname,
    'port': url.port,
    'database': url.path.lstrip('/'),
    'user': url.username,
    'password': url.password,
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
params['ssl_context'] = ctx

ddl_path = Path('Dataset/ddl/walmart_schema.sql')
if not ddl_path.exists():
    raise FileNotFoundError('Dataset/ddl/walmart_schema.sql not found')

sql = ddl_path.read_text()
# Make DDL idempotent: add IF NOT EXISTS to CREATE TABLE statements
import re
sql_transformed = re.sub(r'CREATE\s+TABLE\s+', 'CREATE TABLE IF NOT EXISTS ', sql, flags=re.IGNORECASE)
full_sql = 'CREATE SCHEMA IF NOT EXISTS raw; SET search_path TO raw;\n' + sql_transformed

print('Connecting to database', params['database'])
conn = pg8000.connect(**params)
try:
    cur = conn.cursor()
    cur.execute(full_sql)
    conn.commit()
    print('Schema and tables created (or already existed) in database', params['database'])

    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='raw' ORDER BY table_name;")
    rows = cur.fetchall()
    print('Tables in schema raw:', [r[0] for r in rows])
finally:
    conn.close()
