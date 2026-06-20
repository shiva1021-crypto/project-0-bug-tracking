import json


def get_widgets(cursor, organization_id, user_id=None):
    cursor.execute(
        """
        SELECT * FROM dashboard_widgets
        WHERE organization_id = %s AND (user_id = %s OR user_id IS NULL)
        ORDER BY position, id
        """,
        (organization_id, user_id or 0),
    )
    rows = cursor.fetchall()
    for row in rows:
        if row.get("config") and isinstance(row["config"], str):
            try:
                row["config"] = json.loads(row["config"])
            except (json.JSONDecodeError, TypeError):
                row["config"] = {}
        elif row.get("config") is None:
            row["config"] = {}
    return rows


def add_widget(cursor, organization_id, user_id, widget_type, title, config=None, width="full"):
    cursor.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM dashboard_widgets WHERE organization_id = %s",
        (organization_id,),
    )
    row = cursor.fetchone()
    next_pos = row["next_pos"] if isinstance(row, dict) else row[0]
    cursor.execute(
        """
        INSERT INTO dashboard_widgets
            (organization_id, user_id, widget_type, title, config, position, width)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (organization_id, user_id, widget_type, title, json.dumps(config) if config else None,
         next_pos, width),
    )


def remove_widget(cursor, widget_id, organization_id):
    cursor.execute(
        "DELETE FROM dashboard_widgets WHERE id = %s AND organization_id = %s",
        (widget_id, organization_id),
    )


def update_widget_position(cursor, widget_id, organization_id, position):
    cursor.execute(
        "UPDATE dashboard_widgets SET position = %s WHERE id = %s AND organization_id = %s",
        (position, widget_id, organization_id),
    )
