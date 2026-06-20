import json


def get_rules(cursor, organization_id, project_id=None):
    if project_id:
        cursor.execute(
            """
            SELECT * FROM automation_rules
            WHERE organization_id = %s AND (project_id = %s OR project_id IS NULL)
            ORDER BY created_at DESC
            """,
            (organization_id, project_id),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM automation_rules
            WHERE organization_id = %s
            ORDER BY created_at DESC
            """,
            (organization_id,),
        )
    rows = cursor.fetchall()
    for row in rows:
        if row.get("actions") and isinstance(row["actions"], str):
            row["actions"] = json.loads(row["actions"])
        if row.get("conditions") and isinstance(row["conditions"], str):
            row["conditions"] = json.loads(row["conditions"])
        row["enabled"] = bool(row["enabled"])
    return rows


def get_matching_rules(cursor, organization_id, project_id, trigger_event):
    cursor.execute(
        """
        SELECT * FROM automation_rules
        WHERE organization_id = %s
          AND (project_id = %s OR project_id IS NULL)
          AND trigger_event = %s
          AND enabled = 1
        ORDER BY id
        """,
        (organization_id, project_id, trigger_event),
    )
    rows = cursor.fetchall()
    for row in rows:
        if row.get("actions") and isinstance(row["actions"], str):
            row["actions"] = json.loads(row["actions"])
        if row.get("conditions") and isinstance(row["conditions"], str):
            row["conditions"] = json.loads(row["conditions"])
    return rows


def create_rule(cursor, organization_id, project_id, name, trigger_event, conditions, actions):
    cursor.execute(
        """
        INSERT INTO automation_rules
            (organization_id, project_id, name, trigger_event, conditions, actions)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            organization_id,
            project_id,
            name,
            trigger_event,
            json.dumps(conditions) if conditions else None,
            json.dumps(actions),
        ),
    )


def delete_rule(cursor, rule_id, organization_id):
    cursor.execute(
        "DELETE FROM automation_rules WHERE id = %s AND organization_id = %s",
        (rule_id, organization_id),
    )


def toggle_rule(cursor, rule_id, organization_id):
    cursor.execute(
        "UPDATE automation_rules SET enabled = NOT enabled WHERE id = %s AND organization_id = %s",
        (rule_id, organization_id),
    )
