from flask import abort, flash, redirect, render_template, request, session, url_for

from config import get_db_connection
from repositories.issue_repository import get_projects
from repositories.version_repository import (
    create_version as repo_create_version,
    get_version_issues,
    get_versions,
    update_version_status as repo_update_version_status,
)
from utils.decorators import login_required, role_required
from utils.responses import action_response


def register_version_routes(bp):
    @bp.route("/versions")
    @login_required
    def versions():
        project_id = request.args.get("project", "")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        projects = get_projects(cursor, session["organization_id"])
        selected = int(project_id) if project_id.isdigit() else (projects[0]["id"] if projects else None)
        version_list = []
        if selected:
            version_list = get_versions(cursor, session["organization_id"], selected)
            for v in version_list:
                v["issues"] = get_version_issues(cursor, v["id"], session["organization_id"])
                for issue in v["issues"]:
                    issue["label_list"] = [label.strip() for label in (issue.get("labels") or "").split(",") if label.strip()]
        cursor.close()
        conn.close()
        return render_template(
            "versions.html",
            projects=projects,
            selected_project=str(selected) if selected else "",
            version_list=version_list,
        )

    @bp.route("/versions/create", methods=["POST"])
    @role_required("admin", "project_manager")
    def version_create():
        name = request.form.get("name", "").strip()
        project_id = request.form.get("project_id", "")
        description = request.form.get("description", "").strip()
        release_date = request.form.get("release_date", "").strip() or None
        if not name or not project_id.isdigit():
            flash("Version name and project are required.", "error")
            return redirect(url_for("bug.versions", project=project_id))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        repo_create_version(cursor, session["organization_id"], int(project_id), name, description, release_date)
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Version \"{name}\" created.", "success")
        return redirect(url_for("bug.versions", project=project_id))

    @bp.route("/versions/<int:version_id>/release", methods=["POST"])
    @role_required("admin", "project_manager")
    def version_release(version_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT project_id FROM versions WHERE id = %s AND organization_id = %s", (version_id, session["organization_id"]))
        version = cursor.fetchone()
        if not version:
            cursor.close()
            conn.close()
            abort(404)
        repo_update_version_status(cursor, version_id, session["organization_id"], "released")
        conn.commit()
        cursor.close()
        conn.close()
        flash("Version released.", "success")
        return redirect(url_for("bug.versions", project=version["project_id"]))

    @bp.route("/versions/<int:version_id>/archive", methods=["POST"])
    @role_required("admin", "project_manager")
    def version_archive(version_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT project_id FROM versions WHERE id = %s AND organization_id = %s", (version_id, session["organization_id"]))
        version = cursor.fetchone()
        if not version:
            cursor.close()
            conn.close()
            abort(404)
        repo_update_version_status(cursor, version_id, session["organization_id"], "archived")
        conn.commit()
        cursor.close()
        conn.close()
        flash("Version archived.", "success")
        return redirect(url_for("bug.versions", project=version["project_id"]))
