from flask import abort, flash, redirect, request, session, url_for

from config import db_cursor, get_db_connection
from repositories.workflow_repository import (
    add_comment as save_comment,
    get_assignment,
    get_developer,
    get_reporter,
    get_status_context,
    get_watchers,
    issue_exists,
    save_assignment,
    save_status,
    set_watching,
)
from routes.bug_blueprint import bug_bp
from services.issue_service import STATUSES
from utils.decorators import can_update_bug_status, login_required, role_required
from utils.notifications import queue_email


@bug_bp.route("/bugs/<int:bug_id>/assign", methods=["POST"])
@role_required("admin", "project_manager")
def assign_bug(bug_id):
    developer_id = request.form.get("developer_id", "")
    new_assigned_to = int(developer_id) if developer_id.isdigit() else None

    conn = get_db_connection()
    cursor = conn.cursor()
    bug = get_assignment(cursor, bug_id, session["organization_id"])
    if not bug:
        cursor.close()
        conn.close()
        abort(404)

    old_assigned_to, old_status, issue_key = bug
    new_status = "In Progress" if new_assigned_to and old_status == "Open" else old_status

    developer = None
    if new_assigned_to:
        developer = get_developer(cursor, new_assigned_to, session["organization_id"])
        if not developer:
            cursor.close()
            conn.close()
            flash("Please select a developer from your organization.", "error")
            return redirect(url_for("bug.bug_details", bug_id=bug_id))

    save_assignment(
        cursor, bug_id, session["organization_id"], session["user_id"], old_assigned_to,
        old_status, new_assigned_to, new_status,
    )
    conn.commit()
    cursor.close()
    conn.close()

    if developer:
        queue_email(
            developer[1],
            f"Issue assigned: {issue_key}",
            f"Hello {developer[2]},\n\n{issue_key} has been assigned to you.",
        )
    flash("Issue assignment updated.", "success")
    return redirect(url_for("bug.bug_details", bug_id=bug_id))


@bug_bp.route("/bugs/<int:bug_id>/status", methods=["POST"])
@role_required("developer")
def update_status(bug_id):
    new_status = request.form.get("status", "")
    if new_status not in STATUSES:
        flash("Please select a valid status.", "error")
        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    with db_cursor(dictionary=True, commit=True) as cursor:
        bug = get_status_context(cursor, bug_id, session["organization_id"])
        if not bug:
            abort(404)
        if not can_update_bug_status(bug, session["user_id"], session.get("role")):
            flash("Only the developer assigned to this issue can update its status.", "error")
            return redirect(url_for("bug.bug_details", bug_id=bug_id))

        old_status = bug["status"]
        save_status(
            cursor, bug_id, session["organization_id"], session["user_id"], old_status, new_status
        )
        reporter = get_reporter(cursor, bug_id, session["organization_id"])
        watchers = get_watchers(
            cursor, bug_id, session["organization_id"],
            (session["user_id"], reporter["reporter_id"]),
        )

    queue_email(
        reporter["email"],
        f"Issue status updated: {reporter['issue_key']}",
        f"Hello {reporter['full_name']},\n\n{reporter['issue_key']} changed from {old_status} to {new_status}.",
    )
    for watcher in watchers:
        queue_email(
            watcher["email"],
            f"Watched issue updated: {reporter['issue_key']}",
            f"Hello {watcher['full_name']},\n\n{reporter['issue_key']} changed from {old_status} to {new_status}.",
        )
    flash("Issue status updated successfully.", "success")
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

    with db_cursor(commit=True) as cursor:
        if not issue_exists(cursor, bug_id, session["organization_id"]):
            abort(404)
        save_comment(cursor, bug_id, session["user_id"], comment)
    flash("Comment added.", "success")
    return redirect(url_for("bug.bug_details", bug_id=bug_id))


@bug_bp.route("/bugs/<int:bug_id>/watch", methods=["POST"])
@login_required
def toggle_watch(bug_id):
    action = request.form.get("action", "watch")
    with db_cursor(commit=True) as cursor:
        if not issue_exists(cursor, bug_id, session["organization_id"]):
            abort(404)
        if action == "unwatch":
            set_watching(cursor, bug_id, session["user_id"], False)
            message = "You are no longer watching this issue."
        else:
            set_watching(cursor, bug_id, session["user_id"], True)
            message = "You are now watching this issue."
    flash(message, "success")
    return redirect(url_for("bug.bug_details", bug_id=bug_id))
