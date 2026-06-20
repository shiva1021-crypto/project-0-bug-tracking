import unittest
from uuid import uuid4

from werkzeug.security import generate_password_hash

from app import app
from config import DatabaseUnavailable, get_db_connection


class DatabaseWorkflowIntegrationTests(unittest.TestCase):
    def test_registration_hierarchy_watchers_and_board_pagination(self):
        token = uuid4().hex[:10]
        organization_name = f"Integration {token}"
        admin_email = f"admin-{token}@integration.test"
        applicant_email = f"applicant-{token}@integration.test"
        password = "IntegrationPass123!"
        organization_id = None
        original_testing = app.config["TESTING"]
        original_page_size = app.config["BOARD_PAGE_SIZE"]
        original_verification = app.config["REQUIRE_EMAIL_VERIFICATION"]
        app.config.update(
            TESTING=True, BOARD_PAGE_SIZE=2, REQUIRE_EMAIL_VERIFICATION=False
        )

        try:
            connection = get_db_connection()
        except DatabaseUnavailable as exc:
            app.config["TESTING"] = original_testing
            app.config["BOARD_PAGE_SIZE"] = original_page_size
            app.config["REQUIRE_EMAIL_VERIFICATION"] = original_verification
            self.skipTest(f"MySQL integration database is unavailable: {exc}")
        cursor = connection.cursor()
        try:
            cursor.execute("INSERT INTO organizations (name) VALUES (%s)", (organization_name,))
            organization_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO projects (organization_id, name, project_key, description)
                VALUES (%s, %s, %s, %s)
                """,
                (organization_id, "Integration Project", f"I{token[:5].upper()}", "Temporary integration project"),
            )
            project_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO users (organization_id, full_name, email, password_hash, role)
                VALUES (%s, %s, %s, %s, 'admin')
                """,
                (organization_id, "Integration Admin", admin_email, generate_password_hash(password)),
            )
            connection.commit()
            connection.autocommit = True

            applicant = app.test_client()
            response = applicant.post(
                "/register",
                data={
                    "full_name": "Integration Applicant",
                    "email": applicant_email,
                    "password": password,
                    "organization_name": organization_name,
                },
            )
            self.assertEqual(response.status_code, 302)

            connection.commit()
            cursor.execute(
                "SELECT id, status FROM registration_requests WHERE organization_id = %s AND email = %s",
                (organization_id, applicant_email),
            )
            request_id, status = cursor.fetchone()
            self.assertEqual(status, "pending")

            admin = app.test_client()
            self.assertEqual(
                admin.post("/login", data={"email": admin_email, "password": password}).status_code,
                302,
            )
            self.assertEqual(
                admin.post(
                    f"/admin/registrations/{request_id}/approve",
                    data={"role": "developer"},
                ).status_code,
                302,
            )
            self.assertEqual(
                applicant.post("/login", data={"email": applicant_email, "password": password}).status_code,
                302,
            )

            role_accounts = (
                ("Integration Manager", f"manager-{token}@integration.test", "project_manager"),
                ("Integration Tester", f"tester-{token}@integration.test", "tester"),
                ("Second Developer", f"developer-{token}@integration.test", "developer"),
            )
            for full_name, email, role in role_accounts:
                self.assertEqual(
                    admin.post(
                        "/admin/users/create",
                        data={
                            "full_name": full_name,
                            "email": email,
                            "password": password,
                            "role": role,
                        },
                    ).status_code,
                    302,
                )

            connection.commit()
            cursor.execute(
                "SELECT id FROM users WHERE organization_id = %s AND email = %s",
                (organization_id, applicant_email),
            )
            applicant_id = cursor.fetchone()[0]

            manager = app.test_client()
            tester = app.test_client()
            second_developer = app.test_client()
            for client, email in (
                (manager, role_accounts[0][1]),
                (tester, role_accounts[1][1]),
                (second_developer, role_accounts[2][1]),
            ):
                self.assertEqual(
                    client.post("/login", data={"email": email, "password": password}).status_code,
                    302,
                )

            self.assertEqual(admin.get("/admin/users").status_code, 200)
            self.assertEqual(manager.get("/admin/users").status_code, 302)
            self.assertEqual(tester.get("/admin/users").status_code, 302)
            self.assertEqual(applicant.get("/admin/users").status_code, 302)

            def create_issue(issue_type, title, parent_id=""):
                result = admin.post(
                    "/bugs/add",
                    data={
                        "project_id": str(project_id),
                        "issue_type": issue_type,
                        "parent_id": str(parent_id) if parent_id else "",
                        "title": title,
                        "description": "Integration test issue",
                        "category": "Backend",
                        "priority": "High",
                        "severity": "Major",
                    },
                )
                self.assertEqual(result.status_code, 302)
                return int(result.headers["Location"].rstrip("/").split("/")[-1])

            epic_id = create_issue("Epic", "Integration epic")
            story_id = create_issue("Story", "Integration story", epic_id)
            subtask_id = create_issue("Subtask", "Integration subtask", story_id)
            self.assertTrue(subtask_id)

            denied_assignment = tester.post(
                f"/bugs/{story_id}/assign",
                data={"developer_id": str(applicant_id)},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            self.assertEqual(denied_assignment.status_code, 403)
            self.assertFalse(denied_assignment.get_json()["ok"])

            allowed_assignment = manager.post(
                f"/bugs/{story_id}/assign", data={"developer_id": str(applicant_id)}
            )
            self.assertEqual(allowed_assignment.status_code, 302)

            denied_status = second_developer.post(
                f"/bugs/{story_id}/status",
                data={"status": "Resolved"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            self.assertEqual(denied_status.status_code, 403)
            self.assertFalse(denied_status.get_json()["ok"])
            connection.commit()
            cursor.execute("SELECT status FROM bugs WHERE id = %s", (story_id,))
            self.assertEqual(cursor.fetchone()[0], "In Progress")

            allowed_status = applicant.post(
                f"/bugs/{story_id}/status",
                data={"status": "Resolved"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            self.assertEqual(allowed_status.status_code, 200)
            self.assertTrue(allowed_status.get_json()["ok"])
            connection.commit()
            cursor.execute("SELECT status FROM bugs WHERE id = %s", (story_id,))
            self.assertEqual(cursor.fetchone()[0], "Resolved")

            connection.commit()
            cursor.execute("SELECT COUNT(*) FROM bugs WHERE organization_id = %s", (organization_id,))
            before_invalid = cursor.fetchone()[0]
            invalid = admin.post(
                "/bugs/add",
                data={
                    "project_id": str(project_id),
                    "issue_type": "Story",
                    "parent_id": str(story_id),
                    "title": "Invalid hierarchy",
                    "description": "Must not be inserted",
                    "category": "Backend",
                    "priority": "High",
                    "severity": "Major",
                },
            )
            self.assertEqual(invalid.status_code, 302)
            connection.commit()
            cursor.execute("SELECT COUNT(*) FROM bugs WHERE organization_id = %s", (organization_id,))
            self.assertEqual(cursor.fetchone()[0], before_invalid)

            watch_response = admin.post(f"/bugs/{story_id}/watch", data={"action": "watch"})
            self.assertEqual(watch_response.status_code, 302)
            connection.commit()
            cursor.execute(
                "SELECT COUNT(*) FROM issue_watchers WHERE bug_id = %s",
                (story_id,),
            )
            self.assertEqual(cursor.fetchone()[0], 1)

            board = admin.get(f"/board?project={project_id}&page=2")
            self.assertEqual(board.status_code, 200)
            self.assertIn(b"Page 2 of 2", board.data)
            self.assertEqual(board.data.count(b'class="kanban-card"'), 1)
        finally:
            app.config["TESTING"] = original_testing
            app.config["BOARD_PAGE_SIZE"] = original_page_size
            app.config["REQUIRE_EMAIL_VERIFICATION"] = original_verification
            if organization_id is not None:
                cursor.execute(
                    "DELETE FROM email_outbox WHERE recipient LIKE %s",
                    (f"%-{token}@integration.test",),
                )
                cursor.execute("DELETE FROM organizations WHERE id = %s", (organization_id,))
                connection.commit()
            cursor.close()
            connection.close()


if __name__ == "__main__":
    unittest.main()
