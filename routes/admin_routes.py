from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from config import get_db_connection
from routes.auth_routes import VALID_ROLES
from utils.decorators import role_required


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
    cursor.close()
    conn.close()
    return render_template("users.html", users=all_users, roles=sorted(VALID_ROLES))


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
