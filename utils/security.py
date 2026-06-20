import secrets

from flask import abort, current_app, request, session


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf():
    if current_app.config.get("TESTING"):
        return

    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    sent_token = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
    if not sent_token or not secrets.compare_digest(sent_token, session.get("_csrf_token", "")):
        abort(400, description="Invalid or missing CSRF token.")


def set_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self';",
    )
    if current_app.config.get("APP_ENV") == "production" and request.is_secure:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response
