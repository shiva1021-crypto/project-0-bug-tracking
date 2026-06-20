import csv
from io import StringIO

from flask import Blueprint, Response, current_app, render_template, request, session, url_for

from config import get_db_connection
from services.issue_service import ISSUE_TYPES, PRIORITIES, SEVERITIES, STATUSES
from utils.decorators import role_required
from utils.pagination import pagination_values


report_bp = Blueprint("report", __name__)


def safe_csv_cell(value):
    if value is None:
        return ""

    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


def with_percent(rows, label_key):
    max_total = max([row["total"] for row in rows], default=0) or 1
    return [
        {
            "label": row[label_key],
            "total": row["total"],
            "percent": round((row["total"] / max_total) * 100),
        }
        for row in rows
    ]


def build_report_query(args):
    query = """
        SELECT bugs.id, bugs.issue_key, bugs.issue_type, bugs.title, bugs.category,
               bugs.status, bugs.priority, bugs.severity, bugs.story_points, bugs.due_date,
               bugs.created_at, reporter.full_name AS reporter_name,
               developer.full_name AS developer_name, projects.name AS project_name
        FROM bugs
        JOIN projects ON bugs.project_id = projects.id
        JOIN users AS reporter ON bugs.reporter_id = reporter.id
        LEFT JOIN users AS developer ON bugs.assigned_to = developer.id
        WHERE bugs.organization_id = %s
    """
    params = [session["organization_id"]]

    status = args.get("status", "")
    priority = args.get("priority", "")
    severity = args.get("severity", "")
    start_date = args.get("start_date", "")
    end_date = args.get("end_date", "")
    project_id = args.get("project", "")
    issue_type = args.get("issue_type", "")

    if status in STATUSES:
        query += " AND bugs.status = %s"
        params.append(status)
    if priority in PRIORITIES:
        query += " AND bugs.priority = %s"
        params.append(priority)
    if severity in SEVERITIES:
        query += " AND bugs.severity = %s"
        params.append(severity)
    if start_date:
        query += " AND DATE(bugs.created_at) >= %s"
        params.append(start_date)
    if end_date:
        query += " AND DATE(bugs.created_at) <= %s"
        params.append(end_date)
    if project_id.isdigit():
        query += " AND bugs.project_id = %s"
        params.append(int(project_id))
    if issue_type in ISSUE_TYPES:
        query += " AND bugs.issue_type = %s"
        params.append(issue_type)

    query += " ORDER BY bugs.created_at DESC"
    return query, params


@report_bp.route("/reports")
@role_required("admin", "project_manager")
def reports():
    query, params = build_report_query(request.args)
    export_args = request.args.to_dict(flat=True)
    export_args.pop("page", None)
    export_args["export"] = "csv"
    is_csv_export = request.args.get("export") == "csv"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    pagination = None
    if not is_csv_export:
        cursor.execute(f"SELECT COUNT(*) AS total FROM ({query}) AS filtered_bugs", params)
        total_items = cursor.fetchone()["total"]
        pagination = pagination_values(
            request.args.get("page", 1), total_items, current_app.config["PAGE_SIZE"]
        )
        offset = (pagination["page"] - 1) * pagination["page_size"]
        query += " LIMIT %s OFFSET %s"
        params = [*params, pagination["page_size"], offset]

    cursor.execute(query, params)
    bugs = cursor.fetchall()

    cursor.execute(
        "SELECT status, COUNT(*) AS total FROM bugs WHERE organization_id = %s GROUP BY status",
        (session["organization_id"],),
    )
    status_counts = cursor.fetchall()
    cursor.execute(
        "SELECT priority, COUNT(*) AS total FROM bugs WHERE organization_id = %s GROUP BY priority",
        (session["organization_id"],),
    )
    priority_counts = cursor.fetchall()
    cursor.execute(
        "SELECT category, COUNT(*) AS total FROM bugs WHERE organization_id = %s GROUP BY category ORDER BY total DESC LIMIT 8",
        (session["organization_id"],),
    )
    category_counts = cursor.fetchall()
    cursor.execute(
        "SELECT id, name, project_key FROM projects WHERE organization_id = %s ORDER BY name",
        (session["organization_id"],),
    )
    projects = cursor.fetchall()

    cursor.close()
    conn.close()

    if is_csv_export:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Key", "Type", "Issue", "Project", "Category", "Status", "Priority", "Severity", "Points", "Due", "Reporter", "Assigned", "Created"])
        for bug in bugs:
            writer.writerow(
                [
                    safe_csv_cell(value)
                    for value in (
                    bug["issue_key"],
                    bug["issue_type"],
                    bug["title"],
                    bug["project_name"],
                    bug["category"],
                    bug["status"],
                    bug["priority"],
                    bug["severity"],
                    bug["story_points"] or "",
                    bug["due_date"] or "",
                    bug["reporter_name"],
                    bug["developer_name"] or "Not Assigned",
                    bug["created_at"],
                    )
                ]
            )

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=bug_report.csv"},
        )

    return render_template(
        "reports.html",
        bugs=bugs,
        status_counts=status_counts,
        priority_counts=priority_counts,
        status_chart=with_percent(status_counts, "status"),
        priority_chart=with_percent(priority_counts, "priority"),
        category_chart=with_percent(category_counts, "category"),
        export_url=url_for("report.reports", **export_args),
        statuses=STATUSES,
        priorities=PRIORITIES,
        severities=SEVERITIES,
        issue_types=ISSUE_TYPES,
        projects=projects,
        filters=request.args,
        pagination=pagination,
        page_args={
            key: value
            for key, value in request.args.items()
            if key not in {"page", "export"}
        },
    )
