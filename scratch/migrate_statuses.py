import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

host = os.getenv("DB_HOST", "127.0.0.1")
port = int(os.getenv("DB_PORT", "3306"))
user = os.getenv("DB_USER", "root")
password = os.getenv("DB_PASSWORD", "")
database = os.getenv("DB_NAME", "bug_tracking_db")

print(f"Connecting to database {database}...")
conn = mysql.connector.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database=database
)
cursor = conn.cursor()

try:
    print("Modifying bugs.status column...")
    cursor.execute("ALTER TABLE bugs MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'To Do'")
    
    print("Mapping status values...")
    cursor.execute("UPDATE bugs SET status = 'To Do' WHERE status = 'Open'")
    cursor.execute("UPDATE bugs SET status = 'Testing' WHERE status = 'Resolved'")
    cursor.execute("UPDATE bugs SET status = 'Done' WHERE status = 'Closed'")
    
    conn.commit()
    print("Migration successful!")
except Exception as e:
    conn.rollback()
    print("Error during migration:", e)
finally:
    cursor.close()
    conn.close()
