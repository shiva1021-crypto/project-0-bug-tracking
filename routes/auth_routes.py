import hashlib
import secrets
from datetime import datetime, timezone

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

from config import db_cursor, get_db_connection
from utils.decorators import login_required
from utils.notifications import queue_email
from utils.rate_limit import rate_limit_exceeded


auth_bp = Blueprint("auth", __name__)

VALID_ROLES = {"admin", "project_manager", "developer", "tester"}


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        organization_name = request.form.get("organization_name", "").strip()

        if request.form.get("website", "").strip():
            flash("Your access request has been submitted for review.", "success")
            return redirect(url_for("auth.login"))

        if rate_limit_exceeded(
            "register_ip", request.remote_addr, limit=5, window_seconds=3600
        ):
            flash("Too many registration attempts. Please try again later.", "error")
            return redirect(url_for("auth.register"))

        if not full_name or not email or not organization_name or len(password) < 8:
            flash("Please provide valid registration details.", "error")
            return redirect(url_for("auth.register"))

        admin_emails = []
        verification_token = None
        try:
            with db_cursor(dictionary=True, commit=True) as cursor:
                cursor.execute("SELECT id FROM organizations WHERE name = %s", (organization_name,))
                organization = cursor.fetchone()
                if not organization:
                    flash("Organization not found. Ask your administrator for the exact name.", "error")
                    return redirect(url_for("auth.register"))

                cursor.execute(
                    """
                    SELECT id FROM users WHERE email = %s
                    """,
                    (email,),
                )
                if cursor.fetchone():
                    flash("An account with that email already exists.", "error")
                    return redirect(url_for("auth.login"))

                cursor.execute(
                    """
                    SELECT id FROM registration_requests
                    WHERE organization_id = %s AND email = %s AND status = 'pending'
                    """,
                    (organization["id"], email),
                )
                if cursor.fetchone():
                    flash("Your access request is already awaiting review.", "error")
                    return redirect(url_for("auth.login"))

                if current_app.config["REQUIRE_EMAIL_VERIFICATION"]:
                    verification_token = secrets.token_urlsafe(32)
                    verification_token_hash = hashlib.sha256(verification_token.encode()).hexdigest()
                    verified_at = None
                else:
                    verification_token_hash = None
                    verified_at = datetime.now(timezone.utc).replace(tzinfo=None)

                cursor.execute(
                    """
                    INSERT INTO registration_requests
                        (organization_id, full_name, email, password_hash, requester_ip,
                         verification_token_hash, verified_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        organization["id"],
                        full_name,
                        email,
                        generate_password_hash(password),
                        request.remote_addr,
                        verification_token_hash,
                        verified_at,
                    ),
                )
                cursor.execute(
                    "SELECT email FROM users WHERE organization_id = %s AND role = 'admin'",
                    (organization["id"],),
                )
                admin_emails = [row["email"] for row in cursor.fetchall()]

            if verification_token:
                verification_url = url_for(
                    "auth.verify_registration", token=verification_token, _external=True
                )
                queue_email(
                    email,
                    "Verify your IssueFlow access request",
                    f"Verify your email before an administrator can approve access:\n\n{verification_url}",
                )
                flash("Access request submitted. Check your email to verify it before administrator approval.", "success")
            else:
                for admin_email in admin_emails:
                    queue_email(
                        admin_email,
                        "New IssueFlow access request",
                        f"{full_name} ({email}) requested access to {organization_name}.",
                    )
                flash("Access request submitted. An administrator must approve it before login.", "success")
            return redirect(url_for("auth.login"))
        except Error:
            flash("Registration request failed. Please try again.", "error")

    return render_template("register.html")


@auth_bp.route("/register/verify/<token>")
def verify_registration(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    admin_emails = []
    registration = None
    with db_cursor(dictionary=True, commit=True) as cursor:
        cursor.execute(
            """
            SELECT id, organization_id, full_name, email
            FROM registration_requests
            WHERE verification_token_hash = %s AND status = 'pending' AND verified_at IS NULL
              AND requested_at >= NOW() - INTERVAL 24 HOUR
            """,
            (token_hash,),
        )
        registration = cursor.fetchone()
        if registration:
            cursor.execute(
                """
                UPDATE registration_requests
                SET verified_at = NOW(), verification_token_hash = NULL
                WHERE id = %s
                """,
                (registration["id"],),
            )
            cursor.execute(
                "SELECT email FROM users WHERE organization_id = %s AND role = 'admin'",
                (registration["organization_id"],),
            )
            admin_emails = [row["email"] for row in cursor.fetchall()]

    if not registration:
        flash("This verification link is invalid or has already been used.", "error")
        return redirect(url_for("auth.login"))

    for admin_email in admin_emails:
        queue_email(
            admin_email,
            "Verified IssueFlow access request",
            f"{registration['full_name']} ({registration['email']}) is ready for approval.",
        )
    flash("Email verified. An administrator can now approve your access request.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        login_limited = rate_limit_exceeded(
            "login_ip", request.remote_addr, limit=50, window_seconds=300
        ) or rate_limit_exceeded("login_account", email, limit=10, window_seconds=300)
        if login_limited:
            flash("Too many login attempts. Please wait before trying again.", "error")
            return render_template("login.html"), 429

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
