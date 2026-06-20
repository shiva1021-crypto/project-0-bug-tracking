import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import db_cursor, get_db_connection
from utils.decorators import login_required


auth_bp = Blueprint("auth", __name__)

VALID_ROLES = {"admin", "project_manager", "developer", "tester"}


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        organization_name = request.form.get("organization_name", "").strip()

        if not full_name or not email or not organization_name or len(password) < 8:
            flash("Please provide valid registration details.", "error")
            return redirect(url_for("auth.register"))

        try:
            with db_cursor(commit=True) as cursor:
                cursor.execute("SELECT id FROM organizations WHERE name = %s", (organization_name,))
                if cursor.fetchone():
                    flash("That organization already exists. Ask your admin to create your account.", "error")
                    return redirect(url_for("auth.register"))

                cursor.execute("INSERT INTO organizations (name) VALUES (%s)", (organization_name,))
                organization_id = cursor.lastrowid
                project_key = re.sub(r"[^A-Za-z0-9]", "", organization_name).upper()[:10]
                if len(project_key) < 2:
                    project_key = f"ORG{organization_id}"
                cursor.execute(
                    """
                    INSERT INTO projects (organization_id, name, project_key, description)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (organization_id, "General", project_key, "Default project"),
                )
                cursor.execute(
                    """
                    INSERT INTO users (organization_id, full_name, email, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (organization_id, full_name, email, generate_password_hash(password), "admin"),
                )
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("auth.login"))
        except Exception:
            flash("Email already exists or registration failed.", "error")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT users.*, organizations.name AS organization_name
            FROM users
            JOIN organizations ON users.organization_id = organizations.id
            WHERE users.email = %s
            """,
            (email,),
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            session["organization_id"] = user["organization_id"]
            session["organization_name"] = user["organization_name"]
            flash("Login successful.", "success")
            return redirect(url_for("bug.dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


def get_profile_data(user_id, organization_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id, organization_id, full_name, email, role, created_at
        FROM users
        WHERE id = %s AND organization_id = %s
        """,
        (user_id, organization_id),
    )
    profile_user = cursor.fetchone()

    if not profile_user:
        cursor.close()
        conn.close()
        return None

    cursor.execute(
        "SELECT COUNT(*) AS total FROM bugs WHERE reporter_id = %s AND organization_id = %s",
        (user_id, organization_id),
    )
    reported_count = cursor.fetchone()["total"]

    cursor.execute(
        "SELECT COUNT(*) AS total FROM bugs WHERE assigned_to = %s AND organization_id = %s",
        (user_id, organization_id),
    )
    assigned_count = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM bugs
        WHERE assigned_to = %s AND organization_id = %s AND status IN ('Open', 'In Progress')
        """,
        (user_id, organization_id),
    )
    active_assigned_count = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM comments
        JOIN bugs ON comments.bug_id = bugs.id
        WHERE comments.user_id = %s AND bugs.organization_id = %s
        """,
        (user_id, organization_id),
    )
    comment_count = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT id, title, priority, severity, status, created_at
        FROM bugs
        WHERE reporter_id = %s AND organization_id = %s
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (user_id, organization_id),
    )
    reported_bugs = cursor.fetchall()

    cursor.execute(
        """
        SELECT id, title, priority, severity, status, created_at
        FROM bugs
        WHERE assigned_to = %s AND organization_id = %s
        ORDER BY updated_at DESC
        LIMIT 5
        """,
        (user_id, organization_id),
    )
    assigned_bugs = cursor.fetchall()

    cursor.execute(
        """
        SELECT comments.comment, comments.created_at, bugs.id AS bug_id, bugs.title AS bug_title
        FROM comments
        JOIN bugs ON comments.bug_id = bugs.id
        WHERE comments.user_id = %s AND bugs.organization_id = %s
        ORDER BY comments.created_at DESC
        LIMIT 5
        """,
        (user_id, organization_id),
    )
    recent_comments = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "profile_user": profile_user,
        "stats": {
            "reported_count": reported_count,
            "assigned_count": assigned_count,
            "active_assigned_count": active_assigned_count,
            "comment_count": comment_count,
        },
        "reported_bugs": reported_bugs,
        "assigned_bugs": assigned_bugs,
        "recent_comments": recent_comments,
    }


@auth_bp.route("/profile")
@login_required
def profile():
    return redirect(url_for("auth.user_profile", user_id=session["user_id"]))


@auth_bp.route("/profile/<int:user_id>")
@login_required
def user_profile(user_id):
    data = get_profile_data(user_id, session["organization_id"])
    if not data:
        flash("User profile not found.", "error")
        return redirect(url_for("bug.dashboard"))

    can_view_email = user_id == session["user_id"] or session.get("role") == "admin"
    return render_template("profile.html", can_view_email=can_view_email, **data)
