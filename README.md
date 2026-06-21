# Software Bug Tracking and Reporting Tool — Work Management

A Jira-inspired bug tracking and agile project management tool built with Flask. Supports multi-tenant organizations, role-based access, Kanban boards, sprint planning, backlog management, issue hierarchies (Epic → Story → Task → Subtask), burndown charts, time tracking, custom fields, automation rules, issue linking, saved filters, release management, and configurable dashboard widgets.

---

## Quick Start

### Prerequisites

- Python 3.13+
- MySQL 8.0+ (running locally or remotely)

### Step-by-Step Setup for Client

#### 1. Install Prerequisites

- **Python 3.13+** — Download from https://www.python.org/downloads/
- **MySQL 8.0+** — Download from https://dev.mysql.com/downloads/installer/
  - During MySQL installation, **remember the root password** you set

#### 2. Clone the Project

```bash
git clone https://github.com/shiva1021-crypto/project-0-bug-tracking.git
cd project-0-bug-tracking
```

> Alternatively, if you received the files as a ZIP, extract them and open a terminal in that folder.

#### 3. Create & Activate Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

#### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 5. Configure Environment

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open the `.env` file in a text editor and set your MySQL password:

```
DB_PASSWORD=your_mysql_password_here
```

> Leave all other settings at their defaults for first-time setup.

#### 6. Verify Database Connection

```bash
python check_db.py
```

If you see `OK: MySQL server is reachable`, proceed to the next step.

> **Troubleshooting**: If this fails, make sure MySQL is running (check Services on Windows or `systemctl status mysql` on Linux) and that `DB_PASSWORD` in `.env` is correct.

#### 7. Initialize Database

```bash
python init_db.py
```

This creates all 14 tables and runs any pending migrations. Expected output:

```
Initializing database from ...\bug_tracking.sql...
OK: Database and tables are ready.
```

#### 8. (Optional) Load Demo Data

```bash
python seed_demo_data.py
```

This populates the app with 5 sample projects, 18 users, and 150 realistic issues for testing.

#### 9. Start the Application

```bash
python run_dev.py
```

Open your browser and go to **http://localhost:5000**

#### 10. Login

Use the registration page to create your account, or if you ran the demo seed, login with:

| Email | Password | Role |
|---|---|---|
| `admin@example.com` | _printed in terminal_ | Admin |
| `ava.admin@example.com` | _same password_ | Admin |
| `liam.developer@example.com` | _same password_ | Developer |

The default demo password is printed when you run `seed_demo_data.py`. If not set via `DEMO_SEED_PASSWORD` in `.env`, it will be auto-generated.

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
| `DB_POOL_SIZE` | `5` | MySQL connection pool size |
| `PAGE_SIZE` | `20` | Issues list page size |
| `BOARD_PAGE_SIZE` | `40` | Kanban board page size |
| `SESSION_COOKIE_SECURE` | `false` | Secure session cookies |
| `SESSION_LIFETIME_SECONDS` | `7200` | Session duration |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | Require email link verification on registration |
| `RATELIMIT_STORAGE` | `database` | Rate limit backend (`database` or `memory`) |
| `NOTIFICATION_WORKER_ENABLED` | `true` | Enable email notifications |
| `SMTP_HOST` / `SMTP_PORT` / etc. | — | SMTP server for email sending |
| `SHOW_DEMO_CREDENTIALS` | `false` | Show demo credentials on login page |

### Key Scripts

| Script | Purpose |
|---|---|
| `check_db.py` | Test MySQL connectivity |
| `init_db.py` | Create all tables and run migrations |
| `seed_demo_data.py` | Populate with 5 projects, 18 users, and 150 realistic issues |
| `run_dev.py` | Start Flask development server |
| `wsgi.py` | Production WSGI entry point (Waitress) |
| `scratch/migrate_statuses.py` | Data migration for existing databases when upgrading from old statuses |

---

## Architecture Overview

```
┌──────────────────────────────────────────────┐
│              Flask App (app.py)               │
├──────────────────────────────────────────────┤
│  Blueprints                                   │
│  ├─ auth     — registration, login           │
│  ├─ bug      — issues, sprints, backlog,     │
│  │             workflows, linking, search,    │
│  │             versions, time tracking,       │
│  │             custom fields, automation,     │
│  │             dashboard                      │
│  ├─ project  — projects, board                │
│  ├─ report   — analytics, CSV                 │
│  └─ admin    — users, registrations           │
├──────────────────────────────────────────────┤
│  Layers                                       │
│  ├─ routes/         — HTTP handlers            │
│  ├─ repositories/   — SQL queries              │
│  ├─ services/       — business logic           │
│  └─ utils/          — decorators,              │
│                        pagination, etc.        │
└──────────────────────────────────────────────┘
```

### Registration Order (Critical)

All routes register on the `bug_bp` singleton blueprint in this exact order in `app.py`:

```
register_automation_routes(bp)
register_bug_routes(bp)
register_custom_field_routes(bp)
register_dashboard_routes(bp)
register_link_routes(bp)
register_search_routes(bp)
register_sprint_routes(bp)
register_time_routes(bp)
register_version_routes(bp)
register_workflow_routes(bp)
```

Then `app.register_blueprint(bug_bp)` is called once.

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

Developers can update the status of issues assigned to them. Assigning an issue auto-transitions it from "To Do" to "In Progress".

### 3. Projects & Issue Keys

- Each organization can have multiple projects
- A project has a short **key** (e.g. `WEB`, `API`, `MOB`)
- Issues are auto-numbered per project: `PROJECT-1`, `PROJECT-2`, ...

**Managing projects**: Navigate to **Projects** in the sidebar. Admins and project managers can create new projects with a name and key.

### 4. Issue Types & Hierarchy

Software Bug Tracking and Reporting Tool supports a hierarchy inspired by Jira:

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

**Creating issues**: Click the **+ Create** button in the header. Select a project, issue type, priority, severity, and optionally a parent issue. You can also attach a screenshot, set story points, a due date, fix version, labels, custom fields, and link an external issue URL.

### 5. Status Workflow

Issues flow through a 5-status lifecycle:

```
Idea → To Do → In Progress → Testing → Done
```

| Status | Description |
|---|---|
| `Idea` | Conceptual / proposed work not yet ready for action |
| `To Do` | Ready and prioritized, awaiting assignment |
| `In Progress` | Actively being worked on |
| `Testing` | Implementation complete, awaiting verification |
| `Done` | Completed and accepted |

- The `bugs.status` column is `VARCHAR(50)` (flexible, not an ENUM)
- Assigning an issue auto-transitions from "To Do" to "In Progress"
- All status changes are recorded in `bug_history` (full audit trail)
- The Kanban board displays 4 columns: To Do, In Progress, Testing, Done (Idea issues are not shown on the board)

### 6. Kanban Board

The board displays issues in four columns: **To Do → In Progress → Testing → Done**.

- **Filter** by project and sprint using dropdowns at the top
- **Assignee quick-filter**: Click an avatar to filter by assignee
- **Group by**: Group cards by assignee, priority, or issue type
- **Quick status change**: Drag cards to a different column; only the assigned developer can move a card
- **Card details**: Display issue key, title, priority badge, labels, assignee avatar, and story points
- **Pagination**: The board supports pagination (configured via `BOARD_PAGE_SIZE`)

### 7. Backlog & Sprints

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

### 8. Issue Details

Click any issue key or title to view its full details:

- **Metadata**: Issue key, type, priority, severity, status, category, story points, due date, fix version, labels, time tracking stats
- **Description** with reproduction steps
- **Hierarchy**: Parent issue link and child issues list
- **Screenshot**: Displayed if uploaded
- **Comments**: Add comments in a threaded discussion
- **History**: Full audit trail of status changes, assignments, and edits
- **Watchers**: Watch an issue to receive email notifications on status changes
- **Assignment**: Admins & project managers can assign issues to developers
- **Issue Linking**: Link related issues (blocks, relates to, duplicates, clones) with directional labels
- **Custom Fields**: Display project-specific field values inline in the sidebar
- **Time Tracking**: Log work hours, view time spent, set original and remaining estimates

### 9. Editing Issues

Click **Edit** on any issue detail page. The reporter, admins, and project managers can edit:
- Title, description, reproduction steps
- Category, priority, severity, fix version
- Issue type and parent (hierarchy validation enforced)
- Labels, story points, due date
- Screenshot (replace or remove)
- Custom field values (loaded dynamically based on the project)

### 10. Filters, Search & Saved Filters

The **Issues List** page (`/bugs`) provides comprehensive filtering:
- By status, priority, severity, issue type, project, assignee, and reporter
- Full-text search across issue key, title, and description
- Results are paginated

**Saved Filters**: Save your current query as a named filter. Filters persist across sessions and appear as clickable shortcuts above the issue table. Each filter stores the full query parameter state as JSON.

### 11. Reports & Analytics

Available to admins and project managers.

- **Filterable**: Apply date range, status, priority, and project filters
- **Charts**:
  - Status breakdown (bar chart)
  - Priority distribution (bar chart)
  - Issues by category (horizontal bar chart)
- **Export**: Download the filtered issue list as a CSV file (injection-safe)
- **Print**: Printer-friendly view

### 12. User Management (Admin)

The **Users** admin page (`/admin/users`) allows admins to:
- View all users in the organization
- Create new users directly (bypass registration)
- Change user roles
- Approve or reject pending registration requests
- View registration request details (including requester IP)

### 13. Issue Linking

Link any two issues with a typed relationship. Links are bidirectional and displayed with a directional label on the issue detail page:

| Link Type | Display on Bug A | Display on Bug B |
|---|---|---|
| `blocks` | Blocks B | Blocked by A |
| `relates_to` | Relates to B | Relates to A |
| `duplicates` | Duplicates B | Duplicated by A |
| `clones` | Clones B | Cloned by A |

Link/unlink issues directly from the sidebar form on the issue detail page.

### 14. Release / Version Management

The **Releases** page (`/versions`) manages project versions:
- **Create** a version with a name and optional release date
- **Track** issue counts per version (total, open, resolved)
- **Release** a version to mark it as shipped
- **Archive** a version to hide it from the main list

Issues can be assigned a **Fix Version** during creation or editing. The fix version is displayed in the issue detail sidebar.

### 15. Time Tracking

Log work hours directly on any issue. Track estimates and remaining effort:

- **Log Time**: Enter hours spent and a work description; each entry records the user and timestamp
- **Original Estimate**: Set the total expected effort for the issue
- **Remaining Estimate**: Track how much work is left
- **View History**: All time entries are listed in the Time Tracking panel with user, hours, description, and date
- **Stats**: Time Estimate, Time Spent (total), and Time Remaining appear in the issue detail sidebar

### 16. Custom Fields

Define project-specific fields to capture additional metadata on issues:

**Supported field types**: Text, Number, Date, Dropdown, Checkbox

**Managing fields**: Navigate to **Projects → Fields** (visible to admins and project managers). Create fields with a name, type, and optional constraints:
- Dropdown fields require at least 2 options (one per line)
- Fields can be marked as required
- Fields can be deleted (values are cascade-deleted)

**On issue forms**: Custom fields load dynamically via AJAX when a project is selected. Values are saved and displayed on the issue detail page.

### 17. Automation Rules

Create if-this-then-that rules that execute automatically on issue events:

**Supported triggers**:
- `issue_created` — when a new issue is created
- `status_changed` — when an issue's status changes
- `field_updated` — when an issue is edited

**Supported actions**:
- `transition_status` — change to a specific status (e.g. "Testing")
- `assign_to` — assign to a specific user by ID
- `assign_to_role` — assign to a random user with matching role
- `add_comment` — add a system comment (supports `{bug_id}`, `{issue_key}`, `{actor_id}` placeholders)

**Conditions**: Optionally restrict rules with field/operator/value conditions (e.g. only fire when status changes "To" In Progress).

**Managing rules**: Navigate to **Automation** in the sidebar. Create, enable/disable, and delete rules. Rules can be scoped to a specific project or apply globally.

### 18. Configurable Dashboard Widgets

The **Dashboard** page is a customizable grid of data widgets:

**Widget types**:
| Widget | Description |
|---|---|
| Statistics Summary | Total, To Do, In Progress, Testing, Done, Critical counts |
| Recent Issues | Last 10 created issues with key, priority, status |
| Issues by Status | Doughnut chart broken down by issue status |
| Issues by Priority | Doughnut chart broken down by priority level |
| Issues by Severity | Doughnut chart broken down by severity level |
| Issues by Type | Doughnut chart broken down by issue type |

**Widget management**: Click **+ Add Widget** to open a modal where you choose the type, title, and width (full, half, or third). Widgets can be removed individually. New users start with a default layout of Statistics Summary, Issues by Status, Issues by Priority, and Recent Issues. Charts use Chart.js 4 rendered client-side via CDN.

### 19. Email Notifications

When configured with SMTP credentials, Software Bug Tracking and Reporting Tool sends email notifications for:
- Issue assignment
- Status changes (to the reporter and watchers)
- Registration approval/rejection

Notifications are queued in the `email_outbox` table and processed asynchronously.

### 20. Rate Limiting

Login and registration attempts are rate-limited (configurable via `RATELIMIT_STORAGE` and environment settings). Limits can be stored in the database or in-memory.

### 21. Security

- **CSRF protection** on all POST routes
- **Password hashing** with Werkzeug
- **Session-based authentication** with configurable lifetime
- **Content Security Policy**: `script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net`
- **Screenshot upload validation**: content-type detection via Pillow
- **CSV injection prevention**: Formula prefixes (`=`, `+`, `-`, `@`, `\t`) are neutralized in exports
- **Organization-scoped queries**: All data access is filtered by `organization_id`

### 22. Demo Data

Run `seed_demo_data.py` to populate a **Demo Organization** with:
- 5 projects (WEB, API, MOB, OPS, DATA)
- 18 users across all roles (2 admin, 2 project_manager, 7 developers, 7 testers)
- 150 issues with realistic titles, descriptions, priorities, and severities
- Issue hierarchy: 3 Epics, 8 Stories, 8 Tasks, 7 Bugs, 4 Subtasks per project
- 1–5 comments per issue, 1–4 watchers per issue
- Full bug_history with creation, assignment, and status change entries
- Default password printed at the end (configurable via `DEMO_SEED_PASSWORD`)

---

## Development

### Project Structure

```
app.py                  — Application factory + module-level instance
config.py               — Configuration + MySQL connection pool
init_db.py              — Schema creation + migration runner
seed_demo_data.py       — Deterministic demo data generator
run_dev.py              — Development server launcher
check_db.py             — MySQL connectivity checker
wsgi.py                 — Production WSGI entry point (Waitress)

database/
  bug_tracking.sql      — Full DDL schema (14 tables)

routes/                 — 14 route modules + 1 blueprint definition
  bug_blueprint.py        — bug_bp singleton blueprint
  auth_routes.py          — Registration, login, logout, profile
  admin_routes.py         — User management, registration approvals
  project_routes.py       — Projects list, Kanban board
  report_routes.py        — Reports, charts, CSV export
  bug_routes.py           — Add/view/edit bug details
  sprint_routes.py        — Backlog, sprint CRUD, burndown
  workflow_routes.py      — Assign, status change, comments, watch
  link_routes.py          — Issue linking/unlinking
  search_routes.py        — Saved filters CRUD
  version_routes.py       — Release/version management
  time_routes.py          — Time tracking (log time, estimates)
  custom_field_routes.py  — Custom field management + JSON API
  automation_routes.py    — Automation rules CRUD
  dashboard_routes.py     — Configurable dashboard widgets

repositories/           — 10 SQL query modules
  issue_repository.py     — Board queries, projects, developers
  sprint_repository.py    — Sprint CRUD, backlog/burndown queries
  workflow_repository.py  — Assign, status, comments, watchers
  link_repository.py      — Issue link queries
  filter_repository.py    — Saved filter CRUD
  version_repository.py   — Version CRUD, issue counts
  time_repository.py      — Time entries, estimates
  custom_field_repository.py — Field definitions, values
  automation_repository.py   — Automation rules CRUD + matching
  dashboard_repository.py    — Dashboard widget CRUD

services/
  issue_service.py        — Constants (STATUSES, PRIORITIES), hierarchy validation, parsers
  automation_service.py   — Rule matching & action execution engine

templates/              — 19 Jinja2 templates (Jira-inspired UI)
  base.html               — Layout with header + collapsible sidebar
  index.html              — Landing/hero page
  login.html, register.html
  dashboard.html          — Widget-based customizable dashboard
  add_bug.html            — Create issue form
  edit_bug.html           — Edit issue form
  bug_details.html        — Full issue detail view (521 lines)
  board.html              — Kanban board with drag-and-drop (587 lines)
  backlog.html            — Sprint backlog management (526 lines)
  projects.html, reports.html, profile.html
  users.html              — Admin user management
  versions.html           — Release management
  project_custom_fields.html
  automation_rules.html
  database_error.html     — 503 error page
  macros.html             — SVG icon macros for issue types

static/
  css/style.css           — ~2100 lines, Jira-inspired design system with dark mode
  js/script.js            — ~540 lines, theme, sidebar, drag-and-drop, AJAX UI

models/                 — Legacy query wrappers
  bug_model.py, user_model.py, comment_model.py

utils/                  — 7 cross-cutting modules
  decorators.py           — login_required, role_required
  security.py             — CSRF token, CSP headers
  pagination.py           — Page calculation helpers
  rate_limit.py           — In-memory and DB-backed rate limiting
  notifications.py        — Email outbox queue + SMTP worker thread
  responses.py            — AJAX-aware flash + redirect helper

tests/
  test_database_integration.py  — Full workflow integration test
  test_security_and_helpers.py  — Unit tests for helpers & security

scratch/
  migrate_statuses.py     — Data migration for existing databases (ENUM → VARCHAR)
```

### Adding a New Feature

1. Add repository functions in `repositories/`
2. Create or extend routes in `routes/` with explicit registration via `register_*_routes(bp)`
3. Add templates in `templates/`
4. Register routes in `app.py` via `register_*_routes(bp)` **before** `app.register_blueprint(bug_bp)`
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
