import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error

from config import get_db_connection
from routes.bug_routes import STATUSES
from utils.decorators import login_required


project_bp = Blueprint("project", __name__)


@project_bp.route("/projects", methods=["GET", "POST"])
@login_required
def projects():
    if request.method == "POST":
        if session.get("role") not in {"admin", "project_manager"}:
            flash("Only administrators and project managers can create projects.", "error")
            return redirect(url_for("project.projects"))

        name = request.form.get("name", "").strip()
        project_key = request.form.get("project_key", "").strip().upper()
        description = request.form.get("description", "").strip()
        if not name or not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", project_key):
            flash("Enter a project name and a 2-10 character key beginning with a letter.", "error")
            return redirect(url_for("project.projects"))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO projects (organization_id, name, project_key, description)
                VALUES (%s, %s, %s, %s)
                """,
                (session["organization_id"], name, project_key, description or None),
            )
            conn.commit()
            flash(f"Project {project_key} created.", "success")
        except Error as exc:
            conn.rollback()
            if exc.errno == 1062:
                flash("That project key is already in use in your organization.", "error")
            else:
                raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("project.projects"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT projects.*, COUNT(bugs.id) AS issue_count
        FROM projects
        LEFT JOIN bugs ON bugs.project_id = projects.id
        WHERE projects.organization_id = %s
        GROUP BY projects.id
        ORDER BY projects.name
        """,
        (session["organization_id"],),
    )
    all_projects = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("projects.html", projects=all_projects)


@project_bp.route("/board")
@login_required
def board():
    selected_project = request.args.get("project", "")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, name, project_key
        FROM projects
        WHERE organization_id = %s
        ORDER BY name
        """,
        (session["organization_id"],),
    )
    projects = cursor.fetchall()

    query = """
        SELECT bugs.id, bugs.issue_key, bugs.issue_type, bugs.title, bugs.status,
               bugs.priority, bugs.story_points, bugs.due_date, bugs.labels,
               bugs.assigned_to, users.full_name AS assignee_name,
               projects.name AS project_name, projects.project_key
        FROM bugs
        JOIN projects ON bugs.project_id = projects.id
        LEFT JOIN users ON bugs.assigned_to = users.id
        WHERE bugs.organization_id = %s
    """
    params = [session["organization_id"]]
    if selected_project.isdigit():
        query += " AND bugs.project_id = %s"
        params.append(int(selected_project))
    query += " ORDER BY bugs.priority DESC, bugs.created_at DESC"
    cursor.execute(query, params)
    issues = cursor.fetchall()
    cursor.close()
    conn.close()

    columns = {status: [] for status in STATUSES}
    for issue in issues:
        issue["label_list"] = [label.strip() for label in (issue["labels"] or "").split(",") if label.strip()]
        columns[issue["status"]].append(issue)
    return render_template(
        "board.html",
        columns=columns,
        statuses=STATUSES,
        projects=projects,
        selected_project=selected_project,
    )
