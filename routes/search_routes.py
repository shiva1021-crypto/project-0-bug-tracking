from flask import abort, flash, redirect, render_template, request, session, url_for

from config import get_db_connection
from repositories.filter_repository import (
    delete_filter as repo_delete_filter,
    get_filter,
    get_saved_filters,
    save_filter as repo_save_filter,
)
from utils.decorators import login_required
from utils.responses import action_response


def register_search_routes(bp):
    @bp.route("/filters/save", methods=["POST"])
    @login_required
    def save_filter():
        name = request.form.get("name", "").strip()
        if not name:
            flash("Filter name is required.", "error")
            return redirect(url_for("bug.view_bugs"))
        filter_data = {}
        for key in ("q", "status", "priority", "severity", "assigned_to", "project", "issue_type"):
            val = request.form.get(key, "").strip()
            if val:
                filter_data[key] = val
        if not filter_data:
            flash("Apply at least one filter before saving.", "error")
            return redirect(url_for("bug.view_bugs"))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        repo_save_filter(cursor, session["user_id"], session["organization_id"], name, filter_data)
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Filter \"{name}\" saved.", "success")
        return redirect(url_for("bug.view_bugs", **filter_data))

    @bp.route("/filters/<int:filter_id>/delete", methods=["POST"])
    @login_required
    def delete_filter(filter_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        f = get_filter(cursor, filter_id, session["user_id"], session["organization_id"])
        if not f:
            cursor.close()
            conn.close()
            abort(404)
        repo_delete_filter(cursor, filter_id, session["user_id"], session["organization_id"])
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Filter \"{f['name']}\" deleted.", "success")
        return redirect(url_for("bug.view_bugs"))

    @bp.route("/filters/<int:filter_id>/load")
    @login_required
    def load_filter(filter_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        f = get_filter(cursor, filter_id, session["user_id"], session["organization_id"])
        cursor.close()
        conn.close()
        if not f:
            flash("Filter not found.", "error")
            return redirect(url_for("bug.view_bugs"))
        return redirect(url_for("bug.view_bugs", **f["filter_data"]))
