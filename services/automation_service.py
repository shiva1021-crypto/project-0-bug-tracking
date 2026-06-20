from mysql.connector import Error

from config import get_db_connection
from repositories.automation_repository import get_matching_rules
from utils.notifications import queue_email


def execute_automation_rules(organization_id, project_id, trigger_event, context):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    except Error:
        return

    try:
        rules = get_matching_rules(cursor, organization_id, project_id, trigger_event)
        for rule in rules:
            actions = rule["actions"] or []
            if not isinstance(actions, list):
                actions = [actions]

            conditions = rule["conditions"]
            if conditions and not _check_conditions(conditions, context):
                continue

            for action in actions:
                _execute_action(cursor, conn, action, context)
    finally:
        cursor.close()
        conn.close()


def _check_conditions(conditions, context):
    if not conditions:
        return True
    field = conditions.get("field")
    operator = conditions.get("operator")
    value = conditions.get("value")
    actual = context.get(field)
    if operator == "changed_to":
        return actual == value
    if operator == "not_changed_to":
        return actual != value
    if operator == "equals":
        return actual == value
    if operator == "not_equals":
        return actual != value
    return True


def _execute_action(cursor, conn, action, context):
    action_type = action.get("type")
    action_value = action.get("value")
    bug_id = context.get("bug_id")
    if not bug_id:
        return

    try:
        if action_type == "transition_status":
            cursor.execute(
                "UPDATE bugs SET status = %s WHERE id = %s",
                (action_value, bug_id),
            )
            cursor.execute(
                """
                INSERT INTO bug_history (bug_id, changed_by, old_status, new_status, change_note)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (bug_id, context.get("actor_id", 0),
                 context.get("old_status"), action_value,
                 f"Automation: status changed to {action_value}"),
            )
            conn.commit()

        elif action_type == "assign_to":
            cursor.execute(
                "UPDATE bugs SET assigned_to = %s WHERE id = %s",
                (int(action_value), bug_id),
            )
            conn.commit()

        elif action_type == "assign_to_role":
            cursor.execute(
                """
                SELECT id FROM users
                WHERE organization_id = %s AND role = %s
                ORDER BY RAND() LIMIT 1
                """,
                (context.get("organization_id"), action_value),
            )
            user = cursor.fetchone()
            if user:
                cursor.execute(
                    "UPDATE bugs SET assigned_to = %s WHERE id = %s",
                    (user[0], bug_id),
                )
                conn.commit()

        elif action_type == "add_comment":
            formatted = action_value.format(**context) if action_value else ""
            cursor.execute(
                "INSERT INTO comments (bug_id, user_id, comment) VALUES (%s, %s, %s)",
                (bug_id, context.get("actor_id", 0), formatted),
            )
            conn.commit()

        elif action_type == "notify":
            cursor.execute(
                """
                SELECT DISTINCT users.email, users.full_name
                FROM issue_watchers
                JOIN users ON issue_watchers.user_id = users.id
                WHERE issue_watchers.bug_id = %s
                """,
                (bug_id,),
            )
            for email, name in cursor.fetchall():
                queue_email(
                    email,
                    action_value.get("subject", "Automation notification"),
                    action_value.get("body", "").format(**context),
                )
    except Exception:
        conn.rollback()
