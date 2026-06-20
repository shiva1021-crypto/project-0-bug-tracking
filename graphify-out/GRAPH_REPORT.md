# Graph Report - .  (2026-06-20)

## Corpus Check
- Corpus is ~14,465 words - fits in a single context window. You may not need a graph.

## Summary
- 70 nodes · 134 edges · 11 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Application Security & Config|Application Security & Config]]
- [[_COMMUNITY_Database Access & Admin|Database Access & Admin]]
- [[_COMMUNITY_Bug Workflow|Bug Workflow]]
- [[_COMMUNITY_Authentication & Profiles|Authentication & Profiles]]
- [[_COMMUNITY_Reports & Authorization|Reports & Authorization]]
- [[_COMMUNITY_Database Initialization|Database Initialization]]

## God Nodes (most connected - your core abstractions)
1. `get_db_connection()` - 28 edges
2. `DatabaseUnavailable` - 6 edges
3. `db_cursor()` - 6 edges
4. `run_migrations()` - 4 edges
5. `main()` - 4 edges
6. `save_screenshot()` - 4 edges
7. `bug_details()` - 4 edges
8. `update_status()` - 4 edges
9. `reports()` - 4 edges
10. `role_required()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `login()` --calls--> `get_db_connection()`  [EXTRACTED]
  routes/auth_routes.py → config.py
- `get_bug_by_id()` --calls--> `get_db_connection()`  [EXTRACTED]
  models/bug_model.py → config.py
- `get_comments_for_bug()` --calls--> `get_db_connection()`  [EXTRACTED]
  models/comment_model.py → config.py
- `get_developers()` --calls--> `get_db_connection()`  [EXTRACTED]
  models/user_model.py → config.py
- `get_user_by_id()` --calls--> `get_db_connection()`  [EXTRACTED]
  models/user_model.py → config.py

## Import Cycles
- None detected.

## Communities (11 total, 0 thin omitted)

### Community 0 - "Application Security & Config"
Cohesion: 0.20
Nodes (8): Config, DatabaseUnavailable, _db_config(), get_server_connection(), RuntimeError, csrf_token(), set_security_headers(), validate_csrf()

### Community 1 - "Database Access & Admin"
Cohesion: 0.22
Nodes (10): get_db_connection(), get_bug_by_id(), get_comments_for_bug(), get_developers(), get_user_by_id(), create_user(), update_user_role(), users() (+2 more)

### Community 2 - "Bug Workflow"
Cohesion: 0.28
Nodes (11): add_bug(), allowed_file(), assign_bug(), bug_details(), edit_bug(), get_developers(), save_screenshot(), update_status() (+3 more)

### Community 3 - "Authentication & Profiles"
Cohesion: 0.32
Nodes (5): db_cursor(), get_profile_data(), login(), register(), user_profile()

### Community 4 - "Reports & Authorization"
Cohesion: 0.36
Nodes (5): build_report_query(), reports(), with_percent(), login_required(), role_required()

### Community 5 - "Database Initialization"
Cohesion: 0.67
Nodes (5): column_exists(), main(), run_if_needed(), run_migrations(), split_sql_statements()

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_db_connection()` connect `Database Access & Admin` to `Application Security & Config`, `Bug Workflow`, `Authentication & Profiles`, `Reports & Authorization`?**
  _High betweenness centrality (0.264) - this node is a cross-community bridge._
- **Why does `DatabaseUnavailable` connect `Application Security & Config` to `Database Access & Admin`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `db_cursor()` connect `Authentication & Profiles` to `Application Security & Config`, `Database Access & Admin`, `Bug Workflow`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._