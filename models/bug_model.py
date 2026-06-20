from config import get_db_connection


def get_bug_by_id(bug_id, organization_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM bugs WHERE id = %s AND organization_id = %s",
        (bug_id, organization_id),
    )
    bug = cursor.fetchone()
    cursor.close()
    conn.close()
    return bug
