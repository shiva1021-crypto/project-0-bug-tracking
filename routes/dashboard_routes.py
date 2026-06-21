from flask import flash, redirect, render_template, request, session, url_for

from config import get_db_connection
from repositories.dashboard_repository import add_widget, get_widgets, remove_widget
from repositories.issue_repository import get_projects


from utils.decorators import login_required


WIDGET_TYPES = [
    ("stats_summary", "Statistics Summary"),
    ("recent_issues", "Recent Issues"),
    ("issues_by_status", "Issues by Status"),
    ("issues_by_priority", "Issues by Priority"),
    ("issues_by_severity", "Issues by Severity"),
    ("issues_by_type", "Issues by Type"),
]


def register_dashboard_routes(bp):
    @bp.route("/dashboard")
    @login_required
    def dashboard():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        widgets = get_widgets(cursor, session["organization_id"], session["user_id"])
        if not widgets:
            widgets = get_widgets(cursor, session["organization_id"])
        if not widgets:
            widgets = _default_widgets(cursor, session["organization_id"])
            for w in widgets:
                add_widget(cursor, session["organization_id"], session["user_id"],
                           w["widget_type"], w["title"], w.get("config"), w.get("width", "full"))
            conn.commit()
            widgets = get_widgets(cursor, session["organization_id"], session["user_id"])

        widget_data = []
        for w in widgets:
            data = _render_widget_data(cursor, session["organization_id"], w)
            widget_data.append(data)

        projects = get_projects(cursor, session["organization_id"])
        cursor.close()
        conn.close()

        return render_template(
            "dashboard.html",
            widget_data=widget_data,
            widget_types=WIDGET_TYPES,
            projects=projects,
        )

    @bp.route("/dashboard/add-widget", methods=["POST"])
    @login_required
    def add_dashboard_widget():
        widget_type = request.form.get("widget_type", "")
        title = request.form.get("title", "").strip()
        width = request.form.get("width", "full")

        valid_types = {t[0] for t in WIDGET_TYPES}
        if widget_type not in valid_types or not title:
            flash("Please select a valid widget type and enter a title.", "error")
            return redirect(url_for("bug.dashboard"))

        config = None
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            add_widget(cursor, session["organization_id"], session["user_id"],
                       widget_type, title, config, width)
            conn.commit()
            flash(f"Widget '{title}' added.", "success")
        except Exception:
            conn.rollback()
            flash("Could not add widget.", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("bug.dashboard"))

    @bp.route("/dashboard/<int:widget_id>/remove", methods=["POST"])
    @login_required
    def remove_dashboard_widget(widget_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            remove_widget(cursor, widget_id, session["organization_id"])
            conn.commit()
            flash("Widget removed.", "success")
        except Exception:
            conn.rollback()
            flash("Could not remove widget.", "error")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("bug.dashboard"))


def _default_widgets(cursor, organization_id):
    return [
        {"widget_type": "stats_summary", "title": "Statistics Summary", "config": None, "width": "full"},
        {"widget_type": "issues_by_status", "title": "Issues by Status", "config": None, "width": "half"},
        {"widget_type": "issues_by_priority", "title": "Issues by Priority", "config": None, "width": "half"},
        {"widget_type": "recent_issues", "title": "Recent Issues", "config": None, "width": "full"},
    ]


def _render_widget_data(cursor, organization_id, widget):
    base = {
        "id": widget["id"],
        "widget_type": widget["widget_type"],
        "title": widget["title"],
        "width": widget.get("width", "full"),
        "config": widget.get("config", {}),
    }

    org_filter = (organization_id,)

    if widget["widget_type"] == "stats_summary":
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(status = 'To Do') AS todo,
                SUM(status = 'In Progress') AS in_progress,
                SUM(status = 'Testing') AS testing,
                SUM(status = 'Done') AS done,
                SUM(severity IN ('Critical', 'Blocker')) AS critical
            FROM bugs WHERE organization_id = %s
            """,
            org_filter,
        )
        base["data"] = cursor.fetchone()

    elif widget["widget_type"] == "recent_issues":
        cursor.execute(
            """
            SELECT bugs.id, bugs.issue_key, bugs.issue_type, bugs.title,
                   bugs.priority, bugs.severity, bugs.status,
                   reporter.full_name AS reporter_name,
                   developer.full_name AS developer_name
            FROM bugs
            JOIN users AS reporter ON bugs.reporter_id = reporter.id
            LEFT JOIN users AS developer ON bugs.assigned_to = developer.id
            WHERE bugs.organization_id = %s
            ORDER BY bugs.created_at DESC LIMIT 10
            """,
            org_filter,
        )
        base["data"] = cursor.fetchall()

    elif widget["widget_type"] == "issues_by_status":
        cursor.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM bugs WHERE organization_id = %s
            GROUP BY status ORDER BY count DESC
            """,
            org_filter,
        )
        base["data"] = cursor.fetchall()

    elif widget["widget_type"] == "issues_by_priority":
        cursor.execute(
            """
            SELECT priority, COUNT(*) AS count
            FROM bugs WHERE organization_id = %s
            GROUP BY priority ORDER BY FIELD(priority, 'Urgent','Highest','High','Medium','Low','Lowest')
            """,
            org_filter,
        )
        base["data"] = cursor.fetchall()

    elif widget["widget_type"] == "issues_by_severity":
        cursor.execute(
            """
            SELECT severity, COUNT(*) AS count
            FROM bugs WHERE organization_id = %s
            GROUP BY severity ORDER BY count DESC
            """,
            org_filter,
        )
        base["data"] = cursor.fetchall()

    elif widget["widget_type"] == "issues_by_type":
        cursor.execute(
            """
            SELECT issue_type, COUNT(*) AS count
            FROM bugs WHERE organization_id = %s
            GROUP BY issue_type ORDER BY count DESC
            """,
            org_filter,
        )
        base["data"] = cursor.fetchall()

    return base
