import sqlite3
from pathlib import Path
path = Path('xtreem.db')
print('DB exists:', path.exists(), path.resolve())
conn = sqlite3.connect(path)
cur = conn.cursor()
tables = ['booking_status_history', 'customer_memberships', 'bookings', 'wash_records', 'payments', 'vehicles', 'customers']
for tbl in tables:
    try:
        cur.execute(f'DELETE FROM {tbl}')
        print(f'Deleted rows from {tbl}:', cur.rowcount)
    except Exception as e:
        print('Error', tbl, e)
conn.commit()
conn.close()
