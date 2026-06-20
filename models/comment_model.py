from config import get_db_connection


def get_comments_for_bug(bug_id, organization_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT comments.*, users.full_name
        FROM comments
        JOIN users ON comments.user_id = users.id
        JOIN bugs ON comments.bug_id = bugs.id
        WHERE comments.bug_id = %s AND bugs.organization_id = %s
        ORDER BY comments.created_at DESC
        """,
        (bug_id, organization_id),
    )
    comments = cursor.fetchall()
    cursor.close()
    conn.close()
    return comments
