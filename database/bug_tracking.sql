CREATE DATABASE IF NOT EXISTS bug_tracking_db;
USE bug_tracking_db;

CREATE TABLE IF NOT EXISTS organizations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    name VARCHAR(120) NOT NULL,
    project_key VARCHAR(10) NOT NULL,
    description TEXT,
    next_issue_number INT NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_projects_org_key (organization_id, project_key),
    INDEX idx_projects_organization (organization_id),
    CONSTRAINT fk_projects_organization
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'project_manager', 'developer', 'tester') NOT NULL DEFAULT 'tester',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_organization (organization_id),
    CONSTRAINT fk_users_organization
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS registration_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    requested_role ENUM('admin', 'project_manager', 'developer', 'tester') NOT NULL DEFAULT 'tester',
    status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    requester_ip VARCHAR(45),
    verification_token_hash CHAR(64) NULL,
    verified_at DATETIME NULL,
    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME NULL,
    reviewed_by INT NULL,
    INDEX idx_registration_org_status (organization_id, status),
    INDEX idx_registration_email (email),
    CONSTRAINT fk_registration_organization
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_registration_reviewer
        FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS bugs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
    project_id INT NOT NULL,
    issue_key VARCHAR(30) NOT NULL,
    issue_type ENUM('Epic', 'Story', 'Task', 'Bug', 'Subtask') NOT NULL DEFAULT 'Bug',
    parent_id INT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    reproduction_steps TEXT,
    category VARCHAR(80) NOT NULL DEFAULT 'General',
    priority ENUM('Low', 'Medium', 'High', 'Urgent') NOT NULL,
    severity ENUM('Minor', 'Major', 'Critical', 'Blocker') NOT NULL,
    status ENUM('Open', 'In Progress', 'Resolved', 'Closed') NOT NULL DEFAULT 'Open',
    reporter_id INT NOT NULL,
    assigned_to INT NULL,
    screenshot_path VARCHAR(255),
    external_issue_url VARCHAR(255),
    labels VARCHAR(255),
    story_points INT NULL,
    due_date DATE NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_bugs_status (status),
    INDEX idx_bugs_priority (priority),
    INDEX idx_bugs_severity (severity),
    INDEX idx_bugs_category (category),
    INDEX idx_bugs_assigned_to (assigned_to),
    INDEX idx_bugs_organization (organization_id),
    UNIQUE KEY uq_bugs_org_issue_key (organization_id, issue_key),
    INDEX idx_bugs_project (project_id),
    INDEX idx_bugs_issue_type (issue_type),
    INDEX idx_bugs_parent (parent_id),
    CONSTRAINT fk_bugs_organization
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_bugs_project
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_bugs_parent
        FOREIGN KEY (parent_id) REFERENCES bugs(id) ON DELETE SET NULL,
    CONSTRAINT fk_bugs_reporter
        FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_bugs_assigned
        FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS issue_watchers (
    bug_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (bug_id, user_id),
    CONSTRAINT fk_watchers_bug
        FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
    CONSTRAINT fk_watchers_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bug_id INT NOT NULL,
    user_id INT NOT NULL,
    comment TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comments_bug
        FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
    CONSTRAINT fk_comments_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bug_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bug_id INT NOT NULL,
    changed_by INT NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    old_assigned_to INT NULL,
    new_assigned_to INT NULL,
    change_note TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_history_bug
        FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE,
    CONSTRAINT fk_history_changed_by
        FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE CASCADE
);
