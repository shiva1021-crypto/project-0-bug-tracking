# Software Bug Tracking and Reporting Tool

## Project Description

The Software Bug Tracking and Reporting Tool is a web-based application designed to help software teams report, assign, monitor, and resolve software defects in a clear and structured way. The system supports role-based access for administrators, project managers, developers, and testers. Testers can submit detailed bug reports with information such as title, description, severity, priority, reproduction steps, and optional screenshots. Administrators and project managers can assign reported bugs to developers, while only the assigned developer can update the progress of a bug through statuses such as Open, In Progress, Resolved, and Closed.

The application is developed using HTML, CSS, JavaScript, Python Flask, and MySQL. It includes authentication, dashboard statistics, comments, search and filtering, report generation, CSV export, PDF print export, screenshot uploads, charts, category analytics, audit history, tenant isolation, optional email notifications, external issue links, dark mode, CSRF protection, secure headers, pooled database connections, production-style WSGI support, and admin user management. The main purpose of the project is to improve defect management and make the software maintenance process more organized and efficient.

## Objectives

### Essential Objectives

- Create user registration, login, and logout features.
- Store user passwords securely using password hashing.
- Implement role-based access for admin, project manager, developer, and tester users.
- Allow testers, admins, and project managers to report bugs.
- Store bug details such as title, description, priority, severity, status, reporter, assigned developer, and creation date.
- Allow authorized users to view reported bugs.
- Allow admins and project managers to assign bugs to developers.
- Allow only the assigned developer to update the status of a bug.
- Add search and filters for status, priority, severity, date, and assigned developer.
- Store all main data in a MySQL database.
- Validate user input before storing it.
- Protect restricted pages from unauthenticated users.
- Isolate users, bugs, reports, profiles, and admin actions by organization.
- Protect POST forms with CSRF tokens.

### Desirable Objectives

- Create dashboard statistics for total, open, resolved, closed, and critical bugs.
- Add comments on individual bug reports.
- Add screenshot upload functionality.
- Add reports based on status, priority, severity, assigned developer, and date range.
- Add client-side and server-side validation.
- Make the user interface responsive.
- Store timestamps for bug creation and updates.
- Display clear success and error messages.

### Optional Objectives Implemented

- CSV export for bug reports.
- Audit trail for bug creation, editing, assignment, and status updates.
- Admin user management for changing user roles.
- Tenant isolation through organization-scoped data.
- Production-style WSGI entry point with Waitress support.
- Secure response headers and safer session cookie defaults.
- Pooled MySQL connections.
- Report charts and category analytics.
- PDF export through the browser print-to-PDF flow.
- Optional SMTP email notifications for assignments and status updates.
- External issue URL support for GitHub or another issue tracker.
- Same-theme dark mode.

## Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python Flask
- **Database:** MySQL
- **Database Connector:** mysql-connector-python
- **Environment Configuration:** python-dotenv
- **Password Security:** Werkzeug password hashing

## Project Structure

```text
project 0/
|
|-- app.py
|-- config.py
|-- run_dev.py
|-- check_db.py
|-- init_db.py
|-- requirements.txt
|-- .env
|-- .env.example
|-- README.md
|
|-- database/
|   |-- bug_tracking.sql
|
|-- documentation/
|   |-- project_report.md
|   |-- project_description_checked.md
|
|-- models/
|   |-- __init__.py
|   |-- bug_model.py
|   |-- comment_model.py
|   |-- user_model.py
|
|-- routes/
|   |-- __init__.py
|   |-- admin_routes.py
|   |-- auth_routes.py
|   |-- bug_routes.py
|   |-- report_routes.py
|
|-- static/
|   |-- css/
|   |   |-- style.css
|   |-- js/
|       |-- script.js
|
|-- templates/
|   |-- base.html
|   |-- index.html
|   |-- login.html
|   |-- register.html
|   |-- dashboard.html
|   |-- add_bug.html
|   |-- view_bugs.html
|   |-- edit_bug.html
|   |-- bug_details.html
|   |-- reports.html
|   |-- users.html
|   |-- database_error.html
|
|-- uploads/
    |-- bug_screenshots/
```

## Database Tables

### users

Stores registered user information.

Main fields:

- `id`
- `full_name`
- `email`
- `password_hash`
- `role`
- `created_at`

### bugs

Stores reported bug information.

Main fields:

- `id`
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

### comments

Stores comments added to bug reports.

Main fields:

- `id`
- `bug_id`
- `user_id`
- `comment`
- `created_at`

### bug_history

Stores the audit trail for important bug changes.

Main fields:

- `id`
- `bug_id`
- `changed_by`
- `old_status`
- `new_status`
- `old_assigned_to`
- `new_assigned_to`
- `change_note`
- `changed_at`

### organizations

Stores tenant or organization records.

Main fields:

- `id`
- `name`
- `created_at`

## Role Permissions

| Feature | Admin | Project Manager | Developer | Tester |
| --- | --- | --- | --- | --- |
| Register/Login | Yes | Yes | Yes | Yes |
| View Dashboard | Yes | Yes | Yes | Yes |
| Report Bug | Yes | Yes | No | Yes |
| View Bugs | Yes | Yes | Yes | Yes |
| Assign Bug | Yes | Yes | No | No |
| Update Bug Status | No | No | Assigned developer only | No |
| Add Comment | Yes | Yes | Yes | Yes |
| View Reports | Yes | Yes | No | No |
| Manage Users | Yes | No | No | No |

## Status Update Isolation Rule

Bug status changes are isolated to the assigned developer. Admins and project managers can assign or reassign a bug, but they cannot directly submit the status update form. Other developers can view the bug, but they cannot update its status unless the bug is assigned to them.

## Tenant Isolation Rule

Each organization is treated as a separate tenant. Users can only see and manage bugs, comments, reports, profiles, developers, and user records that belong to their own organization. Public registration creates a new organization and makes the first user the admin. Additional users should be created from the admin user management page.

## Optional Production Settings

Email notifications are disabled until SMTP settings are added to `.env`. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, and `SMTP_USE_TLS` to enable assignment and status update emails.

Production requires `APP_ENV=production` and a random `SECRET_KEY` of at least 32 characters. Also enable secure cookies when the application is served over HTTPS:

```env
APP_ENV=production
SECRET_KEY=replace-with-a-long-random-secret
SESSION_COOKIE_SECURE=true
```

## Setup Instructions

### 1. Open the Project Folder

```powershell
cd "D:\mybi doc\project 0"
```

### 2. Create a Virtual Environment

```powershell
python -m venv venv
```

### 3. Activate the Virtual Environment

```powershell
venv\Scripts\activate
```

### 4. Install Requirements

```powershell
pip install -r requirements.txt
```

### 5. Configure `.env`

Update `.env` with your MySQL details:

```env
APP_ENV=development
SECRET_KEY=
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=bug_tracking_db
DB_POOL_SIZE=5
SESSION_COOKIE_SECURE=false
SESSION_LIFETIME_SECONDS=7200
PAGE_SIZE=20
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_USE_TLS=true
```

If your MySQL root user has no password, leave `DB_PASSWORD` empty:

```env
DB_PASSWORD=
```

### 6. Start MySQL

Start MySQL using MySQL Workbench, XAMPP, Laragon, or the Windows service.

To check the connection:

```powershell
venv\Scripts\python check_db.py
```

### 7. Create the Database and Tables

Run:

```powershell
venv\Scripts\python init_db.py
```

Then verify:

```powershell
venv\Scripts\python check_db.py
```

Expected output:

```text
OK: MySQL server is reachable.
OK: Database 'bug_tracking_db' is reachable.
```

### 8. Run the Flask Application

```powershell
venv\Scripts\python run_dev.py
```

Open the browser:

```text
http://127.0.0.1:5000
```

### Production-style local run on Windows

For a production-style WSGI server on Windows, install requirements and run:

```powershell
venv\Scripts\waitress-serve --listen=127.0.0.1:8000 wsgi:application
```

Open:

```text
http://127.0.0.1:8000
```

## MySQL Workbench Queries

To view the database in MySQL Workbench, open a query tab and run:

```sql
SHOW DATABASES;
USE bug_tracking_db;
SHOW TABLES;
```

To view table data:

```sql
SELECT * FROM users;
SELECT * FROM bugs;
SELECT * FROM comments;
SELECT * FROM bug_history;
```

## Application Workflow

1. Register users with different roles.
2. Login as a tester and report a bug.
3. Login as an admin or project manager and assign the bug to a developer.
4. Login as the assigned developer and update the bug status.
5. Confirm that other users cannot update that bug status.
5. Add comments on the bug detail page.
6. View dashboard statistics.
7. Generate filtered reports.
8. Export report data as CSV.

## Important Routes

| URL | Purpose |
| --- | --- |
| `/` | Home page |
| `/register` | User registration |
| `/login` | User login |
| `/logout` | User logout |
| `/profile` | Logged-in user's profile |
| `/profile/<id>` | View a user's profile and bug activity |
| `/dashboard` | Dashboard statistics |
| `/bugs` | View, search, and filter bugs |
| `/bugs/add` | Report a new bug |
| `/bugs/<id>` | View bug details |
| `/bugs/<id>/edit` | Edit a bug |
| `/reports` | View reports and export CSV |
| `/admin/users` | Admin user management |

## Testing Checklist

Run the automated security and helper tests:

```powershell
venv\Scripts\python -m unittest discover -s tests -v
```

- User can register successfully.
- User can login successfully.
- Wrong password shows an error.
- Logout works.
- Tester can report a bug.
- Developer cannot access the report bug page.
- Project manager can assign a bug.
- Assigned developer can update the assigned bug status.
- Other developers, testers, admins, and project managers cannot directly update bug status.
- Comments are saved correctly.
- Dashboard counts display correctly.
- Search and filters work correctly.
- Reports page works correctly.
- CSV export downloads successfully.
- Uploaded screenshots are saved.
- Required form fields are validated.
- Restricted pages redirect unauthenticated users.
- Passwords are stored as hashes.

## Common Problems and Fixes

### MySQL server connection error

Error:

```text
Can't connect to MySQL server on 'localhost:3306'
```

Fix:

- Start MySQL.
- Check `DB_HOST`, `DB_PORT`, `DB_USER`, and `DB_PASSWORD` in `.env`.
- Run `venv\Scripts\python check_db.py`.

### Unknown database error

Error:

```text
Unknown database 'bug_tracking_db'
```

Fix:

```powershell
venv\Scripts\python init_db.py
venv\Scripts\python check_db.py
```

### App does not open

Make sure Flask is running:

```powershell
venv\Scripts\python run_dev.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Future Improvements

- Add charts for bug trends.
- Add password reset and optional multi-factor authentication.
- Add virus scanning for uploaded evidence.
- Add deployment configuration for production hosting.
