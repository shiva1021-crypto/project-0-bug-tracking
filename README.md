# IssueFlow — Work Management

A Jira-inspired bug tracking and agile project management tool built with Flask. Supports multi-tenant organizations, role-based access, Kanban boards, sprint planning, backlog management, issue hierarchies (Epic → Story → Task → Subtask), and burndown charts.

---

## Quick Start

### Prerequisites

- Python 3.13+
- MySQL 8.0+ (running locally or remotely)

### Setup

```bash
# 1. Clone & enter the project directory
cd issueflow

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate  # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env   # Windows
# Edit .env — set DB_PASSWORD to your MySQL root password

# 5. Verify database connectivity
python check_db.py

# 6. Initialize the database schema
python init_db.py

# 7. (Optional) Seed demo data
python seed_demo_data.py

# 8. Run the development server
python run_dev.py
```

The app starts at **http://localhost:5000**.

---

## Setup Details

### `.env` Configuration

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | `development` or `production` |
| `SECRET_KEY` | auto-generated | Session signing key |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | — | MySQL password |
| `DB_NAME` | `bug_tracking_db` | Database name |
| `PAGE_SIZE` | `20` | Issues list page size |
| `BOARD_PAGE_SIZE` | `40` | Kanban board page size |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | Require email link verification on registration |
| `RATELIMIT_STORAGE` | `database` | Rate limit backend (`database` or `memory`) |
| `NOTIFICATION_WORKER_ENABLED` | `true` | Enable email notifications |
| `SMTP_HOST` / `SMTP_PORT` / etc. | — | SMTP server for email sending |

### Key Scripts

| Script | Purpose |
|---|---|
| `check_db.py` | Test MySQL connectivity |
| `init_db.py` | Create all tables and run migrations |
| `seed_demo_data.py` | Populate with 5 projects, 10 users, and 150 realistic issues |
| `run_dev.py` | Start Flask development server |
| `wsgi.py` | Production WSGI entry point (Waitress) |

---

## Architecture Overview

```
┌─────────────────────────────────────┐
│           Flask App (app.py)         │
├─────────────────────────────────────┤
│  Blueprints                          │
│  ├─ auth     — registration, login  │
│  ├─ bug      — issues, sprints,     │
│  │             backlog, workflows    │
│  ├─ project  — projects, board      │
│  ├─ report   — analytics, CSV       │
│  └─ admin    — users, registrations │
├─────────────────────────────────────┤
│  Layers                              │
│  ├─ routes/     — HTTP handlers      │
│  ├─ repositories/  — SQL queries     │
│  ├─ services/     — business logic   │
│  └─ utils/        — decorators,      │
│                    pagination, etc.  │
└─────────────────────────────────────┘
```

---

## Features

### 1. Organizations & Multi-Tenancy

Every user, project, and issue belongs to an organization. Users from different organizations never see each other's data.

- **New organization**: During registration, enter an organization name that doesn't exist — you become its first admin with a "General" project auto-created
- **Existing organization**: Enter the name of an existing org — an admin must approve your registration
- **Admin panel**: Admins manage users, approve/reject registrations, and change roles

### 2. Roles & Permissions

| Role | Create Issues | Edit Issues | Assign Issues | Manage Sprints | Manage Users | View Reports |
|---|---|---|---|---|---|---|
| Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Project Manager | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Developer | ✓ | own only | ✗ | ✗ | ✗ | ✗ |
| Tester | ✓ | own only | ✗ | ✗ | ✗ | ✗ |

Developers can update the status of issues assigned to them.

### 3. Projects & Issue Keys

- Each organization can have multiple projects
- A project has a short **key** (e.g. `WEB`, `API`, `MOB`)
- Issues are auto-numbered per project: `PROJECT-1`, `PROJECT-2`, ...

**Managing projects**: Navigate to **Projects** in the sidebar. Admins and project managers can create new projects with a name and key.

### 4. Issue Types & Hierarchy

IssueFlow supports a hierarchy inspired by Jira:

```
Epic
 └── Story
      └── Subtask
Task
Bug
```

- **Epic**: Large body of work; can contain Stories and Tasks
- **Story**: A user-valuable feature; can contain Subtasks
- **Task**: Technical work item
- **Bug**: A defect
- **Subtask**: Breakdown of a Story

**Creating issues**: Click the **+ Create** button in the header. Select a project, issue type, priority, severity, and optionally a parent issue. You can also attach a screenshot, set story points, a due date, labels, and link an external issue URL.

### 5. Kanban Board

The board displays issues in four columns: **Open → In Progress → Resolved → Closed**.

- **Filter** by project and sprint using the dropdowns at the top
- **Search** by issue key or title
- **Quick status change**: Developers assigned to an issue can change its status directly from the card
- **Pagination**: The board supports pagination (configured via `BOARD_PAGE_SIZE`)

### 6. Backlog & Sprints

The **Backlog** page provides a Scrum-style planning view.

**Sprints** have three states:
| State | Description |
|---|---|
| `future` | Planned but not started |
| `active` | In progress (only one active sprint per project at a time) |
| `closed` | Completed |

**Sprint lifecycle**:
1. **Create** a sprint from the Backlog page (give it a name, optional goal, start and end dates)
2. **Assign issues** to the sprint by selecting from the dropdown next to each backlog issue
3. **Start** the sprint when ready — it becomes the active sprint
4. **Close** the sprint when done

A **burndown chart** auto-renders for the active sprint, showing ideal vs. actual progress.

### 7. Issue Details

Click any issue key or title to view its full details:

- **Metadata**: Issue key, type, priority, severity, status, category, story points, due date, labels
- **Description** with reproduction steps
- **Hierarchy**: Parent issue link and child issues list
- **Screenshot**: Displayed if uploaded
- **Comments**: Add comments in a threaded discussion
- **History**: Full audit trail of status changes, assignments, and edits
- **Watchers**: Watch an issue to receive email notifications on status changes
- **Assignment**: Admins & project managers can assign issues to developers

### 8. Editing Issues

Click **Edit** on any issue detail page. The reporter, admins, and project managers can edit:
- Title, description, reproduction steps
- Category, priority, severity
- Issue type and parent (hierarchy validation enforced)
- Labels, story points, due date
- Screenshot (replace or remove)

### 9. Filters & Search

The **Issues List** page (`/bugs`) provides comprehensive filtering:
- By status, priority, severity, issue type, project, and assignee
- Full-text search across issue key, title, and description
- Results are paginated

### 10. Reports & Analytics

Available to admins and project managers.

- **Filterable**: Apply date range, status, priority, and project filters
- **Charts**:
  - Status breakdown (bar chart)
  - Priority distribution (bar chart)
  - Issues by category (horizontal bar chart)
- **Export**: Download the filtered issue list as a CSV file (injection-safe)
- **Print**: Printer-friendly view

### 11. User Management (Admin)

The **Users** admin page (`/admin/users`) allows admins to:
- View all users in the organization
- Create new users directly (bypass registration)
- Change user roles
- Approve or reject pending registration requests
- View registration request details (including requester IP)

### 12. Email Notifications

When configured with SMTP credentials, IssueFlow sends email notifications for:
- Issue assignment
- Status changes (to the reporter and watchers)
- Registration approval/rejection

Notifications are queued in the `email_outbox` table and processed asynchronously.

### 13. Rate Limiting

Login and registration attempts are rate-limited (configurable via `RATELIMIT_STORAGE` and environment settings). Limits can be stored in the database or in-memory.

### 14. Security

- **CSRF protection** on all POST routes
- **Password hashing** with Werkzeug
- **Session-based authentication** with configurable lifetime
- **Screenshot upload validation**: content-type detection via Pillow
- **CSV injection prevention**: Formula prefixes (`=`, `+`, `-`, `@`, `\t`) are neutralized in exports
- **Organization-scoped queries**: All data access is filtered by `organization_id`

### 15. Demo Data

Run `seed_demo_data.py` to populate a **Demo Organization** with:
- 5 projects (WEB, API, MOB, OPS, DATA)
- 10 users across all roles (default password: configured via `DEMO_SEED_PASSWORD`)
- 150 issues with realistic titles, descriptions, priorities, and severities
- Parent-child hierarchies and watchers

---

## Development

### Project Structure

```
app.py                  — Application factory
config.py               — Configuration + DB connection
init_db.py              — Schema + migrations
wsgi.py                 — Production entry point

database/
  bug_tracking.sql      — Full DDL schema

routes/
  auth_routes.py        — Registration, login, logout, profile
  bug_routes.py         — Dashboard, add/view/edit issue details
  sprint_routes.py      — Backlog, sprint CRUD, burndown
  workflow_routes.py    — Assign, status change, comments, watch
  project_routes.py     — Projects list, Kanban board
  report_routes.py      — Reports, charts, CSV export
  admin_routes.py       — User management, registration approvals

repositories/
  issue_repository.py   — Board queries, projects, developers
  sprint_repository.py  — Sprint CRUD, backlog/burndown queries
  workflow_repository.py— Assign, status, comments, watchers

services/
  issue_service.py      — Issue hierarchy validation, field parsers

templates/              — Jinja2 templates (Jira-inspired UI)

utils/
  decorators.py         — login_required, role_required
  notifications.py      — Email queue
  pagination.py         — Pagination helpers
  rate_limit.py         — Rate limiting
  responses.py          — JSON vs redirect response helpers
  security.py           — CSRF, security headers
```

### Adding a New Feature

1. Add repository functions in `repositories/`
2. Create or extend routes in `routes/` with explicit registration
3. Add templates in `templates/`
4. Register routes in `app.py` via `register_*_routes(bp)` before blueprint registration
5. Run `python init_db.py` if schema changes are needed
6. Verify tests pass: `python -m unittest discover -s tests -v`

### Running Tests

```bash
python -m unittest discover -s tests -v
```

Requires a running MySQL instance with the schema initialized.

---

## License

Internal project.
