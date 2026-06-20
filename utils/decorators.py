from functools import wraps

from flask import flash, redirect, session, url_for

from config import get_db_connection


def has_valid_session():
    return "user_id" in session and "organization_id" in session


def refresh_session_user():
    if not has_valid_session():
        return False

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT users.full_name, users.role, organizations.name AS organization_name
            FROM users
            JOIN organizations ON users.organization_id = organizations.id
            WHERE users.id = %s AND users.organization_id = %s
            """,
            (session["user_id"], session["organization_id"]),
        )
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not user:
        session.clear()
        return False

    session["full_name"] = user["full_name"]
    session["role"] = user["role"]
    session["organization_name"] = user["organization_name"]
    return True


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not refresh_session_user():
            session.clear()
            flash("Please login first.", "error")
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not refresh_session_user():
                session.clear()
                flash("Please login first.", "error")
                return redirect(url_for("auth.login"))

            if session.get("role") not in roles:
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for("bug.dashboard"))

            return func(*args, **kwargs)

        return wrapper

    return decorator


def can_update_bug_status(bug, user_id, role):
    return role == "developer" and bug.get("assigned_to") == user_id
