import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error

from config import get_db_connection
from repositories.issue_repository import count_board_issues, get_board_issues, get_projects, get_developers
from repositories.sprint_repository import get_sprints
from services.issue_service import STATUSES
from utils.decorators import login_required
from utils.pagination import pagination_values


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
    selected_sprint = request.args.get("sprint", "")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    projects = get_projects(cursor, session["organization_id"])
    project_id = int(selected_project) if selected_project.isdigit() else None
    try:
        sprints = get_sprints(cursor, session["organization_id"], project_id) if project_id else []
    except Exception:
        sprints = []
    sprint_id = selected_sprint if selected_sprint else None
    page_size = current_app.config["BOARD_PAGE_SIZE"]
    total = count_board_issues(cursor, session["organization_id"], project_id, sprint_id)
    pagination = pagination_values(request.args.get("page", 1), total, page_size)
    offset = (pagination["page"] - 1) * page_size
    issues = get_board_issues(
        cursor, session["organization_id"], project_id, page_size, offset, sprint_id
    )
    developers = get_developers(cursor, session["organization_id"])
    cursor.close()
    conn.close()

    columns = {status: [] for status in STATUSES}
    for issue in issues:
        issue["label_list"] = [label.strip() for label in (issue["labels"] or "").split(",") if label.strip()]
        columns.get(issue["status"], columns["To Do"]).append(issue)

    active_sprint = next((s for s in sprints if s["status"] == "active"), None) if sprints else None
    return render_template(
        "board.html",
        columns=columns,
        statuses=STATUSES,
        projects=projects,
        sprints=sprints,
        active_sprint=active_sprint,
        developers=developers,
        selected_project=selected_project,
        pagination=pagination,
    )
