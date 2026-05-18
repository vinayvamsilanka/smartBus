import sqlite3
import os

db_path = 'instance/smartbus.db'

if not os.path.exists(db_path):
    print(f"Error: Database {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables_to_patch = ['cities', 'graph_routes', 'buses', 'routes', 'bus_schedules']

for table in tables_to_patch:
    print(f"Migrating table: {table}...")
    try:
        # Check if column exists first
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_active' not in columns:
            print(f"  Adding 'is_active' column to {table}...")
            # SQLite added column with default 1 (True)
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN is_active BOOLEAN DEFAULT 1")
            conn.commit()
            print(f"  Successfully added 'is_active' to {table}.")
        else:
            print(f"  Column 'is_active' already exists in {table}.")
    except Exception as e:
        print(f"Error migrating {table}: {e}")

conn.close()
print("Migration completed.")
