def get_versions(cursor, organization_id, project_id):
    cursor.execute(
        """
        SELECT v.*,
               COUNT(b.id) AS issue_count,
               SUM(CASE WHEN b.status IN ('Testing', 'Done') THEN 1 ELSE 0 END) AS resolved_count
        FROM versions v
        LEFT JOIN bugs b ON b.fix_version_id = v.id AND b.organization_id = v.organization_id
        WHERE v.organization_id = %s AND v.project_id = %s
        GROUP BY v.id
        ORDER BY FIELD(v.status, 'unreleased', 'released', 'archived'),
                 COALESCE(v.release_date, v.created_at) DESC
        """,
        (organization_id, project_id),
    )
    return cursor.fetchall()


def create_version(cursor, organization_id, project_id, name, description, release_date):
    cursor.execute(
        """
        INSERT INTO versions (organization_id, project_id, name, description, release_date)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (organization_id, project_id, name, description, release_date),
    )
    return cursor.lastrowid


def update_version_status(cursor, version_id, organization_id, status):
    cursor.execute(
        "UPDATE versions SET status = %s WHERE id = %s AND organization_id = %s",
        (status, version_id, organization_id),
    )


def get_version_issues(cursor, version_id, organization_id):
    cursor.execute(
        """
        SELECT bugs.id, bugs.issue_key, bugs.issue_type, bugs.title, bugs.status,
               bugs.priority, bugs.story_points, bugs.assigned_to,
               users.full_name AS assignee_name
        FROM bugs
        LEFT JOIN users ON bugs.assigned_to = users.id
        WHERE bugs.fix_version_id = %s AND bugs.organization_id = %s
        ORDER BY bugs.status, bugs.created_at DESC
        """,
        (version_id, organization_id),
    )
    return cursor.fetchall()


def get_versions_for_project(cursor, organization_id, project_id):
    cursor.execute(
        """
        SELECT id, name, status
        FROM versions
        WHERE organization_id = %s AND project_id = %s AND status != 'archived'
        ORDER BY FIELD(status, 'unreleased', 'released'), COALESCE(release_date, created_at) DESC
        """,
        (organization_id, project_id),
    )
    return cursor.fetchall()
