from flask import flash, redirect, request, session, url_for

from config import get_db_connection
from repositories.time_repository import (
    get_time_entries,
    get_total_time_spent,
    log_time,
    update_time_estimate,
    update_time_remaining,
)
from utils.decorators import login_required


def register_time_routes(bp):
    @bp.route("/bugs/<int:bug_id>/log-time", methods=["POST"])
    @login_required
    def log_time_route(bug_id):
        hours_spent = request.form.get("hours_spent", "")
        description = request.form.get("description", "").strip()

        if not hours_spent:
            flash("Hours spent is required.", "error")
            return redirect(url_for("bug.bug_details", bug_id=bug_id))

        try:
            hours_spent = float(hours_spent)
            if hours_spent <= 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Hours spent must be a positive number.", "error")
            return redirect(url_for("bug.bug_details", bug_id=bug_id))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            log_time(cursor, bug_id, session["user_id"], hours_spent, description or None)
            conn.commit()
            flash(f"Logged {hours_spent}h on this issue.", "success")
        except Exception:
            conn.rollback()
            flash("Could not log time.", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    @bp.route("/bugs/<int:bug_id>/update-estimate", methods=["POST"])
    @login_required
    def update_time_estimate_route(bug_id):
        estimate = request.form.get("time_estimate", "")

        try:
            estimate = float(estimate) if estimate else None
            if estimate is not None and estimate < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Estimate must be a non-negative number.", "error")
            return redirect(url_for("bug.bug_details", bug_id=bug_id))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            update_time_estimate(cursor, bug_id, estimate)
            conn.commit()
            flash("Time estimate updated.", "success")
        except Exception:
            conn.rollback()
            flash("Could not update estimate.", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    @bp.route("/bugs/<int:bug_id>/update-remaining", methods=["POST"])
    @login_required
    def update_time_remaining_route(bug_id):
        remaining = request.form.get("time_remaining", "")

        try:
            remaining = float(remaining) if remaining else None
            if remaining is not None and remaining < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Remaining time must be a non-negative number.", "error")
            return redirect(url_for("bug.bug_details", bug_id=bug_id))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            update_time_remaining(cursor, bug_id, remaining)
            conn.commit()
            flash("Remaining time updated.", "success")
        except Exception:
            conn.rollback()
            flash("Could not update remaining time.", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("bug.bug_details", bug_id=bug_id))
