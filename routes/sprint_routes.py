from datetime import date

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for

from config import get_db_connection
from repositories.issue_repository import get_projects
from repositories.sprint_repository import (
    close_sprint as repo_close_sprint,
    create_sprint as repo_create_sprint,
    get_active_sprint,
    get_backlog_issues,
    get_sprint,
    get_sprint_burndown,
    get_sprint_issues,
    get_sprints,
    remove_issue_sprint,
    set_issue_sprint,
    start_sprint as repo_start_sprint,
    update_sprint as repo_update_sprint,
)
from utils.decorators import login_required, role_required
from utils.responses import action_response


def register_sprint_routes(bp):
    @bp.route("/backlog")
    @login_required
    def backlog():
        project_id = request.args.get("project", "")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        projects = get_projects(cursor, session["organization_id"])
        selected = int(project_id) if project_id.isdigit() else (projects[0]["id"] if projects else None)
        sprints = []
        backlog_issues = []
        active = None
        if selected:
            try:
                sprints = get_sprints(cursor, session["organization_id"], selected)
                active = get_active_sprint(cursor, session["organization_id"], selected)
                backlog_issues = get_backlog_issues(cursor, session["organization_id"], selected)
            except Exception:
                sprints = []
                active = None
                backlog_issues = []
            for issue in backlog_issues:
                issue["label_list"] = [label.strip() for label in (issue["labels"] or "").split(",") if label.strip()]
            for sprint in sprints:
                sprint["issues"] = get_sprint_issues(cursor, sprint["id"], session["organization_id"])
                for issue in sprint["issues"]:
                    issue["label_list"] = [label.strip() for label in (issue["labels"] or "").split(",") if label.strip()]
        cursor.close()
        conn.close()
        return render_template(
            "backlog.html",
            projects=projects,
            selected_project=str(selected) if selected else "",
            sprints=sprints,
            active_sprint=active,
            backlog_issues=backlog_issues,
        )

    @bp.route("/sprints/create", methods=["POST"])
    @role_required("admin", "project_manager")
    def sprint_create():
        name = request.form.get("name", "").strip()
        project_id = request.form.get("project_id", "")
        goal = request.form.get("goal", "").strip()
        start_date = request.form.get("start_date", "").strip() or None
        end_date = request.form.get("end_date", "").strip() or None
        if not name or not project_id.isdigit():
            flash("Sprint name and project are required.", "error")
            return redirect(url_for("sprint.backlog", project=project_id))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        repo_create_sprint(cursor, session["organization_id"], int(project_id), name, goal, start_date, end_date)
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Sprint \"{name}\" created.", "success")
        return redirect(url_for("sprint.backlog", project=project_id))

    @bp.route("/sprints/<int:sprint_id>/edit", methods=["POST"])
    @role_required("admin", "project_manager")
    def sprint_edit(sprint_id):
        name = request.form.get("name", "").strip()
        goal = request.form.get("goal", "").strip()
        start_date = request.form.get("start_date", "").strip() or None
        end_date = request.form.get("end_date", "").strip() or None
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sprint = get_sprint(cursor, sprint_id, session["organization_id"])
        if not sprint:
            cursor.close()
            conn.close()
            abort(404)
        repo_update_sprint(cursor, sprint_id, session["organization_id"],
                           name=name, goal=goal, start_date=start_date, end_date=end_date)
        conn.commit()
        cursor.close()
        conn.close()
        flash("Sprint updated.", "success")
        return redirect(url_for("sprint.backlog", project=sprint["project_id"]))

    @bp.route("/sprints/<int:sprint_id>/start", methods=["POST"])
    @role_required("admin", "project_manager")
    def sprint_start(sprint_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sprint = get_sprint(cursor, sprint_id, session["organization_id"])
        if not sprint:
            cursor.close()
            conn.close()
            abort(404)
        repo_start_sprint(cursor, sprint_id, session["organization_id"])
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Sprint \"{sprint['name']}\" started.", "success")
        return redirect(url_for("sprint.backlog", project=sprint["project_id"]))

    @bp.route("/sprints/<int:sprint_id>/close", methods=["POST"])
    @role_required("admin", "project_manager")
    def sprint_close(sprint_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        sprint = get_sprint(cursor, sprint_id, session["organization_id"])
        if not sprint:
            cursor.close()
            conn.close()
            abort(404)
        repo_close_sprint(cursor, sprint_id, session["organization_id"])
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Sprint \"{sprint['name']}\" closed.", "success")
        return redirect(url_for("sprint.backlog", project=sprint["project_id"]))

    @bp.route("/bugs/<int:bug_id>/sprint", methods=["POST"])
    @role_required("admin", "project_manager", "developer")
    def issue_sprint(bug_id):
        sprint_id = request.form.get("sprint_id", "")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if sprint_id.isdigit():
            set_issue_sprint(cursor, bug_id, int(sprint_id), session["organization_id"])
        else:
            remove_issue_sprint(cursor, bug_id, session["organization_id"])
        conn.commit()
        cursor.close()
        conn.close()
        return action_response("Issue sprint updated.", "sprint.backlog")

    @bp.route("/sprints/<int:sprint_id>/burndown")
    @login_required
    def burndown(sprint_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        data = get_sprint_burndown(cursor, sprint_id, session["organization_id"])
        if not data or not data["start_date"]:
            cursor.close()
            conn.close()
            return jsonify([])
        cursor.execute(
            """
            SELECT DATE(changed_at) AS day,
                   SUM(b.story_points) AS points
            FROM bug_history h
            JOIN bugs b ON h.bug_id = b.id
            WHERE b.sprint_id = %s
              AND h.new_status IN ('Testing', 'Done')
              AND DATE(h.changed_at) >= %s
              AND DATE(h.changed_at) <= COALESCE(%s, CURDATE())
            GROUP BY DATE(h.changed_at)
            ORDER BY day
            """,
            (sprint_id, data["start_date"], data["end_date"]),
        )
        resolved = cursor.fetchall()
        cursor.close()
        conn.close()
        total = data["total_points"] or 0
        end = data["end_date"] or date.today()
        if isinstance(end, str):
            end = date.fromisoformat(str(end))
        start = data["start_date"]
        if isinstance(start, str):
            start = date.fromisoformat(str(start))
        days = (end - start).days or 1
        ideal_per_day = total / days
        points_remaining = total
        series = []
        day_iter = start
        resolved_map = {r["day"]: r["points"] for r in resolved}
        while day_iter <= end:
            points_remaining -= resolved_map.get(day_iter.isoformat(), 0)
            series.append({
                "day": day_iter.isoformat(),
                "remaining": max(points_remaining, 0),
                "ideal": round((days - (day_iter - start).days) * ideal_per_day, 1),
            })
            day_iter += __import__("datetime").timedelta(days=1)
        return jsonify(series)
