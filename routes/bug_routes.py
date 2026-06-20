import os
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
        SELECT bugs.id, bugs.title, bugs.priority, bugs.severity, bugs.status,
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
@role_required("tester", "admin", "project_manager")
def add_bug():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        reproduction_steps = request.form.get("reproduction_steps", "").strip()
        category = request.form.get("category", "General").strip() or "General"
        external_issue_url = request.form.get("external_issue_url", "").strip()
        priority = request.form.get("priority", "")
        severity = request.form.get("severity", "")

        if not title or not description or priority not in PRIORITIES or severity not in SEVERITIES:
            flash("Please fill all required bug fields with valid values.", "error")
            return redirect(url_for("bug.add_bug"))

        screenshot_filename = save_screenshot(request.files.get("screenshot"))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bugs
            (organization_id, title, description, reproduction_steps, category, priority, severity, reporter_id, screenshot_path, external_issue_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["organization_id"],
                title,
                description,
                reproduction_steps,
                category,
                priority,
                severity,
                session["user_id"],
                screenshot_filename,
                external_issue_url or None,
            ),
        )
        bug_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO bug_history (bug_id, changed_by, new_status, change_note)
            VALUES (%s, %s, %s, %s)
            """,
            (bug_id, session["user_id"], "Open", "Bug reported"),
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Bug reported successfully.", "success")
        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    return render_template("add_bug.html", priorities=PRIORITIES, severities=SEVERITIES, categories=DEFAULT_CATEGORIES)


@bug_bp.route("/bugs")
@login_required
def view_bugs():
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    severity = request.args.get("severity", "")
    assigned_to = request.args.get("assigned_to", "")
    search = request.args.get("q", "").strip()

    select_query = """
        SELECT bugs.id, bugs.title, bugs.description, bugs.category, bugs.priority, bugs.severity,
               bugs.status, bugs.created_at, reporter.full_name AS reporter_name,
               developer.full_name AS developer_name
        FROM bugs
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
    if search:
        select_query += " AND (bugs.title LIKE %s OR bugs.description LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])

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
    cursor.close()
    conn.close()

    return render_template(
        "view_bugs.html",
        bugs=bugs,
        developers=developers,
        statuses=STATUSES,
        priorities=PRIORITIES,
        severities=SEVERITIES,
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
               developer.full_name AS developer_name
        FROM bugs
        JOIN users AS reporter ON bugs.reporter_id = reporter.id
        LEFT JOIN users AS developer ON bugs.assigned_to = developer.id
        WHERE bugs.id = %s AND bugs.organization_id = %s
        """,
        (bug_id, session["organization_id"]),
    )
    bug = cursor.fetchone()
    if not bug:
        cursor.close()
        conn.close()
        abort(404)

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

        if not title or not description or priority not in PRIORITIES or severity not in SEVERITIES:
            flash("Please provide valid bug details.", "error")
            return redirect(url_for("bug.edit_bug", bug_id=bug_id))

        screenshot_filename = bug["screenshot_path"]
        uploaded = save_screenshot(request.files.get("screenshot"))
        if uploaded:
            screenshot_filename = uploaded

        cursor.execute(
            """
            UPDATE bugs
            SET title = %s, description = %s, reproduction_steps = %s,
                category = %s, priority = %s, severity = %s,
                screenshot_path = %s, external_issue_url = %s
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

    cursor.close()
    conn.close()
    return render_template("edit_bug.html", bug=bug, priorities=PRIORITIES, severities=SEVERITIES, categories=DEFAULT_CATEGORIES)


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
            SELECT reporter.email, reporter.full_name
            FROM bugs
            JOIN users AS reporter ON bugs.reporter_id = reporter.id
            WHERE bugs.id = %s AND bugs.organization_id = %s
            """,
            (bug_id, session["organization_id"]),
        )
        reporter = cursor.fetchone()

    flash("Bug status updated successfully.", "success")
    if reporter:
        send_email(
            reporter["email"],
            f"Bug status updated: #{bug_id}",
            f"Hello {reporter['full_name']},\n\nBug #{bug_id} status changed from {old_status} to {new_status}.",
        )
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
