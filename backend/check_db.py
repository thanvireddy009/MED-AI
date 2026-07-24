from core.database import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute('SELECT COUNT(*) as count FROM llm_extracted_data')
print('llm_extracted_data rows:', dict(cur.fetchone()))

cur.execute('SELECT file_name FROM llm_extracted_data LIMIT 5')
print('Sample file names in llm_extracted_data:')
for r in cur.fetchall():
    print(' ', r['file_name'])

cur.execute('SELECT file_name, status, extracted_data IS NOT NULL as has_data FROM documents ORDER BY upload_date DESC LIMIT 8')
print('\nRecent documents:')
for r in cur.fetchall():
    print(' ', dict(r))

cur.close()
conn.close()
