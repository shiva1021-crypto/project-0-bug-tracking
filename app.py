import os

from flask import Flask, abort, render_template, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config, DatabaseUnavailable, db_cursor
from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.automation_routes import register_automation_routes
from routes.bug_blueprint import bug_bp
from routes.bug_routes import register_bug_routes
from routes.custom_field_routes import register_custom_field_routes
from routes.dashboard_routes import register_dashboard_routes
from routes.link_routes import register_link_routes
from routes.search_routes import register_search_routes
from routes.sprint_routes import register_sprint_routes
from routes.time_routes import register_time_routes
from routes.version_routes import register_version_routes
from routes.workflow_routes import register_workflow_routes
from routes.report_routes import report_bp
from routes.project_routes import project_bp
from utils.decorators import login_required
from utils.notifications import start_notification_worker
from utils.security import csrf_token, set_security_headers, validate_csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    if app.config["TRUST_PROXY_HEADERS"]:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config["PROXY_FIX_X_FOR"],
            x_proto=app.config["PROXY_FIX_X_PROTO"],
            x_host=app.config["PROXY_FIX_X_HOST"],
            x_prefix=app.config["PROXY_FIX_X_PREFIX"],
        )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    app.before_request(validate_csrf)
    app.after_request(set_security_headers)

    register_automation_routes(bug_bp)
    register_bug_routes(bug_bp)
    register_custom_field_routes(bug_bp)
    register_dashboard_routes(bug_bp)
    register_link_routes(bug_bp)
    register_search_routes(bug_bp)
    register_sprint_routes(bug_bp)
    register_time_routes(bug_bp)
    register_version_routes(bug_bp)
    register_workflow_routes(bug_bp)

    app.register_blueprint(auth_bp)
    app.register_blueprint(bug_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(project_bp)

    if (
        app.config["NOTIFICATION_WORKER_ENABLED"]
        and os.getenv("SMTP_HOST")
        and os.getenv("SMTP_FROM")
    ):
        start_notification_worker()

    @app.context_processor
    def inject_user():
        return {
            "current_user_id": session.get("user_id"),
            "current_user_name": session.get("full_name"),
            "current_user_role": session.get("role"),
            "current_organization_id": session.get("organization_id"),
            "current_organization_name": session.get("organization_name"),
            "csrf_token": csrf_token,
            "show_demo_credentials": app.config["SHOW_DEMO_CREDENTIALS"],
        }

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/uploads/bug_screenshots/<path:filename>")
    @login_required
    def uploaded_file(filename):
        with db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM bugs
                WHERE screenshot_path = %s AND organization_id = %s
                LIMIT 1
                """,
                (filename, session["organization_id"]),
            )
            if not cursor.fetchone():
                abort(404)
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.errorhandler(DatabaseUnavailable)
    def database_unavailable(error):
        return render_template("database_error.html", error=error.original_error), 503

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
