"""Populate the Demo Organization with deterministic, realistic test data."""

import os
import random
import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from config import get_db_connection


SEED = 20260620
ORGANIZATION = "Demo Organization"
ISSUES_PER_PROJECT = 30

PROJECTS = (
    ("WEB", "Customer Web Platform", "Customer-facing web experience and account flows."),
    ("API", "Core API Services", "Shared APIs, authentication, and platform services."),
    ("MOB", "Mobile Applications", "iOS and Android product delivery."),
    ("OPS", "Platform Operations", "Reliability, observability, deployment, and infrastructure."),
    ("DATA", "Data and Analytics", "Reporting, pipelines, dashboards, and data quality."),
)

EXTRA_USERS = (
    ("Ava Chen", "ava.admin@example.com", "admin"),
    ("Noah Williams", "noah.manager@example.com", "project_manager"),
    ("Mia Rodriguez", "mia.manager@example.com", "project_manager"),
    ("Liam Patel", "liam.developer@example.com", "developer"),
    ("Sophia Kim", "sophia.developer@example.com", "developer"),
    ("Ethan Brown", "ethan.developer@example.com", "developer"),
    ("Isabella Garcia", "isabella.developer@example.com", "developer"),
    ("Lucas Martin", "lucas.developer@example.com", "developer"),
    ("Amelia Wilson", "amelia.developer@example.com", "developer"),
    ("Oliver Davis", "oliver.developer@example.com", "developer"),
    ("Harper Moore", "harper.tester@example.com", "tester"),
    ("Elijah Taylor", "elijah.tester@example.com", "tester"),
    ("Evelyn Anderson", "evelyn.tester@example.com", "tester"),
    ("James Thomas", "james.tester@example.com", "tester"),
    ("Charlotte Jackson", "charlotte.tester@example.com", "tester"),
    ("Benjamin White", "benjamin.tester@example.com", "tester"),
)

WORK_ITEMS = (
    "Improve first-time account onboarding",
    "Add project activity summary",
    "Reduce dashboard loading time",
    "Support bulk issue updates",
    "Refine permission management",
    "Build release readiness view",
    "Improve failed login feedback",
    "Add structured audit export",
    "Optimize issue search queries",
    "Create service health dashboard",
    "Improve mobile navigation behavior",
    "Add notification preference controls",
    "Resolve intermittent session expiry",
    "Improve empty states and guidance",
    "Add accessible keyboard navigation",
    "Harden file upload validation",
    "Create monthly delivery report",
    "Improve API error consistency",
    "Add deployment rollback checklist",
    "Resolve duplicate notification delivery",
    "Add data retention controls",
    "Improve comment activity ordering",
    "Create developer workload view",
    "Add project-level quick filters",
    "Resolve timezone display mismatch",
    "Improve CSV export performance",
    "Add issue dependency indicators",
    "Create incident response template",
    "Improve form validation messages",
    "Add archived project visibility",
)

COMMENTS = (
    "I reproduced this in the current test environment and added the relevant context.",
    "The proposed approach looks reasonable. Please include regression coverage before merging.",
    "This is blocked by the related platform change; I will update the issue when it lands.",
    "The latest build fixes the primary path. I am checking edge cases now.",
    "Design review is complete and the acceptance criteria have been clarified.",
    "I added logs from the affected request and confirmed the failure point.",
    "This can be released independently and does not require a database migration.",
    "QA passed on desktop. Mobile verification is still in progress.",
)

LABEL_GROUPS = (
    "frontend,customer-impact",
    "backend,api",
    "security,authentication",
    "performance,observability",
    "mobile,ux",
    "reporting,data",
    "infrastructure,reliability",
    "accessibility,design-system",
)


def weighted_choice(randomizer, values):
    choices, weights = zip(*values)
    return randomizer.choices(choices, weights=weights, k=1)[0]


def main():
    if os.getenv("APP_ENV", "development").lower() == "production":
        raise RuntimeError("Demo data seeding is disabled in production.")
    demo_password = os.getenv("DEMO_SEED_PASSWORD") or secrets.token_urlsafe(18)
    randomizer = random.Random(SEED)
    now = datetime.now().replace(microsecond=0)
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM organizations WHERE name = %s", (ORGANIZATION,))
        organization = cursor.fetchone()
        if not organization:
            raise RuntimeError("Demo Organization is missing. Create the dummy users first.")
        organization_id = organization["id"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM bugs WHERE organization_id = %s AND title LIKE '[DEMO] %%'",
            (organization_id,),
        )
        if cursor.fetchone()["total"]:
            print("SKIPPED: Demo seed issues already exist; no duplicate data was added.")
            return

        password_hash = generate_password_hash(demo_password)
        for full_name, email, role in EXTRA_USERS:
            cursor.execute(
                """
                INSERT IGNORE INTO users
                    (organization_id, full_name, email, password_hash, role)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (organization_id, full_name, email, password_hash, role),
            )

        for project_key, name, description in PROJECTS:
            cursor.execute(
                """
                INSERT IGNORE INTO projects
                    (organization_id, name, project_key, description)
                VALUES (%s, %s, %s, %s)
                """,
                (organization_id, name, project_key, description),
            )

        cursor.execute(
            "SELECT id, full_name, email, role FROM users WHERE organization_id = %s ORDER BY id",
            (organization_id,),
        )
        users = cursor.fetchall()
        user_ids = [user["id"] for user in users]
        developers = [user["id"] for user in users if user["role"] == "developer"]
        reporters = [user["id"] for user in users if user["role"] in {"tester", "admin", "project_manager"}]

        cursor.execute(
            """
            SELECT id, name, project_key, next_issue_number
            FROM projects
            WHERE organization_id = %s
            ORDER BY id
            """,
            (organization_id,),
        )
        projects = cursor.fetchall()

        created_issue_ids = []
        for project in projects:
            next_number = project["next_issue_number"]
            parent_epics = []
            parent_candidates = []

            issue_types = ["Epic"] * 3 + ["Story"] * 8 + ["Task"] * 8 + ["Bug"] * 7 + ["Subtask"] * 4
            for position, issue_type in enumerate(issue_types):
                issue_number = next_number + position
                issue_key = f"{project['project_key']}-{issue_number}"
                title = f"[DEMO] {WORK_ITEMS[(position + project['id'] * 3) % len(WORK_ITEMS)]}"
                status = weighted_choice(
                    randomizer,
                    (("Open", 30), ("In Progress", 30), ("Resolved", 24), ("Closed", 16)),
                )
                priority = weighted_choice(
                    randomizer,
                    (("Low", 15), ("Medium", 42), ("High", 30), ("Urgent", 13)),
                )
                severity = weighted_choice(
                    randomizer,
                    (("Minor", 26), ("Major", 44), ("Critical", 23), ("Blocker", 7)),
                )
                assigned_to = randomizer.choice(developers) if randomizer.random() > 0.12 else None
                reporter_id = randomizer.choice(reporters)
                created_at = now - timedelta(days=randomizer.randint(1, 180), hours=randomizer.randint(0, 20))
                due_date = (created_at + timedelta(days=randomizer.randint(7, 75))).date()
                story_points = None if issue_type == "Bug" else randomizer.choice((1, 2, 3, 5, 8, 13))
                parent_id = None
                if issue_type in {"Story", "Task", "Bug"} and parent_epics and randomizer.random() > 0.25:
                    parent_id = randomizer.choice(parent_epics)
                elif issue_type == "Subtask" and parent_candidates:
                    parent_id = randomizer.choice(parent_candidates)

                cursor.execute(
                    """
                    INSERT INTO bugs
                        (organization_id, project_id, issue_key, issue_type, parent_id,
                         title, description, reproduction_steps, category, priority,
                         severity, status, reporter_id, assigned_to, labels,
                         story_points, due_date, created_at, updated_at)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        organization_id,
                        project["id"],
                        issue_key,
                        issue_type,
                        parent_id,
                        title,
                        f"Test data for {project['name']}. This issue exercises realistic planning, assignment, reporting, and workflow behavior.",
                        "1. Open the relevant project area.\n2. Follow the described workflow.\n3. Compare the actual result with the acceptance criteria.",
                        randomizer.choice(("General", "UI", "Backend", "Database", "Security", "Performance", "Integration")),
                        priority,
                        severity,
                        status,
                        reporter_id,
                        assigned_to,
                        randomizer.choice(LABEL_GROUPS),
                        story_points,
                        due_date,
                        created_at,
                        created_at + timedelta(days=randomizer.randint(0, 12)),
                    ),
                )
                issue_id = cursor.lastrowid
                created_issue_ids.append(issue_id)
                if issue_type == "Epic":
                    parent_epics.append(issue_id)
                elif issue_type != "Subtask":
                    parent_candidates.append(issue_id)

                cursor.execute(
                    """
                    INSERT INTO bug_history
                        (bug_id, changed_by, new_status, change_note, changed_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (issue_id, reporter_id, "Open", f"{issue_type} {issue_key} created", created_at),
                )
                if assigned_to:
                    cursor.execute(
                        """
                        INSERT INTO bug_history
                            (bug_id, changed_by, old_assigned_to, new_assigned_to,
                             change_note, changed_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            issue_id,
                            randomizer.choice(reporters),
                            None,
                            assigned_to,
                            "Issue assigned",
                            created_at + timedelta(hours=4),
                        ),
                    )
                if status != "Open":
                    cursor.execute(
                        """
                        INSERT INTO bug_history
                            (bug_id, changed_by, old_status, new_status,
                             change_note, changed_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            issue_id,
                            assigned_to or reporter_id,
                            "Open",
                            status,
                            "Workflow status updated",
                            created_at + timedelta(days=randomizer.randint(1, 10)),
                        ),
                    )

                for comment_number in range(randomizer.randint(1, 5)):
                    cursor.execute(
                        """
                        INSERT INTO comments (bug_id, user_id, comment, created_at)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            issue_id,
                            randomizer.choice(user_ids),
                            COMMENTS[(comment_number + issue_number) % len(COMMENTS)],
                            created_at + timedelta(days=comment_number + 1, hours=2),
                        ),
                    )

                for watcher_id in randomizer.sample(user_ids, k=randomizer.randint(1, min(4, len(user_ids)))):
                    cursor.execute(
                        "INSERT IGNORE INTO issue_watchers (bug_id, user_id) VALUES (%s, %s)",
                        (issue_id, watcher_id),
                    )

            cursor.execute(
                "UPDATE projects SET next_issue_number = %s WHERE id = %s",
                (next_number + len(issue_types), project["id"]),
            )

        connection.commit()

        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE organization_id = %s", (organization_id,))
        user_count = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM projects WHERE organization_id = %s", (organization_id,))
        project_count = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM bugs WHERE organization_id = %s", (organization_id,))
        issue_count = cursor.fetchone()["total"]
        cursor.execute(
            """
            SELECT COUNT(*) AS total FROM comments
            JOIN bugs ON comments.bug_id = bugs.id
            WHERE bugs.organization_id = %s
            """,
            (organization_id,),
        )
        comment_count = cursor.fetchone()["total"]
        cursor.execute(
            """
            SELECT COUNT(*) AS total FROM issue_watchers
            JOIN bugs ON issue_watchers.bug_id = bugs.id
            WHERE bugs.organization_id = %s
            """,
            (organization_id,),
        )
        watcher_count = cursor.fetchone()["total"]

        print("DEMO_SEED_OK")
        print(f"users={user_count}")
        print(f"projects={project_count}")
        print(f"issues={issue_count}")
        print(f"comments={comment_count}")
        print(f"watchers={watcher_count}")
        print(f"password_for_seed_users={demo_password}")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
