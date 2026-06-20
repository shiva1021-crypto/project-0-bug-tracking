# Project Report: Software Bug Tracking and Reporting Tool

## 1. Introduction

The Software Bug Tracking and Reporting Tool is a web-based application for software defect and work management. It supports project-scoped issues, assignment, a Kanban workflow, Jira-style work types and parent relationships, comments, watchers, and reports.

The application uses Python Flask for backend development, MySQL for database storage, and HTML, CSS, and JavaScript for the frontend interface.

## 2. Aim

The aim of this project is to create a structured bug tracking system that helps users manage software defects from the time they are reported until they are resolved or closed.

## 3. Objectives

- To create secure user registration and login.
- To implement role-based access control.
- To allow testers to report software bugs.
- To allow project managers and administrators to assign bugs to developers.
- To allow developers to update bug progress.
- To allow users to add comments to bug reports.
- To provide dashboard statistics for bug monitoring.
- To provide search, filtering, and reporting features.
- To store all user and bug information in a MySQL database.
- To create a clean and responsive user interface.

## 4. Technology Used

| Technology | Purpose |
| --- | --- |
| Python | Backend programming language |
| Flask | Web framework and routing |
| MySQL | Database management system |
| mysql-connector-python | Python to MySQL connection |
| python-dotenv | Environment variable management |
| Werkzeug | Password hashing |
| HTML | Page structure |
| CSS | Page styling and responsiveness |
| JavaScript | Client-side validation and navigation behavior |

## 5. System Users

The system includes four user roles:

- **Admin:** Can access all major features, manage users, assign bugs, view reports, and manage project data.
- **Project Manager:** Can view bugs, assign bugs to developers, and view reports.
- **Developer:** Can view bugs, comment on bugs, and update the status of bugs assigned to them.
- **Tester:** Can report bugs, view bugs, and add comments.

## 6. Functional Requirements

- The system must allow users to register and login.
- The system must store passwords securely using hashing.
- The system must support role-based access.
- The system must allow users to report bugs.
- The system must allow authorized users to view bugs.
- The system must allow admins and project managers to assign bugs.
- The system must allow only the assigned developer to update assigned bug status.
- The system must allow users to comment on bugs.
- The system must provide dashboard statistics.
- The system must provide report filters.
- The system must support screenshot uploads.
- The system must support CSV export for reports.
- The system must isolate data by organization/tenant.
- The system must protect POST requests with CSRF tokens.
- The system must support a production-style WSGI entry point.

## 7. Non-Functional Requirements

- The system should be easy to use.
- The interface should be responsive.
- The system should validate user input.
- The system should protect restricted pages.
- The system should use environment variables for sensitive configuration.
- The system should display clear success and error messages.

## 8. Database Design

The database is named `bug_tracking_db`.

### users table

Stores user accounts and role information.

Fields:

- `id`
- `full_name`
- `email`
- `password_hash`
- `role`
- `created_at`

### bugs table

Stores issue details, including project membership and Jira-style planning metadata.

Fields:

- `id`
- `project_id`
- `issue_key`
- `issue_type`
- `parent_id`
- `title`
- `description`
- `reproduction_steps`
- `priority`
- `severity`
- `status`
- `reporter_id`
- `assigned_to`
- `screenshot_path`
- `created_at`
- `updated_at`
- `labels`
- `story_points`
- `due_date`

### projects table

Stores organization-scoped projects, short keys, descriptions, and issue-number counters.

### issue_watchers table

Stores users who watch an issue for updates.

### comments table

Stores comments for bug reports.

Fields:

- `id`
- `bug_id`
- `user_id`
- `comment`
- `created_at`

### bug_history table

Stores history of bug changes.

Fields:

- `id`
- `bug_id`
- `changed_by`
- `old_status`
- `new_status`
- `old_assigned_to`
- `new_assigned_to`
- `change_note`
- `changed_at`

## 9. Main Application Modules

### app.py

Creates the Flask application, registers route blueprints, configures uploads, injects session user data into templates, and handles database connection errors.

### config.py

Loads environment variables and creates the MySQL database connection.

### routes/auth_routes.py

Handles registration, login, logout, password hashing, and session creation.

### routes/bug_routes.py

Handles dashboard data, bug creation, bug listing, bug details, bug editing, assignment, status updates, comments, screenshot uploads, and audit history.

### routes/report_routes.py

Handles report filters and CSV export.

### routes/admin_routes.py

Handles admin user management and role updates.

### routes/project_routes.py

Handles project creation, project listing, filtering, and the Kanban board.

### utils/decorators.py

Provides `login_required` and `role_required` decorators to protect routes.

## 10. Role Permission Table

| Feature | Admin | Project Manager | Developer | Tester |
| --- | --- | --- | --- | --- |
| Register/Login | Yes | Yes | Yes | Yes |
| View Dashboard | Yes | Yes | Yes | Yes |
| Create Issue | Yes | Yes | Yes | Yes |
| View Bugs | Yes | Yes | Yes | Yes |
| Assign Bug | Yes | Yes | No | No |
| Update Bug Status | No | No | Assigned developer only | No |
| Add Comment | Yes | Yes | Yes | Yes |
| View Reports | Yes | Yes | No | No |
| Manage Users | Yes | No | No | No |

## 11. How to Run the Project

Open PowerShell in the project folder:

```powershell
cd "D:\mybi doc\project 0"
```

Install requirements:

```powershell
venv\Scripts\activate
pip install -r requirements.txt
```

Check MySQL:

```powershell
venv\Scripts\python check_db.py
```

Initialize the database:

```powershell
venv\Scripts\python init_db.py
```

Run Flask:

```powershell
venv\Scripts\python run_dev.py
```

Open:

```text
http://127.0.0.1:5000
```

## 12. Testing

The following tests should be performed:

- Register an admin account.
- Register a tester account.
- Register a developer account.
- Register a project manager account.
- Login with valid credentials.
- Try login with an invalid password.
- Create a bug as a tester.
- Assign the bug as admin or project manager.
- Update bug status as the assigned developer.
- Check that other developers, testers, admins, and project managers cannot directly update bug status.
- Add a comment to the bug.
- Upload a screenshot.
- Filter bugs by status, priority, severity, and developer.
- Generate a report.
- Export the report as CSV.
- Check that restricted pages are blocked for unauthorized users.

## 13. Security Features

- Passwords are stored using password hashing.
- Routes are protected using login and role decorators.
- Database credentials are stored in `.env`.
- File uploads are restricted to image file types.
- Server-side validation is used before database insertion.
- CSRF validation protects POST forms.
- Secure response headers reduce common browser-side risks.
- Organization-scoped queries isolate tenant data.
- Pooled database connections improve connection handling.

## 14. Conclusion

The system now provides a focused Jira-style workflow with projects, issue keys, multiple work types, parent-child relationships, Kanban tracking, labels, estimates, due dates, watchers, assignment, comments, reports, and audit history while retaining tenant isolation and role-based security.

## 15. Future Enhancements

- Add richer email templates.
- Add sprint planning and backlog ranking.
- Add direct GitHub API synchronization.
- Add production deployment support with HTTPS and managed secrets.
