import os

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error


load_dotenv()


def main():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "bug_tracking_db")

    print(f"Checking MySQL at {host}:{port} as {user}...")

    try:
        server_conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connection_timeout=5,
        )
        server_conn.close()
        print("OK: MySQL server is reachable.")
    except Error as exc:
        print(f"FAILED: Cannot connect to the MySQL server: {exc}")
        print("Start MySQL first, then verify DB_HOST, DB_PORT, DB_USER, and DB_PASSWORD in .env.")
        return

    try:
        db_conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connection_timeout=5,
        )
        db_conn.close()
        print(f"OK: Database '{database}' is reachable.")
    except Error as exc:
        print(f"FAILED: MySQL is running, but the database is not ready: {exc}")
        print("Run database/bug_tracking.sql in MySQL Workbench, then try again.")


if __name__ == "__main__":
    main()
