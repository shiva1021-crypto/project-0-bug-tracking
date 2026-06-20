from config import get_db_connection


def get_user_by_id(user_id, organization_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, full_name, email, role, created_at
        FROM users
        WHERE id = %s AND organization_id = %s
        """,
        (user_id, organization_id),
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_developers(organization_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, full_name
        FROM users
        WHERE role = 'developer' AND organization_id = %s
        ORDER BY full_name
        """,
        (organization_id,),
    )
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users
