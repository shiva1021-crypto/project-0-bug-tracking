def get_developers(cursor, organization_id):
    cursor.execute(
        """
        SELECT id, full_name
        FROM users
        WHERE role = 'developer' AND organization_id = %s
        ORDER BY full_name
        """,
        (organization_id,),
    )
    return cursor.fetchall()


def get_projects(cursor, organization_id):
    cursor.execute(
        """
        SELECT id, name, project_key
        FROM projects
        WHERE organization_id = %s
        ORDER BY name
        """,
        (organization_id,),
    )
    return cursor.fetchall()


def _board_scope(organization_id, project_id):
    where = "WHERE bugs.organization_id = %s"
    params = [organization_id]
    if project_id is not None:
        where += " AND bugs.project_id = %s"
        params.append(project_id)
    return where, params


def count_board_issues(cursor, organization_id, project_id):
    where, params = _board_scope(organization_id, project_id)
    cursor.execute(f"SELECT COUNT(*) AS total FROM bugs {where}", params)
    return cursor.fetchone()["total"]


def get_board_issues(cursor, organization_id, project_id, limit, offset):
    where, params = _board_scope(organization_id, project_id)

    cursor.execute(
        f"""
        SELECT bugs.id, bugs.issue_key, bugs.issue_type, bugs.title, bugs.status,
               bugs.priority, bugs.story_points, bugs.due_date, bugs.labels,
               bugs.assigned_to, users.full_name AS assignee_name,
               projects.name AS project_name, projects.project_key
        FROM bugs
        JOIN projects ON bugs.project_id = projects.id
        LEFT JOIN users ON bugs.assigned_to = users.id
        {where}
        ORDER BY FIELD(bugs.priority, 'Urgent', 'High', 'Medium', 'Low'),
                 bugs.created_at DESC
        LIMIT %s OFFSET %s
        """,
        [*params, limit, offset],
    )
    return cursor.fetchall()
