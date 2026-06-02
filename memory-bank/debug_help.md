# Debug Help — Permission & Question Service

Quick reference for locating permission configuration and question-service code paths.

---

## 1. Permission Configuration (Frontend)

### Entry Page
- **File**: `frontend/src/views/system/permission/index.vue`
- **Route**: `/set/permission`
- **Data flow**:
  1. `getList()` → `/api/v1/ds_permission/list` → returns array of permission groups
  2. Each item in the list is a `ds_rules` row; `item.id` = `ds_rules.id`, `item.permissions` = array of `ds_permission` rows
  3. `getAllRuleTargets()` → `/api/v1/permission-rule/targets` → returns `role_list`, `dept_list`, `user_list` for all rules
  4. `getAllRuleTargets()` → `permissionTargetsMap` (keyed by `ds_rules.id`)

### Key Data Structures
- `ruleTargetsMap`: `Map<ds_rules.id → {roles, departments, users}>` — raw targets data
- `permissionTargetsMap`: `Map<ds_rules.id → {roles, departments, users}>` — same data, keyed by `perm.id` (which IS `ds_rules.id` from `getList()`)

### Save Flow (Create/Edit Permission Group)
1. Frontend calls `savePermissions(obj)` → `/api/v1/ds_permission/save` (xpack compiled `.so`)
2. xpack save returns `{code:0, data:{id: realDsRulesId, ...}}`; frontend `request.ts` auto-unwraps to `data.id`
3. Frontend then calls `updateRuleTargets(realId, {roles, departments, users})` → `PUT /api/v1/permission-rule/{rule_id}/targets`
4. Backend uses raw SQL: `UPDATE ds_rules SET role_list=:role_list, dept_list=:dept_list, user_list=:user_list WHERE id=:id`

### Set User (Edit Restricted Objects)
- Dialog: `SelectPermission.vue` with tabs: Users / Roles / Departments
- Opens via `setUser(row)` → reads current targets from `ruleTargetsMap[String(row.id)]`
- Saves via `updateRuleTargets` (same as save flow step 3)

### Card Display
- **File**: `frontend/src/views/system/permission/Card.vue`
- Shows `roleCount`, `deptCount`, user count from `permissionTargetsMap[String(ele.id)]`

### Frontend API Definitions
- **File**: `frontend/src/api/permissions.ts`
  - `RuleTargets`: `{roles: (number|string)[], departments: (number|string)[], users: (number|string)[]}`
  - `RuleTargetsResponse`: `{rule_id, roles, departments, users}`
  - `updateRuleTargets(ruleId, targets)` → `PUT /api/v1/permission-rule/{ruleId}/targets`
  - `getAllRuleTargets()` → `GET /api/v1/permission-rule/targets`

### Known Bugs (Fixed)
| Bug | Cause | Fix |
|-----|-------|-----|
| ID collision: ds_rules id=10 showed "2 角色" | `permissionTargetsMap` used `ds_permission.id` to lookup `ruleTargetsMap` keyed by `ds_rules.id` | Direct lookup by `perm.id` (= `ds_rules.id`) |
| New group targets never saved | Frontend used `+new Date()` temp ID for `updateRuleTargets` | Use `res?.id || id` from xpack save response |
| `user_list` never populated | Backend/API/frontend didn't include `users` field | Added `users` end-to-end |

---

## 2. Permission Configuration (Backend)

### API Endpoints
- **File**: `backend/apps/datasource/api/permission_rule.py`
- `PUT /{rule_id}/targets` — update `role_list`, `dept_list`, `user_list` via raw SQL
- `GET /targets` — read all rules' targets via raw SQL
- `GET /{rule_id}/targets` — read single rule's targets via raw SQL
- **Why raw SQL**: xpack `DsRules` model (compiled `.so`) does NOT expose `role_list`, `dept_list`, `user_list` as Python attributes

### Models
- `RuleTargetsUpdate`: `{roles: List[int], departments: List[int], users: List[int]}`
- `RuleTargetsResponse`: `{rule_id: int, roles: List[int], departments: List[int], users: List[int]}`

### xpack Save Endpoint (Cannot Modify)
- `/api/v1/ds_permission/save` — registered via `sqlbot_xpack.init_fastapi_app(app)` in `main.py`
- Returns `{code:0, data:{id: dsRulesId, oid, name, user_list:"[]", permission_list:"[7]"}}`
- Frontend `request.ts` auto-unwraps: when `code===0`, returns `response.data.data`

---

## 3. Permission Enforcement (Runtime Matching)

### Entry Function
- **File**: `backend/apps/datasource/crud/permission.py`
- `get_row_permission_filters(session, current_user, ds, tables)` — called by both chat and datasource preview
- `get_column_permission_fields(session, current_user, table, fields, contain_rules)` — column-level filtering

### `_load_rule_targets()` — Raw SQL Pre-loading
```python
# SELECT id, role_list, dept_list, user_list FROM ds_rules
# Returns Dict[int, Tuple[role_list, dept_list, user_list]]
```
- Must use raw SQL because xpack DsRules model lacks these attributes

### `match_rule()` — Three-Dimension Matching (OR semantics)
```python
# 1. permission_id must be in rule.permission_list
# 2. Then OR-check: user_list OR role_list OR dept_list
#    - user_list: current_user.id in u_list (int or string compat)
#    - role_list: any(rid in user_role_ids or f'{rid}' in user_role_strs for rid in r_list)
#    - dept_list: any(did in user_dept_ids or f'{did}' in user_dept_strs for did in d_list)
```
- String/int ID compatibility: `json.loads` may produce int or string IDs depending on how they were stored

### `is_normal_user()` Gate
- `is_normal_user(current_user)` = `current_user.id != 1`
- Admin (id=1) bypasses all permission checks

### CurrentUser Data
- **File**: `backend/apps/system/schemas/system_schema.py` → `UserInfoDTO`
- Fields: `role_ids: list[int]`, `dept_ids: list[int]`, `isAdmin: bool`
- **Populated by**: `backend/apps/system/crud/user.py` → `get_user_info()`
- **Set by middleware**: `backend/apps/system/middleware/auth.py` → `request.state.current_user = UserInfoDTO`
- `UserModel` (`backend/apps/system/models/user.py`) stores `role_ids` and `dept_ids` as JSONB columns in `sys_user` table

---

## 4. Chat Question Service (问数请求)

### Frontend Entry
- **File**: `frontend/src/views/chat/index.vue`
- API: `frontend/src/api/chat.ts` → `Chat`, `ChatRecord`, `ChatMessage` classes

### Backend Entry
- **File**: `backend/apps/chat/api/chat.py` — FastAPI router
- Main class: `backend/apps/chat/task/llm.py` → `LLMTask`

### Question Flow (with Permission WHERE Injection)
```
1. User submits question → /api/v1/chat/question
2. LLMTask.__init__() → setup chat, datasource, config
3. LLM generates SQL (stream)
4. llm.py L1262: check_sql() → extract SQL + table names
5. llm.py L1263-1272: if normal user → generate_filter(session, sql, tables)
   ↓
   permission.py: get_row_permission_filters(session, user, ds, tables)
     → _load_rule_targets() [raw SQL pre-load]
     → match_rule() [3-dimension OR matching]
     → if match → transRecord2DTO(permission) → PermissionDTO
     → transFilterTree() → WHERE fragment from expression_tree
   ↓
6. llm.py L829: build_table_filter() → sends (SQL + filters) to LLM
   → LLM re-writes SQL with WHERE conditions
7. Final SQL saved + executed
```

### Key Line Numbers in llm.py
| Line | Function | Description |
|------|----------|-------------|
| L878 | `generate_filter()` | Entry point for row permission injection |
| L829 | `build_table_filter()` | Sends SQL + filter JSON to LLM for rewriting |
| L1262 | `check_sql()` | Validates and extracts SQL + tables |
| L1272 | `generate_filter()` call | The actual call site in the question flow |
| L1274-1277 | Result handling | If filter applied → `GENERATE_SQL_WITH_PERMISSIONS` |

### WHERE Clause Generation
- **File**: `backend/apps/datasource/crud/row_permission.py`
- `transFilterTree(session, current_user, tree_list, ds)` — converts PermissionDTO list to WHERE string
- `transTreeToWhere()` — recursively processes expression_tree (logic + items)
- `transTreeItem()` — converts individual filter items to SQL fragments
- `getSysVariableValue()` — handles system variables including `role` (→ `current_user.role_ids`) and `department` (→ `current_user.dept_ids`)

### Datasource Preview (Also Uses Permission)
- **File**: `backend/apps/datasource/crud/datasource.py`
- `get_table_preview()` → also calls `get_row_permission_filters()` + `get_column_permission_fields()`
- Directly injects WHERE into preview SQL (no LLM rewriting)

---

## 5. Database Tables

### ds_rules (Permission Group)
| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| name | text | Group name |
| oid | int | Workspace ID |
| permission_list | text/JSON | Array of `ds_permission.id` values |
| role_list | text/JSON | Array of role IDs (restricted objects) |
| dept_list | text/JSON | Array of department IDs (restricted objects) |
| user_list | text/JSON | Array of user IDs (restricted objects) |

### ds_permission (Permission Rule)
| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| table_id | int | References `core_table.id` |
| type | text | 'row' or 'column' |
| expression_tree | JSON | Filter tree structure |
| permissions | JSON | For column type: field enable/disable list |

### sys_user (User)
| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| role_ids | JSONB | Array of role IDs |
| dept_ids | JSONB | Array of department IDs |
| system_variables | JSONB | Extended user attributes |

---

## 6. Quick Debug Checklist

### "Permission targets not saved"
1. Check browser network tab: did `PUT /permission-rule/{id}/targets` return 200?
2. Check DB: `SELECT id, role_list, dept_list, user_list FROM ds_rules WHERE id = ?`
3. Check frontend: did `savePermissions()` return real `ds_rules.id`? (not temp `+new Date()`)

### "Wrong target counts displayed"
1. Check `permissionTargetsMap` key: must use `perm.id` (= `ds_rules.id` from `getList()`)
2. Check `ruleTargetsMap` key: must use `ds_rules.id` (from `getAllRuleTargets()`)
3. Do NOT use `ds_permission.id` as key — it collides with `ds_rules.id`

### "Permission WHERE not applied in question"
1. Check `is_normal_user()`: admin (id=1) bypasses all checks
2. Check `match_rule()`: is `permission_id` in `rule.permission_list`?
3. Check type compatibility: `role_list`/`dept_list` may contain string IDs
4. Check `_load_rule_targets()`: raw SQL must succeed (xpack model has no `role_list` attr)

### "Column permission not working"
1. Same `match_rule()` logic applies to column permissions
2. Check `get_column_permission_fields()` in `permission.py`