import sqlite3

connection = sqlite3.connect("autoguard.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    image_path TEXT NOT NULL,
    note TEXT DEFAULT '',
    status TEXT DEFAULT 'unreviewed'
)
""")

connection.commit()
connection.close()

print("Database and table created successfully.")