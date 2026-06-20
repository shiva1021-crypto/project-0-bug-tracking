import json

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from config import get_db_connection
from repositories.custom_field_repository import (
    create_field_definition,
    delete_field_definition,
    get_field_definitions,
)
from utils.decorators import login_required


def register_custom_field_routes(bp):
    @bp.route("/projects/<int:project_id>/custom-fields", methods=["GET", "POST"])
    @login_required
    def project_custom_fields(project_id):
        if session.get("role") not in {"admin", "project_manager"}:
            flash("Only administrators and project managers can manage custom fields.", "error")
            return redirect(url_for("project.board"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM projects WHERE id = %s AND organization_id = %s",
            (project_id, session["organization_id"]),
        )
        project = cursor.fetchone()
        if not project:
            cursor.close()
            conn.close()
            flash("Project not found.", "error")
            return redirect(url_for("project.projects"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            field_type = request.form.get("field_type", "")
            required = request.form.get("required") == "on"
            options_raw = request.form.get("options", "").strip()

            if not name or field_type not in ("text", "number", "date", "dropdown", "checkbox"):
                flash("Enter a valid field name and type.", "error")
                return redirect(url_for("bug.project_custom_fields", project_id=project_id))

            options_list = None
            if field_type == "dropdown":
                options_list = [o.strip() for o in options_raw.split("\n") if o.strip()]
                if len(options_list) < 2:
                    flash("Dropdown fields need at least 2 options (one per line).", "error")
                    return redirect(url_for("bug.project_custom_fields", project_id=project_id))

            try:
                create_field_definition(
                    cursor, session["organization_id"], project_id, name, field_type, options_list, required
                )
                conn.commit()
                flash(f"Custom field '{name}' created.", "success")
            except Exception:
                conn.rollback()
                flash("Could not create custom field.", "error")

            return redirect(url_for("bug.project_custom_fields", project_id=project_id))

        fields = get_field_definitions(cursor, session["organization_id"], project_id)
        cursor.close()
        conn.close()

        return render_template(
            "project_custom_fields.html",
            project=project,
            fields=fields,
        )

    @bp.route("/projects/<int:project_id>/custom-fields/<int:field_id>/delete", methods=["POST"])
    @login_required
    def delete_custom_field(project_id, field_id):
        if session.get("role") not in {"admin", "project_manager"}:
            flash("Only administrators and project managers can delete custom fields.", "error")
            return redirect(url_for("project.board"))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            delete_field_definition(cursor, field_id, session["organization_id"])
            conn.commit()
            flash("Custom field deleted.", "success")
        except Exception:
            conn.rollback()
            flash("Could not delete custom field.", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("bug.project_custom_fields", project_id=project_id))

    @bp.route("/api/projects/<int:project_id>/custom-fields")
    @login_required
    def api_custom_fields(project_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        fields = get_field_definitions(cursor, session["organization_id"], project_id)
        cursor.close()
        conn.close()
        return jsonify(fields)
