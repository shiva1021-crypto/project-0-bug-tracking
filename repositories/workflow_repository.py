def get_assignment(cursor, issue_id, organization_id):
    cursor.execute(
        "SELECT assigned_to, status, issue_key FROM bugs WHERE id = %s AND organization_id = %s",
        (issue_id, organization_id),
    )
    return cursor.fetchone()


def get_developer(cursor, user_id, organization_id):
    cursor.execute(
        """
        SELECT id, email, full_name
        FROM users
        WHERE id = %s AND role = 'developer' AND organization_id = %s
        """,
        (user_id, organization_id),
    )
    return cursor.fetchone()


def save_assignment(cursor, issue_id, organization_id, actor_id, old_assignment, old_status,
                    new_assignment, new_status):
    cursor.execute(
        "UPDATE bugs SET assigned_to = %s, status = %s WHERE id = %s AND organization_id = %s",
        (new_assignment, new_status, issue_id, organization_id),
    )
    cursor.execute(
        """
        INSERT INTO bug_history
        (bug_id, changed_by, old_status, new_status, old_assigned_to, new_assigned_to, change_note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (issue_id, actor_id, old_status, new_status, old_assignment, new_assignment,
         "Issue assignment updated"),
    )


def get_status_context(cursor, issue_id, organization_id):
    cursor.execute(
        "SELECT status, assigned_to FROM bugs WHERE id = %s AND organization_id = %s",
        (issue_id, organization_id),
    )
    return cursor.fetchone()


def save_status(cursor, issue_id, organization_id, actor_id, old_status, new_status):
    cursor.execute(
        "UPDATE bugs SET status = %s WHERE id = %s AND organization_id = %s",
        (new_status, issue_id, organization_id),
    )
    cursor.execute(
        """
        INSERT INTO bug_history (bug_id, changed_by, old_status, new_status, change_note)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (issue_id, actor_id, old_status, new_status, "Issue status updated"),
    )


def get_reporter(cursor, issue_id, organization_id):
    cursor.execute(
        """
        SELECT reporter.id AS reporter_id, reporter.email, reporter.full_name, bugs.issue_key
        FROM bugs
        JOIN users AS reporter ON bugs.reporter_id = reporter.id
        WHERE bugs.id = %s AND bugs.organization_id = %s
        """,
        (issue_id, organization_id),
    )
    return cursor.fetchone()


def get_watchers(cursor, issue_id, organization_id, excluded_user_ids):
    placeholders = ", ".join(["%s"] * len(excluded_user_ids))
    cursor.execute(
        f"""
        SELECT DISTINCT users.id, users.email, users.full_name
        FROM issue_watchers
        JOIN users ON issue_watchers.user_id = users.id
        WHERE issue_watchers.bug_id = %s AND users.organization_id = %s
          AND users.id NOT IN ({placeholders})
        """,
        (issue_id, organization_id, *excluded_user_ids),
    )
    return cursor.fetchall()


def issue_exists(cursor, issue_id, organization_id):
    cursor.execute(
        "SELECT id FROM bugs WHERE id = %s AND organization_id = %s",
        (issue_id, organization_id),
    )
    return cursor.fetchone() is not None


def add_comment(cursor, issue_id, user_id, comment):
    cursor.execute(
        "INSERT INTO comments (bug_id, user_id, comment) VALUES (%s, %s, %s)",
        (issue_id, user_id, comment),
    )


def set_watching(cursor, issue_id, user_id, watching):
    if watching:
        cursor.execute(
            "INSERT IGNORE INTO issue_watchers (bug_id, user_id) VALUES (%s, %s)",
            (issue_id, user_id),
        )
    else:
        cursor.execute(
            "DELETE FROM issue_watchers WHERE bug_id = %s AND user_id = %s",
            (issue_id, user_id),
        )
