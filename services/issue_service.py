from datetime import date


PRIORITIES = ("Low", "Medium", "High", "Urgent")
SEVERITIES = ("Minor", "Major", "Critical", "Blocker")
STATUSES = ("Idea", "To Do", "In Progress", "Testing", "Done")
ISSUE_TYPES = ("Epic", "Story", "Task", "Bug", "Subtask")
STANDARD_TYPES = {"Story", "Task", "Bug"}
DEFAULT_CATEGORIES = (
    "General",
    "UI",
    "Backend",
    "Database",
    "Security",
    "Performance",
    "Integration",
)


class HierarchyError(ValueError):
    pass


def normalized_labels(raw_labels):
    labels = []
    for value in raw_labels.split(","):
        label = value.strip().lower().replace(" ", "-")
        if label and label not in labels:
            labels.append(label[:30])
    return ",".join(labels[:10]) or None


def parsed_story_points(raw_value):
    if not raw_value:
        return None
    if not raw_value.isdigit() or not 1 <= int(raw_value) <= 100:
        raise ValueError("Story points must be between 1 and 100.")
    return int(raw_value)


def parsed_due_date(raw_value):
    if not raw_value:
        return None
    return date.fromisoformat(raw_value)


def resolve_parent(cursor, issue_type, parent_id, project_id, organization_id, issue_id=None):
    if not parent_id:
        if issue_type == "Subtask":
            raise HierarchyError("A subtask must have a Story, Task, or Bug parent.")
        return None
    if issue_type == "Epic":
        raise HierarchyError("An Epic cannot have a parent.")

    cursor.execute(
        """
        SELECT id, issue_type, parent_id
        FROM bugs
        WHERE id = %s AND project_id = %s AND organization_id = %s
        """,
        (parent_id, project_id, organization_id),
    )
    parent = cursor.fetchone()
    if not parent:
        raise HierarchyError("Select a parent from the same project.")

    allowed_parent_types = {"Epic"} if issue_type in STANDARD_TYPES else STANDARD_TYPES
    if parent["issue_type"] not in allowed_parent_types:
        expected = "Epic" if issue_type in STANDARD_TYPES else "Story, Task, or Bug"
        raise HierarchyError(f"A {issue_type} parent must be an {expected}.")

    ancestor = parent
    visited = set()
    while ancestor:
        if ancestor["id"] == issue_id or ancestor["id"] in visited:
            raise HierarchyError("This parent would create a circular issue hierarchy.")
        visited.add(ancestor["id"])
        if not ancestor["parent_id"]:
            break
        cursor.execute(
            """
            SELECT id, issue_type, parent_id
            FROM bugs
            WHERE id = %s AND project_id = %s AND organization_id = %s
            """,
            (ancestor["parent_id"], project_id, organization_id),
        )
        ancestor = cursor.fetchone()
    return parent["id"]


def validate_children(cursor, issue_id, issue_type, organization_id):
    cursor.execute(
        "SELECT issue_type FROM bugs WHERE parent_id = %s AND organization_id = %s",
        (issue_id, organization_id),
    )
    child_types = {row["issue_type"] for row in cursor.fetchall()}
    allowed = STANDARD_TYPES if issue_type == "Epic" else ({"Subtask"} if issue_type in STANDARD_TYPES else set())
    if not child_types.issubset(allowed):
        raise HierarchyError("Existing child issues are incompatible with the selected work type.")
