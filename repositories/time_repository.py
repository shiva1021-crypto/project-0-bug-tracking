def log_time(cursor, bug_id, user_id, hours_spent, description):
    cursor.execute(
        """
        INSERT INTO time_entries (bug_id, user_id, hours_spent, description)
        VALUES (%s, %s, %s, %s)
        """,
        (bug_id, user_id, hours_spent, description),
    )


def get_time_entries(cursor, bug_id):
    cursor.execute(
        """
        SELECT te.*, u.full_name AS user_name
        FROM time_entries te
        JOIN users u ON te.user_id = u.id
        WHERE te.bug_id = %s
        ORDER BY te.logged_at DESC
        """,
        (bug_id,),
    )
    return cursor.fetchall()


def get_total_time_spent(cursor, bug_id):
    cursor.execute(
        "SELECT COALESCE(SUM(hours_spent), 0) AS total FROM time_entries WHERE bug_id = %s",
        (bug_id,),
    )
    row = cursor.fetchone()
    return float(row['total']) if row else 0.0


def update_time_estimate(cursor, bug_id, hours):
    cursor.execute(
        "UPDATE bugs SET time_estimate = %s WHERE id = %s",
        (hours, bug_id),
    )


def update_time_remaining(cursor, bug_id, hours):
    cursor.execute(
        "UPDATE bugs SET time_remaining = %s WHERE id = %s",
        (hours, bug_id),
    )
