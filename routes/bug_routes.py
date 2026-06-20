import os
from datetime import date
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from config import db_cursor, get_db_connection
from utils.decorators import can_update_bug_status, login_required, role_required
from utils.notifications import send_email
from utils.pagination import pagination_values


bug_bp = Blueprint("bug", __name__)

PRIORITIES = ("Low", "Medium", "High", "Urgent")
SEVERITIES = ("Minor", "Major", "Critical", "Blocker")
STATUSES = ("Open", "In Progress", "Resolved", "Closed")
ISSUE_TYPES = ("Epic", "Story", "Task", "Bug", "Subtask")
DEFAULT_CATEGORIES = ("General", "UI", "Backend", "Database", "Security", "Performance", "Integration")


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


def detected_image_extension(file):
    header = file.stream.read(12)
    file.stream.seek(0)

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def save_screenshot(file):
    if not file or file.filename == "":
        return None

    if not allowed_file(file.filename):
        flash("Screenshot must be an image file: png, jpg, jpeg, gif or webp.", "error")
        return None

    original_name = secure_filename(file.filename)
    extension = original_name.rsplit(".", 1)[1].lower()
    detected_extension = detected_image_extension(file)
    normalized_extension = "jpg" if extension == "jpeg" else extension
    if detected_extension != normalized_extension:
        flash("Screenshot content does not match a supported image format.", "error")
        return None

    filename = f"{uuid4().hex}.{extension}"
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    return filename


def get_developers(cursor):
    cursor.execute(
        """
        SELECT id, full_name
        FROM users
        WHERE role = 'developer' AND organization_id = %s
        ORDER BY full_name
        """,
        (session["organization_id"],),
    )
    return cursor.fetchall()


def get_projects(cursor):
    cursor.execute(
        """
        SELECT id, name, project_key
        FROM projects
        WHERE organization_id = %s
        ORDER BY name
        """,
        (session["organization_id"],),
    )
    return cursor.fetchall()


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


@bug_bp.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            COUNT(*) AS total_bugs,
            SUM(status = 'Open') AS open_bugs,
            SUM(status = 'In Progress') AS in_progress_bugs,
            SUM(status = 'Resolved') AS resolved_bugs,
            SUM(status = 'Closed') AS closed_bugs,
            SUM(severity IN ('Critical', 'Blocker')) AS critical_bugs
        FROM bugs
        WHERE organization_id = %s
        """,
        (session["organization_id"],),
    )
    stats = cursor.fetchone()

    cursor.execute(
        """
        SELECT bugs.id, bugs.issue_key, bugs.issue_type, bugs.title, bugs.priority, bugs.severity, bugs.status,
               bugs.created_at, reporter.full_name AS reporter_name,
               developer.full_name AS developer_name
        FROM bugs
        JOIN users AS reporter ON bugs.reporter_id = reporter.id
        LEFT JOIN users AS developer ON bugs.assigned_to = developer.id
        WHERE bugs.organization_id = %s
        ORDER BY bugs.created_at DESC
        LIMIT 6
        """,
        (session["organization_id"],),
    )
    recent_bugs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("dashboard.html", stats=stats, recent_bugs=recent_bugs)


@bug_bp.route("/bugs/add", methods=["GET", "POST"])
@role_required("tester", "developer", "admin", "project_manager")
def add_bug():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        reproduction_steps = request.form.get("reproduction_steps", "").strip()
        category = request.form.get("category", "General").strip() or "General"
        external_issue_url = request.form.get("external_issue_url", "").strip()
        priority = request.form.get("priority", "")
        severity = request.form.get("severity", "")
        project_id = request.form.get("project_id", "")
        issue_type = request.form.get("issue_type", "Bug")
        parent_id = request.form.get("parent_id", "")
        labels = normalized_labels(request.form.get("labels", ""))

        try:
            story_points = parsed_story_points(request.form.get("story_points", ""))
            due_date = parsed_due_date(request.form.get("due_date", ""))
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("bug.add_bug"))

        if (
            not title
            or not description
            or priority not in PRIORITIES
            or severity not in SEVERITIES
            or issue_type not in ISSUE_TYPES
            or not project_id.isdigit()
        ):
            flash("Please fill all required bug fields with valid values.", "error")
            return redirect(url_for("bug.add_bug"))

        screenshot_filename = save_screenshot(request.files.get("screenshot"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, project_key, next_issue_number
            FROM projects
            WHERE id = %s AND organization_id = %s
            FOR UPDATE
            """,
            (int(project_id), session["organization_id"]),
        )
        project = cursor.fetchone()
        if not project:
            cursor.close()
            conn.close()
            flash("Select a valid project.", "error")
            return redirect(url_for("bug.add_bug"))

        valid_parent_id = None
        if parent_id.isdigit():
            cursor.execute(
                """
                SELECT id FROM bugs
                WHERE id = %s AND project_id = %s AND organization_id = %s
                """,
                (int(parent_id), project["id"], session["organization_id"]),
            )
            parent = cursor.fetchone()
            valid_parent_id = parent["id"] if parent else None

        issue_number = project["next_issue_number"]
        issue_key = f"{project['project_key']}-{issue_number}"
        cursor.execute(
            "UPDATE projects SET next_issue_number = next_issue_number + 1 WHERE id = %s",
            (project["id"],),
        )
        cursor.execute(
            """
            INSERT INTO bugs
            (organization_id, project_id, issue_key, issue_type, parent_id,
             title, description, reproduction_steps, category, priority, severity,
             reporter_id, screenshot_path, external_issue_url, labels, story_points, due_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["organization_id"],
                project["id"],
                issue_key,
                issue_type,
                valid_parent_id,
                title,
                description,
                reproduction_steps,
                category,
                priority,
                severity,
                session["user_id"],
                screenshot_filename,
                external_issue_url or None,
                labels,
                story_points,
                due_date,
            ),
        )
        bug_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO bug_history (bug_id, changed_by, new_status, change_note)
            VALUES (%s, %s, %s, %s)
            """,
            (bug_id, session["user_id"], "Open", f"{issue_type} {issue_key} created"),
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash(f"Issue {issue_key} created successfully.", "success")
        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    projects = get_projects(cursor)
    cursor.execute(
        """
        SELECT id, issue_key, issue_type, title, project_id
        FROM bugs
        WHERE organization_id = %s AND issue_type IN ('Epic', 'Story', 'Task', 'Bug')
        ORDER BY created_at DESC
        """,
        (session["organization_id"],),
    )
    parents = cursor.fetchall()
    cursor.close()
    conn.close()
    if not projects:
        flash("Create a project before adding issues.", "error")
        return redirect(url_for("project.projects"))
    return render_template(
        "add_bug.html",
        priorities=PRIORITIES,
        severities=SEVERITIES,
        categories=DEFAULT_CATEGORIES,
        issue_types=ISSUE_TYPES,
        projects=projects,
        parents=parents,
    )


@bug_bp.route("/bugs")
@login_required
def view_bugs():
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    severity = request.args.get("severity", "")
    assigned_to = request.args.get("assigned_to", "")
    project_id = request.args.get("project", "")
    issue_type = request.args.get("issue_type", "")
    search = request.args.get("q", "").strip()

    select_query = """
        SELECT bugs.id, bugs.issue_key, bugs.issue_type, bugs.title, bugs.description,
               bugs.category, bugs.priority, bugs.severity, bugs.status, bugs.created_at,
               bugs.story_points, bugs.due_date, reporter.full_name AS reporter_name,
               developer.full_name AS developer_name, projects.name AS project_name
        FROM bugs
        JOIN projects ON bugs.project_id = projects.id
        JOIN users AS reporter ON bugs.reporter_id = reporter.id
        LEFT JOIN users AS developer ON bugs.assigned_to = developer.id
        WHERE bugs.organization_id = %s
    """
    params = [session["organization_id"]]

    if status in STATUSES:
        select_query += " AND bugs.status = %s"
        params.append(status)
    if priority in PRIORITIES:
        select_query += " AND bugs.priority = %s"
        params.append(priority)
    if severity in SEVERITIES:
        select_query += " AND bugs.severity = %s"
        params.append(severity)
    if assigned_to.isdigit():
        select_query += " AND bugs.assigned_to = %s"
        params.append(int(assigned_to))
    if project_id.isdigit():
        select_query += " AND bugs.project_id = %s"
        params.append(int(project_id))
    if issue_type in ISSUE_TYPES:
        select_query += " AND bugs.issue_type = %s"
        params.append(issue_type)
    if search:
        select_query += " AND (bugs.issue_key LIKE %s OR bugs.title LIKE %s OR bugs.description LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    count_query = f"SELECT COUNT(*) AS total FROM ({select_query}) AS filtered_bugs"
    cursor.execute(count_query, params)
    total_items = cursor.fetchone()["total"]
    pagination = pagination_values(
        request.args.get("page", 1), total_items, current_app.config["PAGE_SIZE"]
    )
    offset = (pagination["page"] - 1) * pagination["page_size"]

    query = select_query + " ORDER BY bugs.created_at DESC LIMIT %s OFFSET %s"
    cursor.execute(query, [*params, pagination["page_size"], offset])
    bugs = cursor.fetchall()
    developers = get_developers(cursor)
    projects = get_projects(cursor)
    cursor.close()
    conn.close()

    return render_template(
        "view_bugs.html",
        bugs=bugs,
        developers=developers,
        statuses=STATUSES,
        priorities=PRIORITIES,
        severities=SEVERITIES,
        issue_types=ISSUE_TYPES,
        projects=projects,
        filters=request.args,
        pagination=pagination,
        page_args={key: value for key, value in request.args.items() if key != "page"},
    )


@bug_bp.route("/bugs/<int:bug_id>")
@login_required
def bug_details(bug_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT bugs.*, reporter.full_name AS reporter_name,
               developer.full_name AS developer_name,
               projects.name AS project_name, projects.project_key,
               parent.issue_key AS parent_issue_key, parent.title AS parent_title
        FROM bugs
        JOIN projects ON bugs.project_id = projects.id
        JOIN users AS reporter ON bugs.reporter_id = reporter.id
        LEFT JOIN users AS developer ON bugs.assigned_to = developer.id
        LEFT JOIN bugs AS parent ON bugs.parent_id = parent.id
        WHERE bugs.id = %s AND bugs.organization_id = %s
        """,
        (bug_id, session["organization_id"]),
    )
    bug = cursor.fetchone()
    if not bug:
        cursor.close()
        conn.close()
        abort(404)
    bug["label_list"] = [label.strip() for label in (bug["labels"] or "").split(",") if label.strip()]

    cursor.execute(
        """
        SELECT id, issue_key, issue_type, title, status
        FROM bugs
        WHERE parent_id = %s AND organization_id = %s
        ORDER BY created_at
        """,
        (bug_id, session["organization_id"]),
    )
    children = cursor.fetchall()

    cursor.execute(
        """
        SELECT COUNT(*) AS watcher_count,
               COALESCE(SUM(user_id = %s), 0) AS is_watching
        FROM issue_watchers
        WHERE bug_id = %s
        """,
        (session["user_id"], bug_id),
    )
    watcher_info = cursor.fetchone()

    cursor.execute(
        """
        SELECT comments.*, users.full_name
        FROM comments
        JOIN users ON comments.user_id = users.id
        JOIN bugs ON comments.bug_id = bugs.id
        WHERE comments.bug_id = %s AND bugs.organization_id = %s
        ORDER BY comments.created_at DESC
        """,
        (bug_id, session["organization_id"]),
    )
    comments = cursor.fetchall()

    cursor.execute(
        """
        SELECT bug_history.*, users.full_name AS changed_by_name,
               old_dev.full_name AS old_developer_name,
               new_dev.full_name AS new_developer_name
        FROM bug_history
        JOIN bugs ON bug_history.bug_id = bugs.id
        JOIN users ON bug_history.changed_by = users.id
        LEFT JOIN users AS old_dev ON bug_history.old_assigned_to = old_dev.id
        LEFT JOIN users AS new_dev ON bug_history.new_assigned_to = new_dev.id
        WHERE bug_history.bug_id = %s AND bugs.organization_id = %s
        ORDER BY bug_history.changed_at DESC
        """,
        (bug_id, session["organization_id"]),
    )
    history = cursor.fetchall()
    developers = get_developers(cursor)

    cursor.close()
    conn.close()

    return render_template(
        "bug_details.html",
        bug=bug,
        comments=comments,
        history=history,
        children=children,
        watcher_info=watcher_info,
        developers=developers,
        statuses=STATUSES,
        can_update_status=can_update_bug_status(bug, session["user_id"], session.get("role")),
    )


@bug_bp.route("/bugs/<int:bug_id>/edit", methods=["GET", "POST"])
@login_required
def edit_bug(bug_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM bugs WHERE id = %s AND organization_id = %s",
        (bug_id, session["organization_id"]),
    )
    bug = cursor.fetchone()

    if not bug:
        cursor.close()
        conn.close()
        abort(404)

    can_edit = session.get("role") in ("admin", "project_manager") or bug["reporter_id"] == session["user_id"]
    if not can_edit:
        cursor.close()
        conn.close()
        flash("You do not have permission to edit this bug.", "error")
        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        reproduction_steps = request.form.get("reproduction_steps", "").strip()
        category = request.form.get("category", "General").strip() or "General"
        external_issue_url = request.form.get("external_issue_url", "").strip()
        priority = request.form.get("priority", "")
        severity = request.form.get("severity", "")
        issue_type = request.form.get("issue_type", "Bug")
        parent_id = request.form.get("parent_id", "")
        labels = normalized_labels(request.form.get("labels", ""))

        try:
            story_points = parsed_story_points(request.form.get("story_points", ""))
            due_date = parsed_due_date(request.form.get("due_date", ""))
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("bug.edit_bug", bug_id=bug_id))

        if (
            not title
            or not description
            or priority not in PRIORITIES
            or severity not in SEVERITIES
            or issue_type not in ISSUE_TYPES
        ):
            flash("Please provide valid bug details.", "error")
            return redirect(url_for("bug.edit_bug", bug_id=bug_id))

        screenshot_filename = bug["screenshot_path"]
        uploaded = save_screenshot(request.files.get("screenshot"))
        if uploaded:
            screenshot_filename = uploaded

        valid_parent_id = None
        if parent_id.isdigit() and int(parent_id) != bug_id:
            cursor.execute(
                """
                SELECT id FROM bugs
                WHERE id = %s AND project_id = %s AND organization_id = %s
                """,
                (int(parent_id), bug["project_id"], session["organization_id"]),
            )
            parent = cursor.fetchone()
            valid_parent_id = parent["id"] if parent else None

        cursor.execute(
            """
            UPDATE bugs
            SET title = %s, description = %s, reproduction_steps = %s,
                category = %s, priority = %s, severity = %s,
                screenshot_path = %s, external_issue_url = %s,
                issue_type = %s, parent_id = %s, labels = %s,
                story_points = %s, due_date = %s
            WHERE id = %s AND organization_id = %s
            """,
            (
                title,
                description,
                reproduction_steps,
                category,
                priority,
                severity,
                screenshot_filename,
                external_issue_url or None,
                issue_type,
                valid_parent_id,
                labels,
                story_points,
                due_date,
                bug_id,
                session["organization_id"],
            ),
        )
        cursor.execute(
            """
            INSERT INTO bug_history (bug_id, changed_by, change_note)
            VALUES (%s, %s, %s)
            """,
            (bug_id, session["user_id"], "Bug details edited"),
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Bug updated successfully.", "success")
        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    cursor.execute(
        """
        SELECT id, issue_key, issue_type, title
        FROM bugs
        WHERE organization_id = %s AND project_id = %s AND id != %s
          AND issue_type IN ('Epic', 'Story', 'Task', 'Bug')
        ORDER BY created_at DESC
        """,
        (session["organization_id"], bug["project_id"], bug_id),
    )
    parents = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template(
        "edit_bug.html",
        bug=bug,
        priorities=PRIORITIES,
        severities=SEVERITIES,
        categories=DEFAULT_CATEGORIES,
        issue_types=ISSUE_TYPES,
        parents=parents,
    )


@bug_bp.route("/bugs/<int:bug_id>/assign", methods=["POST"])
@role_required("admin", "project_manager")
def assign_bug(bug_id):
    developer_id = request.form.get("developer_id", "")
    new_assigned_to = int(developer_id) if developer_id.isdigit() else None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT assigned_to, status FROM bugs WHERE id = %s AND organization_id = %s",
        (bug_id, session["organization_id"]),
    )
    bug = cursor.fetchone()
    if not bug:
        cursor.close()
        conn.close()
        abort(404)

    old_assigned_to, old_status = bug
    new_status = "In Progress" if new_assigned_to and old_status == "Open" else old_status

    if new_assigned_to:
        cursor.execute(
            """
            SELECT id, email, full_name
            FROM users
            WHERE id = %s AND role = 'developer' AND organization_id = %s
            """,
            (new_assigned_to, session["organization_id"]),
        )
        developer = cursor.fetchone()
        if not developer:
            cursor.close()
            conn.close()
            flash("Please select a developer from your organization.", "error")
            return redirect(url_for("bug.bug_details", bug_id=bug_id))
    else:
        developer = None

    cursor.execute(
        "UPDATE bugs SET assigned_to = %s, status = %s WHERE id = %s AND organization_id = %s",
        (new_assigned_to, new_status, bug_id, session["organization_id"]),
    )
    cursor.execute(
        """
        INSERT INTO bug_history
        (bug_id, changed_by, old_status, new_status, old_assigned_to, new_assigned_to, change_note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            bug_id,
            session["user_id"],
            old_status,
            new_status,
            old_assigned_to,
            new_assigned_to,
            "Bug assignment updated",
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()

    if developer:
        send_email(
            developer[1],
            f"Bug assigned: #{bug_id}",
            f"Hello {developer[2]},\n\nBug #{bug_id} has been assigned to you.\n\nPlease log in to review it.",
        )

    flash("Bug assignment updated.", "success")
    return redirect(url_for("bug.bug_details", bug_id=bug_id))


@bug_bp.route("/bugs/<int:bug_id>/status", methods=["POST"])
@role_required("developer")
def update_status(bug_id):
    new_status = request.form.get("status", "")
    if new_status not in STATUSES:
        flash("Please select a valid status.", "error")
        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    with db_cursor(dictionary=True, commit=True) as cursor:
        cursor.execute(
            "SELECT status, assigned_to FROM bugs WHERE id = %s AND organization_id = %s",
            (bug_id, session["organization_id"]),
        )
        bug = cursor.fetchone()
        if not bug:
            abort(404)

        if not can_update_bug_status(bug, session["user_id"], session.get("role")):
            flash("Only the developer assigned to this bug can update its status.", "error")
            return redirect(url_for("bug.bug_details", bug_id=bug_id))

        old_status = bug["status"]
        cursor.execute(
            "UPDATE bugs SET status = %s WHERE id = %s AND organization_id = %s",
            (new_status, bug_id, session["organization_id"]),
        )
        cursor.execute(
            """
            INSERT INTO bug_history (bug_id, changed_by, old_status, new_status, change_note)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (bug_id, session["user_id"], old_status, new_status, "Bug status updated"),
        )

        cursor.execute(
            """
            SELECT reporter.email, reporter.full_name, bugs.issue_key
            FROM bugs
            JOIN users AS reporter ON bugs.reporter_id = reporter.id
            WHERE bugs.id = %s AND bugs.organization_id = %s
            """,
            (bug_id, session["organization_id"]),
        )
        reporter = cursor.fetchone()
        cursor.execute(
            """
            SELECT users.email, users.full_name
            FROM issue_watchers
            JOIN users ON issue_watchers.user_id = users.id
            WHERE issue_watchers.bug_id = %s AND users.organization_id = %s
              AND users.id != %s
            """,
            (bug_id, session["organization_id"], session["user_id"]),
        )
        watchers = cursor.fetchall()

    flash("Bug status updated successfully.", "success")
    if reporter:
        send_email(
            reporter["email"],
            f"Issue status updated: {reporter['issue_key']}",
            f"Hello {reporter['full_name']},\n\n{reporter['issue_key']} status changed from {old_status} to {new_status}.",
        )
    for watcher in watchers:
        send_email(
            watcher["email"],
            f"Watched issue updated: {reporter['issue_key']}",
            f"Hello {watcher['full_name']},\n\n{reporter['issue_key']} status changed from {old_status} to {new_status}.",
        )
    if request.form.get("return_to") == "board":
        return redirect(url_for("project.board", project=request.form.get("project", "")))
    return redirect(url_for("bug.bug_details", bug_id=bug_id))


@bug_bp.route("/bugs/<int:bug_id>/comment", methods=["POST"])
@login_required
def add_comment(bug_id):
    comment = request.form.get("comment", "").strip()
    if not comment:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM bugs WHERE id = %s AND organization_id = %s",
        (bug_id, session["organization_id"]),
    )
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        abort(404)

    cursor.execute(
        "INSERT INTO comments (bug_id, user_id, comment) VALUES (%s, %s, %s)",
        (bug_id, session["user_id"], comment),
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash("Comment added.", "success")
    return redirect(url_for("bug.bug_details", bug_id=bug_id))


@bug_bp.route("/bugs/<int:bug_id>/watch", methods=["POST"])
@login_required
def toggle_watch(bug_id):
    action = request.form.get("action", "watch")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM bugs WHERE id = %s AND organization_id = %s",
        (bug_id, session["organization_id"]),
    )
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        abort(404)

    if action == "unwatch":
        cursor.execute(
            "DELETE FROM issue_watchers WHERE bug_id = %s AND user_id = %s",
            (bug_id, session["user_id"]),
        )
        message = "You are no longer watching this issue."
    else:
        cursor.execute(
            "INSERT IGNORE INTO issue_watchers (bug_id, user_id) VALUES (%s, %s)",
            (bug_id, session["user_id"]),
        )
        message = "You are now watching this issue."
    conn.commit()
    cursor.close()
    conn.close()
    flash(message, "success")
    return redirect(url_for("bug.bug_details", bug_id=bug_id))
