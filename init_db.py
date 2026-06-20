import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "database" / "bug_tracking.sql"
DEFAULT_ORG_NAME = "Default Organization"

load_dotenv(BASE_DIR / ".env")


def split_sql_statements(sql_text):
    return [statement.strip() for statement in sql_text.split(";") if statement.strip()]


def column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (os.getenv("DB_NAME", "bug_tracking_db"), table_name, column_name),
    )
    return cursor.fetchone()[0] > 0


def run_if_needed(cursor, statement):
    try:
        cursor.execute(statement)
    except Error as exc:
        if exc.errno not in {1005, 1060, 1061, 1062, 1091, 1826}:
            raise


def run_migrations(cursor):
    cursor.execute(f"USE {os.getenv('DB_NAME', 'bug_tracking_db')}")
    cursor.execute(
        "INSERT IGNORE INTO organizations (name) VALUES (%s)",
        (DEFAULT_ORG_NAME,),
    )
    cursor.execute("SELECT id FROM organizations WHERE name = %s", (DEFAULT_ORG_NAME,))
    default_org_id = cursor.fetchone()[0]

    if not column_exists(cursor, "users", "organization_id"):
        cursor.execute("ALTER TABLE users ADD COLUMN organization_id INT NULL AFTER id")
        cursor.execute("UPDATE users SET organization_id = %s WHERE organization_id IS NULL", (default_org_id,))
        cursor.execute("ALTER TABLE users MODIFY organization_id INT NOT NULL")

    if not column_exists(cursor, "bugs", "organization_id"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN organization_id INT NULL AFTER id")
        cursor.execute(
            """
            UPDATE bugs
            JOIN users ON bugs.reporter_id = users.id
            SET bugs.organization_id = users.organization_id
            WHERE bugs.organization_id IS NULL
            """
        )
        cursor.execute("UPDATE bugs SET organization_id = %s WHERE organization_id IS NULL", (default_org_id,))
        cursor.execute("ALTER TABLE bugs MODIFY organization_id INT NOT NULL")

    if not column_exists(cursor, "bugs", "category"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN category VARCHAR(80) NOT NULL DEFAULT 'General' AFTER reproduction_steps")

    if not column_exists(cursor, "bugs", "external_issue_url"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN external_issue_url VARCHAR(255) NULL AFTER screenshot_path")

    run_if_needed(cursor, "CREATE INDEX idx_users_organization ON users (organization_id)")
    run_if_needed(cursor, "CREATE INDEX idx_bugs_organization ON bugs (organization_id)")
    run_if_needed(cursor, "CREATE INDEX idx_bugs_category ON bugs (category)")
    run_if_needed(
        cursor,
        """
        ALTER TABLE users
        ADD CONSTRAINT fk_users_organization
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        """,
    )
    run_if_needed(
        cursor,
        """
        ALTER TABLE bugs
        ADD CONSTRAINT fk_bugs_organization
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        """,
    )


def main():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")

    if not SCHEMA_FILE.exists():
        print(f"FAILED: Schema file not found: {SCHEMA_FILE}")
        return

    print(f"Initializing database from {SCHEMA_FILE}...")

    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connection_timeout=5,
        )
        cursor = conn.cursor()

        for statement in split_sql_statements(SCHEMA_FILE.read_text(encoding="utf-8")):
            run_if_needed(cursor, statement)

        run_migrations(cursor)
        conn.commit()
        cursor.close()
        conn.close()
        print("OK: Database and tables are ready.")
    except Error as exc:
        print(f"FAILED: Could not initialize database: {exc}")


if __name__ == "__main__":
    main()
