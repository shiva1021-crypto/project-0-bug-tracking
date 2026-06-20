import json


def get_field_definitions(cursor, organization_id, project_id):
    cursor.execute(
        """
        SELECT * FROM custom_field_definitions
        WHERE organization_id = %s AND project_id = %s
        ORDER BY display_order, id
        """,
        (organization_id, project_id),
    )
    rows = cursor.fetchall()
    for row in rows:
        if row.get("options") and isinstance(row["options"], str):
            try:
                row["options"] = json.loads(row["options"])
            except (json.JSONDecodeError, TypeError):
                row["options"] = []
        elif row.get("options") is None:
            row["options"] = []
        row["required"] = bool(row["required"])
    return rows


def get_field_values(cursor, bug_id):
    cursor.execute(
        """
        SELECT cfv.field_id, cfv.value
        FROM custom_field_values cfv
        WHERE cfv.bug_id = %s
        """,
        (bug_id,),
    )
    result = {}
    for row in cursor.fetchall():
        result[row["field_id"]] = row["value"]
    return result


def save_field_value(cursor, bug_id, field_id, value):
    cursor.execute(
        """
        INSERT INTO custom_field_values (bug_id, field_id, value)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE value = %s
        """,
        (bug_id, field_id, value, value),
    )


def create_field_definition(cursor, organization_id, project_id, name, field_type, options=None, required=False):
    cursor.execute(
        """
        INSERT INTO custom_field_definitions
            (organization_id, project_id, name, field_type, options, required)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (organization_id, project_id, name, field_type, json.dumps(options) if options else None, int(required)),
    )


def delete_field_definition(cursor, field_id, organization_id):
    cursor.execute(
        "DELETE FROM custom_field_definitions WHERE id = %s AND organization_id = %s",
        (field_id, organization_id),
    )
