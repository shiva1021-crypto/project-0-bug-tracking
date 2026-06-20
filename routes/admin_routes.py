from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error
from werkzeug.security import generate_password_hash

from config import get_db_connection
from routes.auth_routes import VALID_ROLES
from utils.decorators import role_required
from utils.notifications import queue_email


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/users")
@role_required("admin")
def users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, full_name, email, role, created_at
        FROM users
        WHERE organization_id = %s
        ORDER BY created_at DESC
        """,
        (session["organization_id"],),
    )
    all_users = cursor.fetchall()
    cursor.execute(
        """
        SELECT id, full_name, email, requested_role, verified_at, requested_at
        FROM registration_requests
        WHERE organization_id = %s AND status = 'pending'
        ORDER BY requested_at
        """,
        (session["organization_id"],),
    )
    pending_registrations = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template(
        "users.html",
        users=all_users,
        roles=sorted(VALID_ROLES),
        pending_registrations=pending_registrations,
        require_email_verification=current_app.config["REQUIRE_EMAIL_VERIFICATION"],
    )


@admin_bp.route("/admin/registrations/<int:request_id>/approve", methods=["POST"])
@role_required("admin")
def approve_registration(request_id):
    role = request.form.get("role", "tester")
    if role not in VALID_ROLES:
        flash("Select a valid role.", "error")
        return redirect(url_for("admin.users"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    registration = None
    approved = False
    try:
        cursor.execute(
            """
            SELECT * FROM registration_requests
            WHERE id = %s AND organization_id = %s AND status = 'pending'
            FOR UPDATE
            """,
            (request_id, session["organization_id"]),
        )
        registration = cursor.fetchone()
        if not registration:
            flash("Registration request is no longer pending.", "error")
            return redirect(url_for("admin.users"))
        if current_app.config["REQUIRE_EMAIL_VERIFICATION"] and not registration["verified_at"]:
            flash("The requester must verify their email before approval.", "error")
            return redirect(url_for("admin.users"))

        cursor.execute(
            """
            INSERT INTO users (organization_id, full_name, email, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                session["organization_id"],
                registration["full_name"],
                registration["email"],
                registration["password_hash"],
                role,
            ),
        )
        cursor.execute(
            """
            UPDATE registration_requests
            SET status = 'approved', requested_role = %s,
                reviewed_at = NOW(), reviewed_by = %s
            WHERE id = %s
            """,
            (role, session["user_id"], request_id),
        )
        conn.commit()
        approved = True
    except Error as exc:
        conn.rollback()
        if exc.errno == 1062:
            flash("An account with that email already exists.", "error")
        else:
            raise
    finally:
        cursor.close()
        conn.close()

    if approved:
        queue_email(
            registration["email"],
            "Your IssueFlow access was approved",
            "Your registration request was approved. You can now sign in.",
        )
        flash("Registration approved.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/admin/registrations/<int:request_id>/reject", methods=["POST"])
@role_required("admin")
def reject_registration(request_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT email FROM registration_requests
        WHERE id = %s AND organization_id = %s AND status = 'pending'
        """,
        (request_id, session["organization_id"]),
    )
    registration = cursor.fetchone()
    if registration:
        cursor.execute(
            """
            UPDATE registration_requests
            SET status = 'rejected', reviewed_at = NOW(), reviewed_by = %s
            WHERE id = %s
            """,
            (session["user_id"], request_id),
        )
        conn.commit()
    cursor.close()
    conn.close()

    if registration:
        queue_email(
            registration["email"],
            "Your IssueFlow access request",
            "Your registration request was not approved. Contact your organization administrator for help.",
        )
        flash("Registration rejected.", "success")
    else:
        flash("Registration request is no longer pending.", "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/admin/users/create", methods=["POST"])
@role_required("admin")
def create_user():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "tester")

    if not full_name or not email or len(password) < 8 or role not in VALID_ROLES:
        flash("Please provide valid user details. Password must be at least 8 characters.", "error")
        return redirect(url_for("admin.users"))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (organization_id, full_name, email, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                session["organization_id"],
                full_name,
                email,
                generate_password_hash(password),
                role,
            ),
        )
        conn.commit()
        flash("User created successfully.", "success")
    except Exception:
        conn.rollback()
        flash("User creation failed. The email may already exist.", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("admin.users"))


@admin_bp.route("/admin/users/<int:user_id>/role", methods=["POST"])
@role_required("admin")
def update_user_role(user_id):
    role = request.form.get("role", "")
    if role not in VALID_ROLES:
        flash("Invalid role selected.", "error")
        return redirect(url_for("admin.users"))

    if user_id == session["user_id"] and role != "admin":
        flash("You cannot remove your own admin access.", "error")
        return redirect(url_for("admin.users"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET role = %s WHERE id = %s AND organization_id = %s",
        (role, user_id, session["organization_id"]),
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash("User role updated.", "success")
    return redirect(url_for("admin.users"))
