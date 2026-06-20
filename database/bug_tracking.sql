CREATE DATABASE IF NOT EXISTS bug_tracking_db;
USE bug_tracking_db;

CREATE TABLE IF NOT EXISTS organizations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

CREATE TABLE IF NOT EXISTS bugs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    organization_id INT NOT NULL,
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_bugs_status (status),
    INDEX idx_bugs_priority (priority),
    INDEX idx_bugs_severity (severity),
    INDEX idx_bugs_category (category),
    INDEX idx_bugs_assigned_to (assigned_to),
    INDEX idx_bugs_organization (organization_id),
    CONSTRAINT fk_bugs_organization
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_bugs_reporter
        FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_bugs_assigned
        FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
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
