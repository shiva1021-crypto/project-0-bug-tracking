def get_sprints(cursor, organization_id, project_id):
    cursor.execute(
        """
        SELECT * FROM sprints
        WHERE organization_id = %s AND project_id = %s
        ORDER BY FIELD(status, 'active', 'future', 'closed'),
                 COALESCE(start_date, created_at) DESC
        """,
        (organization_id, project_id),
    )
    return cursor.fetchall()





def get_active_sprint(cursor, organization_id, project_id):
    cursor.execute(
        """
        SELECT * FROM sprints
        WHERE organization_id = %s AND project_id = %s AND status = 'active'
        ORDER BY created_at DESC LIMIT 1
        """,
        (organization_id, project_id),
    )
    return cursor.fetchone()


def get_sprint(cursor, sprint_id, organization_id):
    cursor.execute(
        "SELECT * FROM sprints WHERE id = %s AND organization_id = %s",
        (sprint_id, organization_id),
    )
    return cursor.fetchone()


def create_sprint(cursor, organization_id, project_id, name, goal, start_date, end_date):
    cursor.execute(
        """
        INSERT INTO sprints (organization_id, project_id, name, goal, start_date, end_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (organization_id, project_id, name, goal, start_date, end_date),
    )
    return cursor.lastrowid


def update_sprint(cursor, sprint_id, organization_id, **fields):
    allowed = {"name", "goal", "start_date", "end_date", "status"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [sprint_id, organization_id]
    cursor.execute(
        f"UPDATE sprints SET {set_clause} WHERE id = %s AND organization_id = %s",
        values,
    )


def start_sprint(cursor, sprint_id, organization_id):
    cursor.execute(
        "UPDATE sprints SET status = 'active', start_date = COALESCE(start_date, CURDATE()) "
        "WHERE id = %s AND organization_id = %s AND status = 'future'",
        (sprint_id, organization_id),
    )


def close_sprint(cursor, sprint_id, organization_id):
    cursor.execute(
        "UPDATE sprints SET status = 'closed', end_date = COALESCE(end_date, CURDATE()) "
        "WHERE id = %s AND organization_id = %s AND status = 'active'",
        (sprint_id, organization_id),
    )


def get_backlog_issues(cursor, organization_id, project_id):
    cursor.execute(
        """
        SELECT bugs.id, bugs.issue_key, bugs.issue_type, bugs.title, bugs.status,
               bugs.priority, bugs.story_points, bugs.due_date, bugs.labels,
               bugs.assigned_to, users.full_name AS assignee_name,
               projects.name AS project_name, projects.project_key,
               bugs.sprint_id
        FROM bugs
        JOIN projects ON bugs.project_id = projects.id
        LEFT JOIN users ON bugs.assigned_to = users.id
        WHERE bugs.organization_id = %s
          AND bugs.project_id = %s
          AND (bugs.sprint_id IS NULL
               OR bugs.sprint_id IN (
                   SELECT id FROM sprints
                   WHERE organization_id = %s AND project_id = %s AND status = 'future'
               ))
        ORDER BY bugs.created_at DESC
        """,
        (organization_id, project_id, organization_id, project_id),
    )
    return cursor.fetchall()


def get_sprint_issues(cursor, sprint_id, organization_id):
    cursor.execute(
        """
        SELECT bugs.id, bugs.issue_key, bugs.issue_type, bugs.title, bugs.status,
               bugs.priority, bugs.story_points, bugs.due_date, bugs.labels,
               bugs.assigned_to, users.full_name AS assignee_name,
               projects.name AS project_name, projects.project_key
        FROM bugs
        JOIN projects ON bugs.project_id = projects.id
        LEFT JOIN users ON bugs.assigned_to = users.id
        WHERE bugs.sprint_id = %s AND bugs.organization_id = %s
        ORDER BY bugs.status, bugs.created_at DESC
        """,
        (sprint_id, organization_id),
    )
    return cursor.fetchall()


def set_issue_sprint(cursor, bug_id, sprint_id, organization_id):
    cursor.execute(
        "UPDATE bugs SET sprint_id = %s WHERE id = %s AND organization_id = %s",
        (sprint_id, bug_id, organization_id),
    )


def remove_issue_sprint(cursor, bug_id, organization_id):
    cursor.execute(
        "UPDATE bugs SET sprint_id = NULL WHERE id = %s AND organization_id = %s",
        (bug_id, organization_id),
    )


def get_sprint_burndown(cursor, sprint_id, organization_id):
    cursor.execute(
        """
        SELECT s.start_date, s.end_date,
               COALESCE(SUM(b.story_points), 0) AS total_points
        FROM sprints s
        LEFT JOIN bugs b ON b.sprint_id = s.id AND b.organization_id = s.organization_id
        WHERE s.id = %s AND s.organization_id = %s
        GROUP BY s.id
        """,
        (sprint_id, organization_id),
    )
    return cursor.fetchone()
