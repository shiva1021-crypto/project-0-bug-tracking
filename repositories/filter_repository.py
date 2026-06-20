import json


def get_saved_filters(cursor, user_id, organization_id):
    cursor.execute(
        """
        SELECT id, name, filter_data, is_shared, created_at
        FROM saved_filters
        WHERE user_id = %s AND organization_id = %s
        ORDER BY created_at DESC
        """,
        (user_id, organization_id),
    )
    rows = cursor.fetchall()
    for row in rows:
        if isinstance(row.get("filter_data"), str):
            row["filter_data"] = json.loads(row["filter_data"])
    return rows


def save_filter(cursor, user_id, organization_id, name, filter_data, is_shared=False):
    cursor.execute(
        """
        INSERT INTO saved_filters (user_id, organization_id, name, filter_data, is_shared)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, organization_id, name, json.dumps(filter_data), is_shared),
    )
    return cursor.lastrowid


def get_filter(cursor, filter_id, user_id, organization_id):
    cursor.execute(
        """
        SELECT id, name, filter_data, is_shared
        FROM saved_filters
        WHERE id = %s AND user_id = %s AND organization_id = %s
        """,
        (filter_id, user_id, organization_id),
    )
    row = cursor.fetchone()
    if row and isinstance(row.get("filter_data"), str):
        row["filter_data"] = json.loads(row["filter_data"])
    return row


def delete_filter(cursor, filter_id, user_id, organization_id):
    cursor.execute(
        "DELETE FROM saved_filters WHERE id = %s AND user_id = %s AND organization_id = %s",
        (filter_id, user_id, organization_id),
    )
