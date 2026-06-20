Below is the **step-by-step localhost implementation plan** for your client project using **HTML, CSS, JavaScript, Python Flask and MySQL**.

I recommend building this in phases instead of trying to finish everything at once. First complete the **essential features**, then add dashboard, comments, uploads, reports and optional features.

---

# 1. Final development flow

Build the project in this order:

```text
Phase 1  - Setup project folder
Phase 2  - Create virtual environment
Phase 3  - Install Flask and MySQL packages
Phase 4  - Create MySQL database and tables
Phase 5  - Create Flask app structure
Phase 6  - Connect Flask with MySQL
Phase 7  - Build registration and login
Phase 8  - Add role based access
Phase 9  - Create bug reporting feature
Phase 10 - View, search and filter bugs
Phase 11 - Assign bugs to developers
Phase 12 - Developer status update
Phase 13 - Bug details page
Phase 14 - Comments system
Phase 15 - Dashboard statistics
Phase 16 - Screenshot/file upload
Phase 17 - Reports page
Phase 18 - Frontend styling and responsiveness
Phase 19 - Testing
Phase 20 - Final documentation
```

Flask officially supports installation through `pip install Flask`, and for MySQL communication you can use Oracle’s `mysql-connector-python`, which is installable through pip. ([Flask Documentation][1])

---

# 2. Create project folder

Open **VS Code terminal** and run:

```bash
mkdir bug-tracking-tool
cd bug-tracking-tool
```

Create this structure:

```text
bug-tracking-tool/
│
├── app.py
├── config.py
├── requirements.txt
├── .env
├── README.md
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── add_bug.html
│   ├── view_bugs.html
│   ├── edit_bug.html
│   ├── bug_details.html
│   └── reports.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   └── images/
│
├── uploads/
│   └── bug_screenshots/
│
├── database/
│   └── bug_tracking.sql
│
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py
│   ├── bug_routes.py
│   └── report_routes.py
│
├── models/
│   ├── __init__.py
│   ├── user_model.py
│   ├── bug_model.py
│   └── comment_model.py
│
├── utils/
│   ├── __init__.py
│   └── decorators.py
│
└── documentation/
    └── project_report.md
```

---

# 3. Create Python virtual environment

Run:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Then install packages:

```bash
pip install Flask mysql-connector-python python-dotenv
```

Generate `requirements.txt`:

```bash
pip freeze > requirements.txt
```

Your `requirements.txt` will contain packages similar to:

```text
Flask
mysql-connector-python
python-dotenv
```

---

# 4. Create MySQL database

Open **MySQL Workbench** or MySQL terminal.

Create this file:

```text
database/bug_tracking.sql
```

Paste this SQL:

```sql
CREATE DATABASE IF NOT EXISTS bug_tracking_db;
USE bug_tracking_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'project_manager', 'developer', 'tester') NOT NULL DEFAULT 'tester',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bugs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    reproduction_steps TEXT,
    priority ENUM('Low', 'Medium', 'High', 'Urgent') NOT NULL,
    severity ENUM('Minor', 'Major', 'Critical', 'Blocker') NOT NULL,
    status ENUM('Open', 'In Progress', 'Resolved', 'Closed') NOT NULL DEFAULT 'Open',
    reporter_id INT NOT NULL,
    assigned_to INT NULL,
    screenshot_path VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bug_id INT NOT NULL,
    user_id INT NOT NULL,
    comment TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE bug_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bug_id INT NOT NULL,
    changed_by INT NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    old_assigned_to INT NULL,
    new_assigned_to INT NULL,
    change_note TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE CASCADE
);
```

Then run the SQL file in MySQL Workbench.

---

# 5. Create `.env` file

Inside project root:

```env
SECRET_KEY=your_secret_key_here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=bug_tracking_db
```

Never hardcode database passwords directly inside `app.py`.

---

# 6. Create `config.py`

```python
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    UPLOAD_FOLDER = "uploads/bug_screenshots"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
```

---

# 7. Create `app.py`

```python
from flask import Flask, render_template, session
from config import Config
from routes.auth_routes import auth_bp
from routes.bug_routes import bug_bp
from routes.report_routes import report_bp

app = Flask(__name__)
app.config.from_object(Config)

app.register_blueprint(auth_bp)
app.register_blueprint(bug_bp)
app.register_blueprint(report_bp)

@app.context_processor
def inject_user():
    return dict(
        current_user_id=session.get("user_id"),
        current_user_name=session.get("full_name"),
        current_user_role=session.get("role")
    )

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
```

Run the app:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

---

# 8. Create authentication routes

Create:

```text
routes/auth_routes.py
```

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from config import get_db_connection

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        if not full_name or not email or not password or not role:
            flash("All fields are required.", "error")
            return redirect(url_for("auth.register"))

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (full_name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
            """, (full_name, email, password_hash, role))
            conn.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            conn.rollback()
            flash("Email already exists or registration failed.", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash("Login successful.", "success")
            return redirect(url_for("bug.dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
```

Use password hashing instead of storing plain text passwords. Werkzeug provides `generate_password_hash()` and `check_password_hash()` for this purpose. ([werkzeug.palletsprojects.com][2])

---

# 9. Create role protection decorator

Create:

```text
utils/decorators.py
```

```python
from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please login first.", "error")
                return redirect(url_for("auth.login"))

            if session.get("role") not in roles:
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for("bug.dashboard"))

            return func(*args, **kwargs)
        return wrapper
    return decorator
```

This lets you protect pages like:

```python
@role_required("admin", "project_manager")
```

---

# 10. Create bug routes

Create:

```text
routes/bug_routes.py
```

```python
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from config import get_db_connection
from utils.decorators import login_required, role_required

bug_bp = Blueprint("bug", __name__)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


@bug_bp.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM bugs")
    total_bugs = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM bugs WHERE status='Open'")
    open_bugs = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM bugs WHERE status='Resolved'")
    resolved_bugs = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM bugs WHERE status='Closed'")
    closed_bugs = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM bugs WHERE severity='Critical' OR severity='Blocker'")
    critical_bugs = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_bugs=total_bugs,
        open_bugs=open_bugs,
        resolved_bugs=resolved_bugs,
        closed_bugs=closed_bugs,
        critical_bugs=critical_bugs
    )


@bug_bp.route("/bugs/add", methods=["GET", "POST"])
@role_required("tester", "admin", "project_manager")
def add_bug():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        reproduction_steps = request.form.get("reproduction_steps")
        priority = request.form.get("priority")
        severity = request.form.get("severity")

        screenshot_path = None

        file = request.files.get("screenshot")
        if file and file.filename != "" and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(upload_path)
            screenshot_path = upload_path

        if not title or not description or not priority or not severity:
            flash("Please fill all required fields.", "error")
            return redirect(url_for("bug.add_bug"))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO bugs
            (title, description, reproduction_steps, priority, severity, reporter_id, screenshot_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            title,
            description,
            reproduction_steps,
            priority,
            severity,
            session["user_id"],
            screenshot_path
        ))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Bug reported successfully.", "success")
        return redirect(url_for("bug.view_bugs"))

    return render_template("add_bug.html")


@bug_bp.route("/bugs")
@login_required
def view_bugs():
    status = request.args.get("status")
    priority = request.args.get("priority")
    severity = request.args.get("severity")
    assigned_to = request.args.get("assigned_to")

    query = """
        SELECT bugs.*, 
               reporter.full_name AS reporter_name,
               developer.full_name AS developer_name
        FROM bugs
        JOIN users AS reporter ON bugs.reporter_id = reporter.id
        LEFT JOIN users AS developer ON bugs.assigned_to = developer.id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND bugs.status = %s"
        params.append(status)

    if priority:
        query += " AND bugs.priority = %s"
        params.append(priority)

    if severity:
        query += " AND bugs.severity = %s"
        params.append(severity)

    if assigned_to:
        query += " AND bugs.assigned_to = %s"
        params.append(assigned_to)

    query += " ORDER BY bugs.created_at DESC"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(query, params)
    bugs = cursor.fetchall()

    cursor.execute("SELECT id, full_name FROM users WHERE role='developer'")
    developers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("view_bugs.html", bugs=bugs, developers=developers)


@bug_bp.route("/bugs/<int:bug_id>")
@login_required
def bug_details(bug_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT bugs.*, 
               reporter.full_name AS reporter_name,
               developer.full_name AS developer_name
        FROM bugs
        JOIN users AS reporter ON bugs.reporter_id = reporter.id
        LEFT JOIN users AS developer ON bugs.assigned_to = developer.id
        WHERE bugs.id = %s
    """, (bug_id,))
    bug = cursor.fetchone()

    cursor.execute("""
        SELECT comments.*, users.full_name
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.bug_id = %s
        ORDER BY comments.created_at DESC
    """, (bug_id,))
    comments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("bug_details.html", bug=bug, comments=comments)


@bug_bp.route("/bugs/<int:bug_id>/assign", methods=["POST"])
@role_required("admin", "project_manager")
def assign_bug(bug_id):
    developer_id = request.form.get("developer_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT assigned_to FROM bugs WHERE id=%s", (bug_id,))
    old_assigned_to = cursor.fetchone()[0]

    cursor.execute("""
        UPDATE bugs
        SET assigned_to = %s, status = 'In Progress'
        WHERE id = %s
    """, (developer_id, bug_id))

    cursor.execute("""
        INSERT INTO bug_history
        (bug_id, changed_by, old_assigned_to, new_assigned_to, change_note)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        bug_id,
        session["user_id"],
        old_assigned_to,
        developer_id,
        "Bug assigned to developer"
    ))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Bug assigned successfully.", "success")
    return redirect(url_for("bug.bug_details", bug_id=bug_id))


@bug_bp.route("/bugs/<int:bug_id>/status", methods=["POST"])
@role_required("developer", "admin", "project_manager")
def update_status(bug_id):
    new_status = request.form.get("status")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM bugs WHERE id=%s", (bug_id,))
    old_status = cursor.fetchone()[0]

    cursor.execute("""
        UPDATE bugs
        SET status = %s
        WHERE id = %s
    """, (new_status, bug_id))

    cursor.execute("""
        INSERT INTO bug_history
        (bug_id, changed_by, old_status, new_status, change_note)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        bug_id,
        session["user_id"],
        old_status,
        new_status,
        "Bug status updated"
    ))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Bug status updated successfully.", "success")
    return redirect(url_for("bug.bug_details", bug_id=bug_id))


@bug_bp.route("/bugs/<int:bug_id>/comment", methods=["POST"])
@login_required
def add_comment(bug_id):
    comment = request.form.get("comment")

    if not comment:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("bug.bug_details", bug_id=bug_id))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO comments (bug_id, user_id, comment)
        VALUES (%s, %s, %s)
    """, (bug_id, session["user_id"], comment))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Comment added successfully.", "success")
    return redirect(url_for("bug.bug_details", bug_id=bug_id))
```

For file uploads, Flask’s official pattern uses `multipart/form-data`, checks allowed extensions, and recommends `secure_filename()` before saving uploaded files. ([Flask Documentation][3])

---

# 11. Create reports route

Create:

```text
routes/report_routes.py
```

```python
from flask import Blueprint, render_template, request
from config import get_db_connection
from utils.decorators import role_required

report_bp = Blueprint("report", __name__)

@report_bp.route("/reports")
@role_required("admin", "project_manager")
def reports():
    status = request.args.get("status")
    priority = request.args.get("priority")
    severity = request.args.get("severity")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = """
        SELECT bugs.*, 
               reporter.full_name AS reporter_name,
               developer.full_name AS developer_name
        FROM bugs
        JOIN users AS reporter ON bugs.reporter_id = reporter.id
        LEFT JOIN users AS developer ON bugs.assigned_to = developer.id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND bugs.status=%s"
        params.append(status)

    if priority:
        query += " AND bugs.priority=%s"
        params.append(priority)

    if severity:
        query += " AND bugs.severity=%s"
        params.append(severity)

    if start_date:
        query += " AND DATE(bugs.created_at) >= %s"
        params.append(start_date)

    if end_date:
        query += " AND DATE(bugs.created_at) <= %s"
        params.append(end_date)

    query += " ORDER BY bugs.created_at DESC"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(query, params)
    bugs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("reports.html", bugs=bugs)
```

---

# 12. Create base template

Create:

```text
templates/base.html
```

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Bug Tracking Tool</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>

<nav class="navbar">
    <h2>Bug Tracking Tool</h2>

    <div>
        {% if current_user_id %}
            <a href="{{ url_for('bug.dashboard') }}">Dashboard</a>
            <a href="{{ url_for('bug.view_bugs') }}">Bugs</a>

            {% if current_user_role in ['tester', 'admin', 'project_manager'] %}
                <a href="{{ url_for('bug.add_bug') }}">Report Bug</a>
            {% endif %}

            {% if current_user_role in ['admin', 'project_manager'] %}
                <a href="{{ url_for('report.reports') }}">Reports</a>
            {% endif %}

            <a href="{{ url_for('auth.logout') }}">Logout</a>
        {% else %}
            <a href="{{ url_for('auth.login') }}">Login</a>
            <a href="{{ url_for('auth.register') }}">Register</a>
        {% endif %}
    </div>
</nav>

<div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}
</div>

<script src="{{ url_for('static', filename='js/script.js') }}"></script>
</body>
</html>
```

---

# 13. Create login page

```text
templates/login.html
```

```html
{% extends "base.html" %}

{% block content %}
<div class="form-card">
    <h2>Login</h2>

    <form method="POST">
        <label>Email</label>
        <input type="email" name="email" required>

        <label>Password</label>
        <input type="password" name="password" required>

        <button type="submit">Login</button>
    </form>
</div>
{% endblock %}
```

---

# 14. Create register page

```text
templates/register.html
```

```html
{% extends "base.html" %}

{% block content %}
<div class="form-card">
    <h2>Register</h2>

    <form method="POST">
        <label>Full Name</label>
        <input type="text" name="full_name" required>

        <label>Email</label>
        <input type="email" name="email" required>

        <label>Password</label>
        <input type="password" name="password" required>

        <label>Role</label>
        <select name="role" required>
            <option value="tester">Tester</option>
            <option value="developer">Developer</option>
            <option value="project_manager">Project Manager</option>
            <option value="admin">Administrator</option>
        </select>

        <button type="submit">Register</button>
    </form>
</div>
{% endblock %}
```

For a real production system, users should not freely choose `admin`. For your localhost/client demo, this is acceptable. Later, you can restrict role creation to the admin panel.

---

# 15. Create dashboard page

```text
templates/dashboard.html
```

```html
{% extends "base.html" %}

{% block content %}
<h1>Dashboard</h1>

<div class="stats-grid">
    <div class="stat-card">
        <h3>Total Bugs</h3>
        <p>{{ total_bugs }}</p>
    </div>

    <div class="stat-card">
        <h3>Open Bugs</h3>
        <p>{{ open_bugs }}</p>
    </div>

    <div class="stat-card">
        <h3>Resolved Bugs</h3>
        <p>{{ resolved_bugs }}</p>
    </div>

    <div class="stat-card">
        <h3>Closed Bugs</h3>
        <p>{{ closed_bugs }}</p>
    </div>

    <div class="stat-card">
        <h3>Critical Bugs</h3>
        <p>{{ critical_bugs }}</p>
    </div>
</div>
{% endblock %}
```

---

# 16. Create add bug page

```text
templates/add_bug.html
```

```html
{% extends "base.html" %}

{% block content %}
<div class="form-card">
    <h2>Report New Bug</h2>

    <form method="POST" enctype="multipart/form-data">
        <label>Bug Title</label>
        <input type="text" name="title" required>

        <label>Description</label>
        <textarea name="description" required></textarea>

        <label>Reproduction Steps</label>
        <textarea name="reproduction_steps"></textarea>

        <label>Priority</label>
        <select name="priority" required>
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Urgent">Urgent</option>
        </select>

        <label>Severity</label>
        <select name="severity" required>
            <option value="Minor">Minor</option>
            <option value="Major">Major</option>
            <option value="Critical">Critical</option>
            <option value="Blocker">Blocker</option>
        </select>

        <label>Screenshot</label>
        <input type="file" name="screenshot">

        <button type="submit">Submit Bug</button>
    </form>
</div>
{% endblock %}
```

---

# 17. Create view bugs page

```text
templates/view_bugs.html
```

```html
{% extends "base.html" %}

{% block content %}
<h1>Reported Bugs</h1>

<form method="GET" class="filter-box">
    <select name="status">
        <option value="">All Status</option>
        <option value="Open">Open</option>
        <option value="In Progress">In Progress</option>
        <option value="Resolved">Resolved</option>
        <option value="Closed">Closed</option>
    </select>

    <select name="priority">
        <option value="">All Priority</option>
        <option value="Low">Low</option>
        <option value="Medium">Medium</option>
        <option value="High">High</option>
        <option value="Urgent">Urgent</option>
    </select>

    <select name="severity">
        <option value="">All Severity</option>
        <option value="Minor">Minor</option>
        <option value="Major">Major</option>
        <option value="Critical">Critical</option>
        <option value="Blocker">Blocker</option>
    </select>

    <button type="submit">Filter</button>
</form>

<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Priority</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Reporter</th>
            <th>Assigned To</th>
            <th>Created</th>
            <th>View</th>
        </tr>
    </thead>

    <tbody>
        {% for bug in bugs %}
        <tr>
            <td>{{ bug.id }}</td>
            <td>{{ bug.title }}</td>
            <td>{{ bug.priority }}</td>
            <td>{{ bug.severity }}</td>
            <td>{{ bug.status }}</td>
            <td>{{ bug.reporter_name }}</td>
            <td>{{ bug.developer_name or "Not Assigned" }}</td>
            <td>{{ bug.created_at }}</td>
            <td>
                <a href="{{ url_for('bug.bug_details', bug_id=bug.id) }}">View</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

---

# 18. Create bug details page

```text
templates/bug_details.html
```

```html
{% extends "base.html" %}

{% block content %}
<h1>{{ bug.title }}</h1>

<div class="details-card">
    <p><strong>Description:</strong> {{ bug.description }}</p>
    <p><strong>Reproduction Steps:</strong> {{ bug.reproduction_steps }}</p>
    <p><strong>Priority:</strong> {{ bug.priority }}</p>
    <p><strong>Severity:</strong> {{ bug.severity }}</p>
    <p><strong>Status:</strong> {{ bug.status }}</p>
    <p><strong>Reporter:</strong> {{ bug.reporter_name }}</p>
    <p><strong>Assigned Developer:</strong> {{ bug.developer_name or "Not Assigned" }}</p>

    {% if bug.screenshot_path %}
        <p><strong>Screenshot:</strong></p>
        <img src="/{{ bug.screenshot_path }}" class="screenshot">
    {% endif %}
</div>

{% if current_user_role in ['admin', 'project_manager'] %}
<h3>Assign Developer</h3>
<form method="POST" action="{{ url_for('bug.assign_bug', bug_id=bug.id) }}">
    <input type="number" name="developer_id" placeholder="Developer User ID" required>
    <button type="submit">Assign</button>
</form>
{% endif %}

{% if current_user_role in ['developer', 'admin', 'project_manager'] %}
<h3>Update Status</h3>
<form method="POST" action="{{ url_for('bug.update_status', bug_id=bug.id) }}">
    <select name="status">
        <option value="Open">Open</option>
        <option value="In Progress">In Progress</option>
        <option value="Resolved">Resolved</option>
        <option value="Closed">Closed</option>
    </select>
    <button type="submit">Update</button>
</form>
{% endif %}

<h3>Comments</h3>

<form method="POST" action="{{ url_for('bug.add_comment', bug_id=bug.id) }}">
    <textarea name="comment" required></textarea>
    <button type="submit">Add Comment</button>
</form>

{% for comment in comments %}
<div class="comment-box">
    <strong>{{ comment.full_name }}</strong>
    <p>{{ comment.comment }}</p>
    <small>{{ comment.created_at }}</small>
</div>
{% endfor %}

{% endblock %}
```

Later, improve the developer assignment field by using a dropdown instead of manually entering developer ID.

---

# 19. Create reports page

```text
templates/reports.html
```

```html
{% extends "base.html" %}

{% block content %}
<h1>Bug Reports</h1>

<form method="GET" class="filter-box">
    <select name="status">
        <option value="">All Status</option>
        <option value="Open">Open</option>
        <option value="In Progress">In Progress</option>
        <option value="Resolved">Resolved</option>
        <option value="Closed">Closed</option>
    </select>

    <select name="priority">
        <option value="">All Priority</option>
        <option value="Low">Low</option>
        <option value="Medium">Medium</option>
        <option value="High">High</option>
        <option value="Urgent">Urgent</option>
    </select>

    <select name="severity">
        <option value="">All Severity</option>
        <option value="Minor">Minor</option>
        <option value="Major">Major</option>
        <option value="Critical">Critical</option>
        <option value="Blocker">Blocker</option>
    </select>

    <input type="date" name="start_date">
    <input type="date" name="end_date">

    <button type="submit">Generate Report</button>
</form>

<table>
    <thead>
        <tr>
            <th>ID</th>
            <th>Bug</th>
            <th>Status</th>
            <th>Priority</th>
            <th>Severity</th>
            <th>Assigned</th>
            <th>Date</th>
        </tr>
    </thead>

    <tbody>
        {% for bug in bugs %}
        <tr>
            <td>{{ bug.id }}</td>
            <td>{{ bug.title }}</td>
            <td>{{ bug.status }}</td>
            <td>{{ bug.priority }}</td>
            <td>{{ bug.severity }}</td>
            <td>{{ bug.developer_name or "Not Assigned" }}</td>
            <td>{{ bug.created_at }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

---

# 20. Create basic CSS

Create:

```text
static/css/style.css
```

```css
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f6f8;
    color: #222;
}

.navbar {
    background: #1f2937;
    color: white;
    padding: 16px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.navbar a {
    color: white;
    margin-left: 16px;
    text-decoration: none;
}

.container {
    padding: 32px;
}

.form-card,
.details-card {
    background: white;
    padding: 24px;
    border-radius: 10px;
    max-width: 700px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

label {
    display: block;
    margin-top: 14px;
    font-weight: bold;
}

input,
select,
textarea {
    width: 100%;
    padding: 10px;
    margin-top: 6px;
    border: 1px solid #ccc;
    border-radius: 6px;
}

textarea {
    min-height: 120px;
}

button {
    margin-top: 18px;
    padding: 10px 18px;
    border: none;
    background: #2563eb;
    color: white;
    border-radius: 6px;
    cursor: pointer;
}

button:hover {
    background: #1d4ed8;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
}

.stat-card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.stat-card p {
    font-size: 28px;
    font-weight: bold;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    margin-top: 20px;
}

th,
td {
    padding: 12px;
    border-bottom: 1px solid #ddd;
    text-align: left;
}

th {
    background: #e5e7eb;
}

.alert {
    padding: 12px;
    margin-bottom: 16px;
    border-radius: 6px;
}

.alert.success {
    background: #dcfce7;
    color: #166534;
}

.alert.error {
    background: #fee2e2;
    color: #991b1b;
}

.filter-box {
    background: white;
    padding: 16px;
    border-radius: 10px;
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
}

.comment-box {
    background: white;
    padding: 14px;
    border-radius: 8px;
    margin-top: 12px;
}

.screenshot {
    max-width: 400px;
    border-radius: 8px;
}

@media (max-width: 900px) {
    .stats-grid,
    .filter-box {
        grid-template-columns: 1fr;
    }

    .navbar {
        flex-direction: column;
        align-items: flex-start;
    }
}
```

---

# 21. Create simple JavaScript validation

Create:

```text
static/js/script.js
```

```javascript
document.addEventListener("DOMContentLoaded", function () {
    const forms = document.querySelectorAll("form");

    forms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const requiredFields = form.querySelectorAll("[required]");
            let valid = true;

            requiredFields.forEach(function (field) {
                if (!field.value.trim()) {
                    valid = false;
                    field.style.borderColor = "red";
                } else {
                    field.style.borderColor = "#ccc";
                }
            });

            if (!valid) {
                event.preventDefault();
                alert("Please fill all required fields.");
            }
        });
    });
});
```

---

# 22. Add homepage

Create:

```text
templates/index.html
```

```html
{% extends "base.html" %}

{% block content %}
<div class="form-card">
    <h1>Software Bug Tracking and Reporting Tool</h1>
    <p>
        A web based system for reporting, assigning, monitoring and resolving software defects.
    </p>

    {% if not current_user_id %}
        <a href="{{ url_for('auth.login') }}">
            <button>Login</button>
        </a>

        <a href="{{ url_for('auth.register') }}">
            <button>Register</button>
        </a>
    {% else %}
        <a href="{{ url_for('bug.dashboard') }}">
            <button>Go to Dashboard</button>
        </a>
    {% endif %}
</div>
{% endblock %}
```

---

# 23. Run the project

Start Flask:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

Then test in this order:

```text
1. Register admin
2. Register tester
3. Register developer
4. Register project manager
5. Login as tester
6. Create bug
7. Login as project manager
8. Assign bug to developer
9. Login as developer
10. Update bug status
11. Add comment
12. Check dashboard
13. Check reports
```

---

# 24. Recommended role permissions

Use this permission table in your project report:

| Feature           | Admin | Project Manager | Developer | Tester |
| ----------------- | ----: | --------------: | --------: | -----: |
| Register/Login    |   Yes |             Yes |       Yes |    Yes |
| View Dashboard    |   Yes |             Yes |       Yes |    Yes |
| Report Bug        |   Yes |             Yes |        No |    Yes |
| View Bugs         |   Yes |             Yes |       Yes |    Yes |
| Assign Bug        |   Yes |             Yes |        No |     No |
| Update Bug Status |   Yes |             Yes |       Yes |     No |
| Add Comment       |   Yes |             Yes |       Yes |    Yes |
| View Reports      |   Yes |             Yes |        No |     No |
| Manage Users      |   Yes |              No |        No |     No |

---

# 25. Essential features to complete first

Complete these before adding optional features:

```text
Registration
Login
Logout
Role based access
Add bug
View bugs
Search/filter bugs
Assign bug
Update status
Dashboard
Comments
Basic reports
Input validation
Password hashing
Restricted page protection
```

After this, add:

```text
File upload
CSV export
PDF export
Charts
Email notification
Audit trail
Admin user management
Dark mode
GitHub integration
```

---

# 26. Testing checklist

Use this checklist before submitting to your client:

```text
[ ] User can register successfully
[ ] User can login successfully
[ ] Wrong password shows error message
[ ] Logout works
[ ] Tester can report bug
[ ] Developer cannot access report bug page
[ ] Project manager can assign bug
[ ] Developer can update assigned bug status
[ ] Bug status changes correctly
[ ] Comments are saved correctly
[ ] Dashboard count is correct
[ ] Filters work correctly
[ ] Reports page works correctly
[ ] Uploaded screenshot is saved
[ ] Empty form fields show validation error
[ ] Restricted pages redirect unauthenticated users
[ ] Password is stored as hash, not plain text
```

---

# 27. Best AI agent prompt for VS Code / Codex

Use this prompt phase by phase:

```text
You are a senior Python Flask developer.

Build a localhost web application named Software Bug Tracking and Reporting Tool.

Tech stack:
- Python Flask
- MySQL
- HTML
- CSS
- JavaScript
- mysql-connector-python
- python-dotenv
- Werkzeug password hashing

Use this folder structure:
app.py
config.py
templates/
static/
routes/
models/
utils/
database/
uploads/

Features:
1. User registration and login
2. Role based access for admin, project_manager, developer and tester
3. Tester can submit bug reports
4. Admin/project_manager can assign bugs to developers
5. Developer can update bug status
6. Users can comment on bug details
7. Dashboard statistics
8. Search and filtering
9. Reports page
10. Screenshot upload
11. Server-side validation
12. Secure password hashing
13. Protected routes

Create clean, beginner-friendly code with comments.
Do not use advanced frameworks.
Keep the design professional and responsive.
Use MySQL database connection from config.py.
```

---

For your client project, first complete the **essential version** on localhost. After that, add the desirable and optional features one by one. This will make the project easier to debug and easier to explain during submission or client review.

[1]: https://flask.palletsprojects.com/en/stable/installation/?utm_source=chatgpt.com "Installation — Flask Documentation (3.1.x)"
[2]: https://werkzeug.palletsprojects.com/en/stable/utils/?utm_source=chatgpt.com "Utilities — Werkzeug Documentation (3.1.x)"
[3]: https://flask.palletsprojects.com/en/stable/patterns/fileuploads/?utm_source=chatgpt.com "Uploading Files — Flask Documentation (3.1.x)"
