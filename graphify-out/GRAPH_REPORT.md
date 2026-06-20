# Graph Report - .  (2026-06-20)

## Corpus Check
- Corpus is ~25,018 words - fits in a single context window. You may not need a graph.

## Summary
- 117 nodes · 245 edges · 13 communities (9 shown, 4 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Code Community 0|Code Community 0]]
- [[_COMMUNITY_Code Community 1|Code Community 1]]
- [[_COMMUNITY_Code Community 2|Code Community 2]]
- [[_COMMUNITY_Code Community 3|Code Community 3]]
- [[_COMMUNITY_Code Community 4|Code Community 4]]
- [[_COMMUNITY_Code Community 5|Code Community 5]]
- [[_COMMUNITY_Code Community 6|Code Community 6]]
- [[_COMMUNITY_Code Community 7|Code Community 7]]
- [[_COMMUNITY_Code Community 8|Code Community 8]]

## God Nodes (most connected - your core abstractions)
1. `get_db_connection()` - 38 edges
2. `SecurityAndHelperTests` - 12 edges
3. `db_cursor()` - 8 edges
4. `add_bug()` - 7 edges
5. `FakeCursor` - 7 edges
6. `pagination_values()` - 7 edges
7. `DatabaseUnavailable` - 6 edges
8. `edit_bug()` - 6 edges
9. `reports()` - 6 edges
10. `FakeConnection` - 6 edges

## Surprising Connections (you probably didn't know these)
- `login()` --calls--> `get_db_connection()`  [EXTRACTED]
  routes/auth_routes.py → config.py
- `add_comment()` --calls--> `get_db_connection()`  [EXTRACTED]
  routes/bug_routes.py → config.py
- `dashboard()` --calls--> `get_db_connection()`  [EXTRACTED]
  routes/bug_routes.py → config.py
- `toggle_watch()` --calls--> `get_db_connection()`  [EXTRACTED]
  routes/bug_routes.py → config.py
- `board()` --calls--> `get_db_connection()`  [EXTRACTED]
  routes/project_routes.py → config.py

## Import Cycles
- None detected.

## Communities (13 total, 4 thin omitted)

### Community 0 - "Code Community 0"
Cohesion: 0.15
Nodes (17): main(), DatabaseUnavailable, _db_config(), get_db_connection(), get_server_connection(), _secret_key(), get_bug_by_id(), get_comments_for_bug() (+9 more)

### Community 1 - "Code Community 1"
Cohesion: 0.13
Nodes (15): create_app(), Config, db_cursor(), get_profile_data(), login(), register(), user_profile(), board() (+7 more)

### Community 2 - "Code Community 2"
Cohesion: 0.19
Nodes (18): add_bug(), add_comment(), allowed_file(), assign_bug(), bug_details(), dashboard(), edit_bug(), get_developers() (+10 more)

### Community 4 - "Code Community 4"
Cohesion: 0.44
Nodes (5): build_report_query(), reports(), safe_csv_cell(), with_percent(), pagination_values()

### Community 6 - "Code Community 6"
Cohesion: 0.67
Nodes (5): column_exists(), main(), run_if_needed(), run_migrations(), split_sql_statements()

## Knowledge Gaps
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_db_connection()` connect `Code Community 0` to `Code Community 1`, `Code Community 2`, `Code Community 4`?**
  _High betweenness centrality (0.221) - this node is a cross-community bridge._
- **Why does `SecurityAndHelperTests` connect `Code Community 3` to `Code Community 8`, `Code Community 2`, `Code Community 4`, `Code Community 5`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `FakeCursor` connect `Code Community 5` to `Code Community 8`, `Code Community 4`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **What connects `Populate the Demo Organization with deterministic, realistic test data.` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Code Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.13043478260869565 - nodes in this community are weakly interconnected._