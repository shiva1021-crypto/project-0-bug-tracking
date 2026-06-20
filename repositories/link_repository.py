LINK_TYPE_LABELS = {
    "blocks": {"outward": "blocks", "inward": "is blocked by"},
    "relates_to": {"outward": "relates to", "inward": "relates to"},
    "duplicates": {"outward": "duplicates", "inward": "is duplicated by"},
    "clones": {"outward": "clones", "inward": "is cloned from"},
}


def get_linked_issues(cursor, bug_id):
    """Returns two lists: outward_links, inward_links."""
    cursor.execute(
        """
        SELECT il.id AS link_id, il.link_type,
               b.id AS other_id, b.issue_key, b.title, b.status,
               p.project_key
        FROM issue_links il
        JOIN bugs b ON b.id = il.bug_id_b
        JOIN projects p ON b.project_id = p.id
        WHERE il.bug_id_a = %s
        ORDER BY il.created_at DESC
        """,
        (bug_id,),
    )
    outward = cursor.fetchall()
    for link in outward:
        link["direction"] = "outward"
        link["label"] = LINK_TYPE_LABELS.get(link["link_type"], {}).get("outward", link["link_type"])

    cursor.execute(
        """
        SELECT il.id AS link_id, il.link_type,
               b.id AS other_id, b.issue_key, b.title, b.status,
               p.project_key
        FROM issue_links il
        JOIN bugs b ON b.id = il.bug_id_a
        JOIN projects p ON b.project_id = p.id
        WHERE il.bug_id_b = %s
        ORDER BY il.created_at DESC
        """,
        (bug_id,),
    )
    inward = cursor.fetchall()
    for link in inward:
        link["direction"] = "inward"
        link["label"] = LINK_TYPE_LABELS.get(link["link_type"], {}).get("inward", link["link_type"])

    return outward, inward


def link_issues(cursor, bug_id_a, bug_id_b, link_type):
    cursor.execute(
        """
        INSERT IGNORE INTO issue_links (bug_id_a, bug_id_b, link_type)
        VALUES (%s, %s, %s)
        """,
        (bug_id_a, bug_id_b, link_type),
    )
    return cursor.rowcount > 0


def unlink_issues(cursor, link_id):
    cursor.execute("DELETE FROM issue_links WHERE id = %s", (link_id,))


def get_issue_key(cursor, bug_id, organization_id):
    cursor.execute(
        "SELECT issue_key FROM bugs WHERE id = %s AND organization_id = %s",
        (bug_id, organization_id),
    )
    row = cursor.fetchone()
    return row["issue_key"] if row else None
