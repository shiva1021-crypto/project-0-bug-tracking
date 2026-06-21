import os
import re
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


def table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """,
        (os.getenv("DB_NAME", "bug_tracking_db"), table_name),
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
    default_org_id = None

    if not column_exists(cursor, "registration_requests", "verification_token_hash"):
        cursor.execute(
            "ALTER TABLE registration_requests ADD COLUMN verification_token_hash CHAR(64) NULL AFTER requester_ip"
        )
    if not column_exists(cursor, "registration_requests", "verified_at"):
        cursor.execute(
            "ALTER TABLE registration_requests ADD COLUMN verified_at DATETIME NULL AFTER verification_token_hash"
        )
    cursor.execute(
        "ALTER TABLE registration_requests MODIFY requested_role "
        "ENUM('admin', 'project_manager', 'developer', 'tester') NOT NULL DEFAULT 'tester'"
    )

    if not column_exists(cursor, "users", "organization_id"):
        cursor.execute(
            "INSERT IGNORE INTO organizations (name) VALUES (%s)",
            (DEFAULT_ORG_NAME,),
        )
        cursor.execute("SELECT id FROM organizations WHERE name = %s", (DEFAULT_ORG_NAME,))
        default_org_id = cursor.fetchone()[0]
        cursor.execute("ALTER TABLE users ADD COLUMN organization_id INT NULL AFTER id")
        cursor.execute("UPDATE users SET organization_id = %s WHERE organization_id IS NULL", (default_org_id,))
        cursor.execute("ALTER TABLE users MODIFY organization_id INT NOT NULL")

    if not column_exists(cursor, "bugs", "organization_id"):
        if default_org_id is None:
            cursor.execute(
                "INSERT IGNORE INTO organizations (name) VALUES (%s)",
                (DEFAULT_ORG_NAME,),
            )
            cursor.execute("SELECT id FROM organizations WHERE name = %s", (DEFAULT_ORG_NAME,))
            default_org_id = cursor.fetchone()[0]
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

    if not column_exists(cursor, "bugs", "project_id"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN project_id INT NULL AFTER organization_id")
    if not column_exists(cursor, "bugs", "issue_key"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN issue_key VARCHAR(30) NULL AFTER project_id")
    if not column_exists(cursor, "bugs", "issue_type"):
        cursor.execute(
            "ALTER TABLE bugs ADD COLUMN issue_type "
            "ENUM('Epic', 'Story', 'Task', 'Bug', 'Subtask') NOT NULL DEFAULT 'Bug' "
            "AFTER issue_key"
        )
    if not column_exists(cursor, "bugs", "parent_id"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN parent_id INT NULL AFTER issue_type")
    if not column_exists(cursor, "bugs", "labels"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN labels VARCHAR(255) NULL AFTER external_issue_url")
    if not column_exists(cursor, "bugs", "story_points"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN story_points INT NULL AFTER labels")
    if not column_exists(cursor, "bugs", "due_date"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN due_date DATE NULL AFTER story_points")

    if not table_exists(cursor, "saved_filters"):
        cursor.execute(
            """
            CREATE TABLE saved_filters (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                organization_id INT NOT NULL,
                name VARCHAR(120) NOT NULL,
                filter_data JSON NOT NULL,
                is_shared TINYINT(1) NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_saved_filters_user (user_id, organization_id),
                CONSTRAINT fk_saved_filters_user
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_saved_filters_organization
                    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
            )
            """
        )

    if not table_exists(cursor, "versions"):
        cursor.execute(
            """
            CREATE TABLE versions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                organization_id INT NOT NULL,
                project_id INT NOT NULL,
                name VARCHAR(120) NOT NULL,
                description TEXT,
                release_date DATE NULL,
                status ENUM('unreleased', 'released', 'archived') NOT NULL DEFAULT 'unreleased',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_versions_project_name (project_id, name),
                INDEX idx_versions_organization (organization_id),
                INDEX idx_versions_project (project_id),
                CONSTRAINT fk_versions_organization
                    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                CONSTRAINT fk_versions_project
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )
    if not column_exists(cursor, "bugs", "fix_version_id"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN fix_version_id INT NULL AFTER sprint_id")

    if not table_exists(cursor, "time_entries"):
        cursor.execute(
            """
            CREATE TABLE time_entries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bug_id INT NOT NULL,
                user_id INT NOT NULL,
                hours_spent DECIMAL(10,2) NOT NULL,
                description TEXT,
                logged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_time_entries_bug (bug_id),
                INDEX idx_time_entries_user (user_id),
                CONSTRAINT fk_time_entries_bug
                    FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
                CONSTRAINT fk_time_entries_user
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
    if not column_exists(cursor, "bugs", "time_estimate"):
        cursor.execute(
            "ALTER TABLE bugs ADD COLUMN time_estimate DECIMAL(10,2) NULL AFTER due_date"
        )
    if not column_exists(cursor, "bugs", "time_remaining"):
        cursor.execute(
            "ALTER TABLE bugs ADD COLUMN time_remaining DECIMAL(10,2) NULL AFTER time_estimate"
        )

    if not table_exists(cursor, "dashboard_widgets"):
        cursor.execute(
            """
            CREATE TABLE dashboard_widgets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                organization_id INT NOT NULL,
                user_id INT NULL,
                widget_type VARCHAR(50) NOT NULL,
                title VARCHAR(120) NOT NULL,
                config JSON DEFAULT NULL,
                position INT NOT NULL DEFAULT 0,
                width ENUM('full', 'half', 'third') NOT NULL DEFAULT 'full',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_dw_org (organization_id),
                INDEX idx_dw_user (user_id),
                CONSTRAINT fk_dw_org
                    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                CONSTRAINT fk_dw_user
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

    if not table_exists(cursor, "automation_rules"):
        cursor.execute(
            """
            CREATE TABLE automation_rules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                organization_id INT NOT NULL,
                project_id INT NULL,
                name VARCHAR(120) NOT NULL,
                trigger_event ENUM('issue_created', 'status_changed', 'field_updated') NOT NULL,
                conditions JSON DEFAULT NULL,
                actions JSON NOT NULL,
                enabled TINYINT(1) NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ar_org (organization_id),
                INDEX idx_ar_project (project_id),
                INDEX idx_ar_trigger (trigger_event),
                CONSTRAINT fk_ar_org
                    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                CONSTRAINT fk_ar_project
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )

    if not table_exists(cursor, "custom_field_definitions"):
        cursor.execute(
            """
            CREATE TABLE custom_field_definitions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                organization_id INT NOT NULL,
                project_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                field_type ENUM('text', 'number', 'date', 'dropdown', 'checkbox') NOT NULL,
                options JSON DEFAULT NULL,
                required TINYINT(1) NOT NULL DEFAULT 0,
                display_order INT NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_cfd_org (organization_id),
                INDEX idx_cfd_project (project_id),
                CONSTRAINT fk_cfd_org
                    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                CONSTRAINT fk_cfd_project
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )
    if not table_exists(cursor, "custom_field_values"):
        cursor.execute(
            """
            CREATE TABLE custom_field_values (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bug_id INT NOT NULL,
                field_id INT NOT NULL,
                value TEXT,
                UNIQUE KEY uq_cfv_bug_field (bug_id, field_id),
                INDEX idx_cfv_bug (bug_id),
                INDEX idx_cfv_field (field_id),
                CONSTRAINT fk_cfv_bug
                    FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
                CONSTRAINT fk_cfv_field
                    FOREIGN KEY (field_id) REFERENCES custom_field_definitions(id) ON DELETE CASCADE
            )
            """
        )

    if not table_exists(cursor, "issue_links"):
        cursor.execute(
            """
            CREATE TABLE issue_links (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bug_id_a INT NOT NULL,
                bug_id_b INT NOT NULL,
                link_type ENUM('blocks', 'relates_to', 'duplicates', 'clones') NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_issue_links_pair (bug_id_a, bug_id_b, link_type),
                INDEX idx_issue_links_a (bug_id_a),
                INDEX idx_issue_links_b (bug_id_b),
                CONSTRAINT fk_issue_links_a
                    FOREIGN KEY (bug_id_a) REFERENCES bugs(id) ON DELETE CASCADE,
                CONSTRAINT fk_issue_links_b
                    FOREIGN KEY (bug_id_b) REFERENCES bugs(id) ON DELETE CASCADE
            )
            """
        )

    if not table_exists(cursor, "sprints"):
        cursor.execute(
            """
            CREATE TABLE sprints (
                id INT AUTO_INCREMENT PRIMARY KEY,
                organization_id INT NOT NULL,
                project_id INT NOT NULL,
                name VARCHAR(120) NOT NULL,
                goal TEXT,
                start_date DATE NULL,
                end_date DATE NULL,
                status ENUM('active', 'closed', 'future') NOT NULL DEFAULT 'future',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_sprints_organization (organization_id),
                INDEX idx_sprints_project (project_id),
                INDEX idx_sprints_status (status),
                CONSTRAINT fk_sprints_organization
                    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                CONSTRAINT fk_sprints_project
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )
    if not column_exists(cursor, "bugs", "sprint_id"):
        cursor.execute("ALTER TABLE bugs ADD COLUMN sprint_id INT NULL AFTER project_id")

    cursor.execute("SELECT id, name FROM organizations ORDER BY id")
    organizations = cursor.fetchall()
    projects_by_org = {}
    for organization_id, organization_name in organizations:
        cursor.execute(
            "SELECT id, project_key FROM projects WHERE organization_id = %s ORDER BY id LIMIT 1",
            (organization_id,),
        )
        project = cursor.fetchone()
        if not project:
            project_key = re.sub(r"[^A-Za-z0-9]", "", organization_name).upper()[:6] or f"ORG{organization_id}"
            cursor.execute(
                """
                INSERT INTO projects (organization_id, name, project_key, description)
                VALUES (%s, %s, %s, %s)
                """,
                (organization_id, "General", project_key, "Default project"),
            )
            project = (cursor.lastrowid, project_key)
        projects_by_org[organization_id] = project

    cursor.execute(
        "SELECT id, organization_id FROM bugs WHERE project_id IS NULL OR issue_key IS NULL ORDER BY id"
    )
    migrated_counts = {}
    for bug_id, organization_id in cursor.fetchall():
        project_id, project_key = projects_by_org[organization_id]
        migrated_counts[project_id] = migrated_counts.get(project_id, 0) + 1
        issue_number = migrated_counts[project_id]
        cursor.execute(
            "UPDATE bugs SET project_id = %s, issue_key = %s WHERE id = %s",
            (project_id, f"{project_key}-{issue_number}", bug_id),
        )

    for project_id, count in migrated_counts.items():
        cursor.execute(
            "UPDATE projects SET next_issue_number = GREATEST(next_issue_number, %s) WHERE id = %s",
            (count + 1, project_id),
        )

    cursor.execute("ALTER TABLE bugs MODIFY project_id INT NOT NULL")
    cursor.execute("ALTER TABLE bugs MODIFY issue_key VARCHAR(30) NOT NULL")

    run_if_needed(cursor, "CREATE INDEX idx_users_organization ON users (organization_id)")
    run_if_needed(cursor, "CREATE INDEX idx_bugs_organization ON bugs (organization_id)")
    run_if_needed(cursor, "CREATE INDEX idx_bugs_category ON bugs (category)")
    run_if_needed(cursor, "CREATE INDEX idx_bugs_project ON bugs (project_id)")
    run_if_needed(cursor, "CREATE INDEX idx_bugs_issue_type ON bugs (issue_type)")
    run_if_needed(cursor, "CREATE INDEX idx_bugs_parent ON bugs (parent_id)")
    run_if_needed(
        cursor,
        "CREATE UNIQUE INDEX uq_bugs_org_issue_key ON bugs (organization_id, issue_key)",
    )
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
        ADD CONSTRAINT fk_bugs_project
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        """,
    )
    run_if_needed(
        cursor,
        """
        ALTER TABLE bugs
        ADD CONSTRAINT fk_bugs_parent
        FOREIGN KEY (parent_id) REFERENCES bugs(id) ON DELETE SET NULL
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

    db_name = os.getenv("DB_NAME", "bug_tracking_db")

    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connection_timeout=5,
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cursor.execute(f"USE `{db_name}`")

        sql_text = SCHEMA_FILE.read_text(encoding="utf-8")
        sql_text = sql_text.replace("bug_tracking_db", db_name)
        for statement in split_sql_statements(sql_text):
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
