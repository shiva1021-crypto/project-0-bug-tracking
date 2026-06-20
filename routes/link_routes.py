from flask import abort, request, session

from config import get_db_connection
from repositories.link_repository import (
    get_issue_key,
    link_issues as repo_link_issues,
    unlink_issues as repo_unlink_issues,
)
from utils.decorators import login_required, role_required
from utils.responses import action_response


LINK_TYPES = ("blocks", "relates_to", "duplicates", "clones")


def register_link_routes(bp):
    @bp.route("/bugs/<int:bug_id>/link", methods=["POST"])
    @login_required
    def link_issue(bug_id):
        other_key = request.form.get("other_key", "").strip().upper()
        link_type = request.form.get("link_type", "")
        if not other_key or link_type not in LINK_TYPES:
            return action_response(
                "Enter a valid issue key and select a link type.", "bug.bug_details",
                status=400, category="error", bug_id=bug_id,
            )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id FROM bugs
            WHERE issue_key = %s AND organization_id = %s AND id != %s
            """,
            (other_key, session["organization_id"], bug_id),
        )
        other = cursor.fetchone()
        if not other:
            cursor.close()
            conn.close()
            return action_response(
                f"Issue \"{other_key}\" not found in your organization.", "bug.bug_details",
                status=404, category="error", bug_id=bug_id,
            )

        linked = repo_link_issues(cursor, bug_id, other["id"], link_type)
        if not linked:
            cursor.close()
            conn.close()
            return action_response(
                "These issues are already linked.", "bug.bug_details",
                status=409, category="error", bug_id=bug_id,
            )

        cursor.execute(
            """
            INSERT INTO bug_history (bug_id, changed_by, change_note)
            VALUES (%s, %s, %s)
            """,
            (bug_id, session["user_id"], f"Linked to {other_key} ({link_type})"),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return action_response(
            f"Linked to {other_key}.", "bug.bug_details", bug_id=bug_id,
        )

    @bp.route("/bugs/<int:bug_id>/unlink/<int:link_id>", methods=["POST"])
    @login_required
    def unlink_issue(bug_id, link_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        repo_unlink_issues(cursor, link_id)
        conn.commit()
        cursor.close()
        conn.close()
        return action_response("Link removed.", "bug.bug_details", bug_id=bug_id)
