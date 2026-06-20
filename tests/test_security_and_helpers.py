import io
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask, session

import config
from app import app as application
from models import bug_model
from routes.bug_routes import (
    detected_image_extension,
    normalized_labels,
    parsed_due_date,
    parsed_story_points,
)
from routes.report_routes import safe_csv_cell
from utils.decorators import role_required
from utils.pagination import pagination_values


class FakeCursor:
    def __init__(self, row=None):
        self.row = row
        self.query = None
        self.params = None

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchone(self):
        return self.row

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, **_kwargs):
        return self._cursor

    def close(self):
        pass


class SecurityAndHelperTests(unittest.TestCase):
    def test_role_is_refreshed_before_authorization(self):
        app = Flask(__name__)
        app.secret_key = "test-secret"
        app.add_url_rule("/login", endpoint="auth.login", view_func=lambda: "login")
        app.add_url_rule(
            "/dashboard", endpoint="bug.dashboard", view_func=lambda: "dashboard"
        )
        cursor = FakeCursor(
            {
                "full_name": "Changed User",
                "role": "tester",
                "organization_name": "Example",
            }
        )

        @role_required("admin")
        def protected():
            return "allowed"

        with app.test_request_context("/protected"):
            session.update(user_id=7, organization_id=3, role="admin")
            with patch(
                "utils.decorators.get_db_connection",
                return_value=FakeConnection(cursor),
            ):
                response = protected()

            self.assertEqual(response.status_code, 302)
            self.assertEqual(session["role"], "tester")
            self.assertEqual(cursor.params, (7, 3))

    def test_screenshot_route_requires_login(self):
        client = application.test_client()
        response = client.get("/uploads/bug_screenshots/example.png")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_csv_formula_prefixes_are_neutralized(self):
        for value in ("=1+1", "+cmd", "-2+3", "@SUM(A1:A2)", "\tformula"):
            with self.subTest(value=value):
                self.assertTrue(safe_csv_cell(value).startswith("'"))
        self.assertEqual(safe_csv_cell("Normal title"), "Normal title")

    def test_real_image_signature_is_detected(self):
        png = SimpleNamespace(stream=io.BytesIO(b"\x89PNG\r\n\x1a\nrest"))
        fake = SimpleNamespace(stream=io.BytesIO(b"not an image"))
        self.assertEqual(detected_image_extension(png), "png")
        self.assertIsNone(detected_image_extension(fake))

    def test_jira_style_issue_metadata_is_normalized(self):
        self.assertEqual(
            normalized_labels("Frontend, customer impact, frontend"),
            "frontend,customer-impact",
        )
        self.assertEqual(parsed_story_points("8"), 8)
        self.assertEqual(str(parsed_due_date("2026-07-15")), "2026-07-15")
        with self.assertRaises(ValueError):
            parsed_story_points("101")

    def test_production_rejects_missing_secret(self):
        with patch.dict(
            os.environ, {"APP_ENV": "production", "SECRET_KEY": ""}, clear=False
        ):
            with self.assertRaises(RuntimeError):
                config._secret_key()

    def test_bug_model_scopes_query_to_organization(self):
        cursor = FakeCursor({"id": 5})
        with patch(
            "models.bug_model.get_db_connection",
            return_value=FakeConnection(cursor),
        ):
            bug_model.get_bug_by_id(5, 12)

        self.assertIn("organization_id", cursor.query)
        self.assertEqual(cursor.params, (5, 12))

    def test_pagination_clamps_invalid_and_excess_pages(self):
        self.assertEqual(pagination_values("bad", 45, 20)["page"], 1)
        values = pagination_values(99, 45, 20)
        self.assertEqual(values["page"], 3)
        self.assertEqual(values["total_pages"], 3)

    def test_logout_only_accepts_post(self):
        logout_rule = next(
            rule for rule in application.url_map.iter_rules() if rule.endpoint == "auth.logout"
        )
        self.assertIn("POST", logout_rule.methods)
        self.assertNotIn("GET", logout_rule.methods)

    def test_jira_style_routes_are_registered(self):
        endpoints = {rule.endpoint for rule in application.url_map.iter_rules()}
        self.assertIn("project.projects", endpoints)
        self.assertIn("project.board", endpoints)
        self.assertIn("bug.toggle_watch", endpoints)

    def test_premium_landing_page_renders(self):
        response = application.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Turn complex work into", response.data)
        self.assertIn(b"Kanban board preview", response.data)


if __name__ == "__main__":
    unittest.main()
