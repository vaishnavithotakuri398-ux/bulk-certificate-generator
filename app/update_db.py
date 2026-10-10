
import sqlite3

conn = sqlite3.connect("certificates.db")
cursor = conn.cursor()

columns = [
    row[1]
    for row in cursor.execute(
        "PRAGMA table_info(generation_jobs)"
    ).fetchall()
]

if "event_name" not in columns:
    cursor.execute(
        "ALTER TABLE generation_jobs "
        "ADD COLUMN event_name VARCHAR DEFAULT 'Workshop'"
    )
    print("event_name column added successfully.")
else:
    print("event_name column already exists.")

conn.commit()
conn.close()
