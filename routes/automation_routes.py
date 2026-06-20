from flask import flash, redirect, render_template, request, session, url_for

from config import get_db_connection
from repositories.automation_repository import create_rule, delete_rule, get_rules, toggle_rule
from repositories.issue_repository import get_projects
from utils.decorators import login_required


def register_automation_routes(bp):
    @bp.route("/automation", methods=["GET", "POST"])
    @login_required
    def automation_rules():
        if session.get("role") not in {"admin", "project_manager"}:
            flash("Only administrators and project managers can manage automation rules.", "error")
            return redirect(url_for("project.board"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        projects = get_projects(cursor, session["organization_id"])

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            trigger_event = request.form.get("trigger_event", "")
            project_id = request.form.get("project_id", "")
            action_type = request.form.get("action_type", "")
            action_value = request.form.get("action_value", "").strip()
            condition_field = request.form.get("condition_field", "").strip()
            condition_operator = request.form.get("condition_operator", "").strip()
            condition_value = request.form.get("condition_value", "").strip()

            if not name or trigger_event not in ("issue_created", "status_changed", "field_updated"):
                flash("Enter a valid rule name and trigger event.", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("bug.automation_rules"))

            actions = [{"type": action_type, "value": action_value}] if action_type else []
            if not actions:
                flash("Please specify at least one action.", "error")
                cursor.close()
                conn.close()
                return redirect(url_for("bug.automation_rules"))

            conditions = None
            if condition_field and condition_operator and condition_value:
                conditions = {
                    "field": condition_field,
                    "operator": condition_operator,
                    "value": condition_value,
                }

            try:
                project_id_int = int(project_id) if project_id.isdigit() else None
                create_rule(
                    cursor, session["organization_id"], project_id_int,
                    name, trigger_event, conditions, actions,
                )
                conn.commit()
                flash(f"Automation rule '{name}' created.", "success")
            except Exception:
                conn.rollback()
                flash("Could not create automation rule.", "error")

            return redirect(url_for("bug.automation_rules"))

        rules = get_rules(cursor, session["organization_id"])
        cursor.close()
        conn.close()

        return render_template("automation_rules.html", rules=rules, projects=projects)

    @bp.route("/automation/<int:rule_id>/delete", methods=["POST"])
    @login_required
    def delete_automation_rule(rule_id):
        if session.get("role") not in {"admin", "project_manager"}:
            flash("Permission denied.", "error")
            return redirect(url_for("project.board"))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            delete_rule(cursor, rule_id, session["organization_id"])
            conn.commit()
            flash("Automation rule deleted.", "success")
        except Exception:
            conn.rollback()
            flash("Could not delete rule.", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("bug.automation_rules"))

    @bp.route("/automation/<int:rule_id>/toggle", methods=["POST"])
    @login_required
    def toggle_automation_rule(rule_id):
        if session.get("role") not in {"admin", "project_manager"}:
            flash("Permission denied.", "error")
            return redirect(url_for("project.board"))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            toggle_rule(cursor, rule_id, session["organization_id"])
            conn.commit()
            flash("Rule toggled.", "success")
        except Exception:
            conn.rollback()
            flash("Could not toggle rule.", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("bug.automation_rules"))
