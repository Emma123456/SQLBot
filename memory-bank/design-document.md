# 行权限规则分配增强 — 角色与部门支持设计文档

## 0. 项目背景

### 技术栈

→ 详见 [tech-stack.md](tech-stack.md)

核心组合：FastAPI + SQLModel + PostgreSQL（后端） / Vue 3 + Element Plus + Vite（前端） / sqlbot-xpack（商业扩展包）

### 核心权限表结构

| 表名 | 作用 |
|------|------|
| `system_variable` | 系统变量定义（内置3个：name/account/email；支持自定义；已扩展 value_type/match_mode） |
| `ds_permission` | 单条行/列权限规则，含 `expression_tree`（JSON过滤树） |
| `ds_rules` | 规则组，`permission_list` 关联多条权限，`user_list` 分配给多个用户（本设计扩展 `role_list`/`dept_list`） |
| `sys_user` | 用户表，含 `system_variables` JSONB（变量绑定+扩展属性），本设计新增 `role_ids`/`dept_ids` |

### 行权限运行时流程

1. 用户发起查询
2. `permission.py:get_row_permission_filters()` 找出与当前用户匹配的权限规则（当前通过 `ds_rules.user_list` 匹配 `current_user.id`；本设计扩展为同时匹配 `role_list` 和 `dept_list`）
3. 每条规则的 `expression_tree` 由 `row_permission.py:transFilterTree()` 转换为 SQL WHERE 片段
4. WHERE 片段注入最终查询

### 变量类型与取值逻辑

**系统变量**（`type=system`）：
- 内置：`value = ["name"]` / `["account"]` / `["email"]`，运行时由 `getSysVariableValue()` 映射到 `current_user.name` 等
- 用户属性（✅ 已完成）：`value_type=user_attr`，运行时从 `current_user.system_variables` 中按 key 取值

**自定义变量**（`type=custom`）：
- `value = ["华南区","华北区"]` — 候选值范围
- 用户绑定值存在 `sys_user.system_variables[].variableValues`
- 运行时取用户实际绑定的值

### 关键源文件索引

| 文件 | 作用 |
|------|------|
| `backend/apps/datasource/crud/row_permission.py` | 核心：表达式树 → SQL WHERE（✅ 已扩展 user_attr/list/match_mode） |
| `backend/apps/datasource/crud/permission.py` | 查询时拉取适用行权限（本设计需重构匹配逻辑） |
| `backend/apps/system/models/system_variable_model.py` | SystemVariable 模型（✅ 已扩展 value_type/match_mode） |
| `backend/apps/system/crud/system_variable.py` | 变量 CRUD |
| `backend/apps/system/api/variable_api.py` | 变量 API |
| `backend/alembic/versions/064_system_variable.py` | 变量表原始迁移 |
| `backend/alembic/versions/067_system_variable_value_type.py` | 变量表扩展迁移（✅ 已完成） |
| `frontend/src/views/system/variables/index.vue` | 变量管理页面（✅ 已扩展 list/user_attr/match_mode） |
| `frontend/src/views/system/permission/auth-tree/FilterFiled.vue` | 行权限过滤条件配置（✅ 已扩展 list 操作符锁定/user_attr 标签） |
| `frontend/src/views/system/permission/auth-tree/RowAuth.vue` | 行权限表达式树编辑 |
| `frontend/src/views/system/permission/index.vue` | 权限配置主页（本设计需扩展 Tab 选择） |
| `frontend/src/views/system/permission/SelectPermission.vue` | 用户选择组件（现有） |
| `frontend/src/views/system/permission/options.ts` | 操作符与系统参数枚举 |

---

## 1. 背景与现状

SQLBot 的行权限系统通过 `ds_rules` 表将权限规则分配给用户，`user_list` 字段存储用户 ID 的 JSON 数组。当前存在以下限制：

| 场景 | 当前支持 | 痛点 |
|------|---------|------|
| 给"销售"角色所有用户分配规则 | ❌ 必须逐个添加用户 | 规模化不可行 |
| 给"华南区"部门分配规则 | ❌ 不支持 | 无法实现部门级过滤 |
| 新员工入职到某部门 | ❌ 管理员必须手动将其加入每条规则 | 易遗漏、工作量大 |
| 从钉钉/企微同步角色和部门 | ❌ 无角色/部门模型 | 外部组织数据无法利用 |

## 2. 目标

1. **完整实体表**：创建 `sys_role` 和 `sys_department`，配备完整的 CRUD 管理页面
2. **用户-角色/部门关系**：多对多关联表
3. **权限规则分配**：扩展 `ds_rules` 支持按角色和部门分配规则（同时保留用户分配）
4. **运行时匹配**：用户查询时，匹配规则条件为 `用户ID ∈ user_list` OR `任一角色ID ∈ role_list` OR `任一部门ID ∈ dept_list`
5. **外部同步**：设计同步接口，支持从钉钉、企微、LDAP 等外部源拉取用户、角色、部门
6. **前台管理**：角色 CRUD、部门树 CRUD、用户-角色/部门分配、权限规则分配到角色/部门的管理界面

---

## 3. 数据模型

### 3.0 已完成基础设施（✅ 已实现）

以下功能已在上一轮迭代中完成，是本设计的基础设施：

#### `system_variable` 表 — 已扩展字段

| 字段 | 类型 | 默认值 | 说明 | 状态 |
|------|------|--------|------|------|
| `value_type` | varchar(64) | `fixed` | 值来源：`fixed`=固定候选值 / `user_attr`=用户扩展属性 | ✅ 已完成 |
| `match_mode` | varchar(64) | `in` | 匹配模式：`in`=IN 子句 / `like`=LIKE OR 子句 | ✅ 已完成 |

- 迁移文件：`067_system_variable_value_type.py`
- 模型文件：`system_variable_model.py`

#### `var_type` 新增枚举值

| 类型 | 含义 | value 格式 | 状态 |
|------|------|-----------|------|
| `text` | 文本 | `["val1", "val2", ...]` 候选列表 | 原有 |
| `number` | 数值范围 | `[min, max]` | 原有 |
| `datetime` | 日期范围 | `["start", "end"]` | 原有 |
| `list` | 字符串数组 | `["v1", "v2", ...]` 候选列表，拼 SQL 强制 IN | ✅ 已完成 |

#### `sys_user.system_variables` JSONB — 已支持扩展属性

`system_variables` 字段现已支持两种格式的混合存储：

- **变量绑定**：`{variableId: 10, variableValues: ["华南区"]}` — 用户手动绑定自定义变量值
- **扩展属性**：`{key: "area", value: "10000"}` — 管理员为用户设置的任意 key-value 对，供 `user_attr` 类型变量运行时取值

#### 后端 SQL 拼接逻辑 — 已增强（`row_permission.py`）

| 功能 | 说明 | 状态 |
|------|------|------|
| `user_attr` 取值 | `getSysVariableValue()` 新增 `user_attr` 分支，从 `current_user.system_variables` 按 key 取值 | ✅ 已完成 |
| `list` 类型 IN 子句 | `transTreeItem()` 对 `list` 类型强制使用 IN 操作符，支持 sqlServer nvarchar | ✅ 已完成 |
| `user_attr + list` 逗号多值 | 逗号分隔值拆分为数组，按 `match_mode` 生成 IN 或 LIKE OR | ✅ 已完成 |
| `match_mode` 匹配 | `in`→`field IN ('v1','v2')`；`like`→`(field LIKE '%v1%' OR field LIKE '%v2%')` | ✅ 已完成 |
| `user_attr` 取不到值 | 规则静默跳过，不报错、不过滤 | ✅ 已完成 |

#### 前端已完成的改动

| 页面 | 改动 | 状态 |
|------|------|------|
| `variables/index.vue` | 新增 `list` 类型、值来源切换（fixed/user_attr）、匹配模式选项 | ✅ 已完成 |
| `user/User.vue` | 用户编辑表单新增"扩展属性"区块，支持 key-value 对；`user_attr` 变量显示只读提示 | ✅ 已完成 |
| `permission/auth-tree/FilterFiled.vue` | `list` 变量自动锁定操作符；`user_attr` 显示"用户属性"标签 | ✅ 已完成 |
| i18n 三文件 | zh-CN / en / zh-TW 均已补全 | ✅ 已完成 |

#### 已验证的端到端场景

用户 `fengtaiquadmin` 配置扩展属性 `area=10000`，行权限变量"区域"（`value_type=user_attr`, `value=['area']`）生效，查询时 SQL 正确附加 `area = '10000'` 条件。

---

### 3.1 新增表

#### `sys_role`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInteger (雪花ID) | 主键 |
| `name` | varchar(128) | 角色名称（唯一） |
| `code` | varchar(128) | 角色编码，用于外部同步映射（唯一） |
| `description` | varchar(512) | 描述（可选） |
| `origin` | int | 来源：0=手动, 1=钉钉, 2=企微, 3=LDAP |
| `create_time` | BigInteger | 创建时间戳 |

#### `sys_department`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInteger (雪花ID) | 主键 |
| `name` | varchar(128) | 部门名称 |
| `code` | varchar(128) | 部门编码，用于外部同步映射（唯一） |
| `parent_id` | BigInteger | 父部门ID（0=根节点） |
| `origin` | int | 来源：0=手动, 1=钉钉, 2=企微, 3=LDAP |
| `create_time` | BigInteger | 创建时间戳 |

**部门层级**：`parent_id` 支持树形结构。v1 中规则分配到部门时，**仅匹配该部门本身**，不隐式继承子部门（未来可扩展 `include_children` 标志）。

#### `sys_user_role`（关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInteger (雪花ID) | 主键 |
| `uid` | BigInteger | → `sys_user.id` |
| `role_id` | BigInteger | → `sys_role.id` |

唯一约束：`(uid, role_id)`

#### `sys_user_dept`（关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigInteger (雪花ID) | 主键 |
| `uid` | BigInteger | → `sys_user.id` |
| `dept_id` | BigInteger | → `sys_department.id` |
| `is_primary` | boolean | 是否为主部门 |

唯一约束：`(uid, dept_id)`

### 3.2 修改表

#### `ds_rules` — 新增字段

| 新字段 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `role_list` | Text (JSON) | `[]` | 角色 ID 数组，如 `[3, 7]` |
| `dept_list` | Text (JSON) | `[]` | 部门 ID 数组，如 `[2, 5]` |

> `user_list` 保留，向后兼容。一条规则可以同时指定用户、角色、部门的任意组合。

#### `sys_user` — 新增冗余字段

| 新字段 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `role_ids` | JSONB | `[]` | 冗余的角色 ID 数组，用于运行时快速查找 |
| `dept_ids` | JSONB | `[]` | 冗余的部门 ID 数组，用于运行时快速查找 |

**冗余设计理由**：运行时权限检查在每次查询时执行，如果每次都 JOIN `sys_user_role`/`sys_user_dept` 会增加数据库开销。将 `role_ids`/`dept_ids` 冗余存储在 `sys_user` 上，与现有 `system_variables` JSONB 字段的设计模式一致。每当用户-角色/部门关联变更时，同步刷新冗余字段。

---

## 4. 运行时匹配逻辑

### 4.1 当前逻辑（`permission.py`）

```python
u_list = json.loads(r.user_list)
if permission.id in p_list and current_user.id in u_list:
    flag = True
```

### 4.2 新增逻辑

```python
def match_rule(rule: DsRules, current_user: CurrentUser, permission_id: int) -> bool:
    p_list = json.loads(rule.permission_list)
    if p_list is None or permission_id not in p_list:
        return False

    # 检查 user_list
    u_list = json.loads(rule.user_list) if rule.user_list else []
    if current_user.id in u_list or f'{current_user.id}' in u_list:
        return True

    # 检查 role_list
    r_list = json.loads(rule.role_list) if getattr(rule, 'role_list', None) else []
    if r_list and current_user.role_ids:
        if any(rid in current_user.role_ids for rid in r_list):
            return True

    # 检查 dept_list
    d_list = json.loads(rule.dept_list) if getattr(rule, 'dept_list', None) else []
    if d_list and current_user.dept_ids:
        if any(did in current_user.dept_ids for did in d_list):
            return True

    return False
```

**匹配语义**：用户满足三个条件中的**任意一个**即匹配（用户 OR 角色 OR 部门），与当前设计的逻辑一致。

### 4.3 UserInfoDTO 扩展

`current_user` 对象（`UserInfoDTO`）必须包含 `role_ids` 和 `dept_ids`，以便匹配逻辑访问。认证中间件构建 `current_user` 时需要从 `sys_user` 的冗余字段填充这些值。

---

## 5. 后端 API 设计

### 5.1 角色管理（`/api/role`）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/role` | 角色列表 | admin |
| GET | `/role/{id}` | 角色详情 | admin |
| POST | `/role` | 创建角色 | admin |
| PUT | `/role` | 更新角色 | admin |
| DELETE | `/role/{id}` | 删除角色 | admin |
| GET | `/role/{id}/users` | 角色下的用户列表 | admin |
| POST | `/role/{id}/users` | 批量分配用户到角色 | admin |
| DELETE | `/role/{id}/users` | 批量移除角色的用户 | admin |

### 5.2 部门管理（`/api/department`）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/department/tree` | 获取部门树 | admin |
| GET | `/department/{id}` | 部门详情 | admin |
| POST | `/department` | 创建部门 | admin |
| PUT | `/department` | 更新部门 | admin |
| DELETE | `/department/{id}` | 删除部门（须为叶子节点） | admin |
| GET | `/department/{id}/users` | 部门下的用户列表 | admin |
| POST | `/department/{id}/users` | 批量分配用户到部门 | admin |
| DELETE | `/department/{id}/users` | 批量移除部门的用户 | admin |

### 5.3 用户 API 扩展（`/api/user`）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| PUT | `/user/{id}/roles` | 设置用户的角色 | admin |
| PUT | `/user/{id}/departments` | 设置用户的部门 | admin |

### 5.4 权限规则 API 扩展（`/api/permission`）

现有 `savePermissions` 接口接受 `users: [id1, id2, ...]`，扩展为：

```json
{
  "id": 1,
  "name": "规则组名称",
  "permissions": [...],
  "users": [1, 5, 12],
  "roles": [3, 7],
  "departments": [2, 5]
}
```

### 5.5 外部同步 API（`/api/sync`）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/sync/{origin}/users` | 同步用户 | admin |
| POST | `/sync/{origin}/roles` | 同步角色 | admin |
| POST | `/sync/{origin}/departments` | 同步部门 | admin |
| POST | `/sync/{origin}/user-roles` | 同步用户-角色关系 | admin |
| POST | `/sync/{origin}/user-departments` | 同步用户-部门关系 | admin |

`origin` 取值：`1=钉钉`, `2=企微`, `3=LDAP`

每个同步接口接受标准化载荷，执行 **upsert** 逻辑（`code` 不存在则创建，已存在则更新名称）。同步完成后刷新受影响用户的冗余字段。

---

## 6. 冗余字段维护

每当用户-角色或用户-部门关联变更时，必须刷新 `sys_user` 上的 `role_ids`/`dept_ids`。

### 触发点

1. **给角色分配/移除用户** → 刷新受影响用户的 `role_ids`
2. **给部门分配/移除用户** → 刷新受影响用户的 `dept_ids`
3. **删除角色** → 清理 `sys_user_role`，刷新受影响用户的 `role_ids`
4. **删除部门** → 清理 `sys_user_dept`，刷新受影响用户的 `dept_ids`
5. **外部同步** → 同步完成后批量刷新

### 刷新函数

```python
def refresh_user_role_ids(session: Session, uid: int):
    user = session.get(UserModel, uid)
    if user:
        role_ids = session.exec(
            select(SysUserRole.role_id).where(SysUserRole.uid == uid)
        ).all()
        user.role_ids = list(role_ids)
        session.add(user)

def refresh_user_dept_ids(session: Session, uid: int):
    user = session.get(UserModel, uid)
    if user:
        dept_rows = session.exec(
            select(SysUserDept.dept_id).where(SysUserDept.uid == uid)
        ).all()
        user.dept_ids = list(dept_rows)
        session.add(user)
```

---

## 7. 前端设计

### 7.1 新增管理页面

#### 角色管理（`/system/role/index.vue`）

- **列表视图**：表格，列：角色名称、编码、描述、用户数、来源、操作（编辑/删除）
- **创建/编辑弹窗**：表单含 name、code、description 字段
- **用户分配**：点击角色 → 抽屉展示已分配用户，支持添加/移除（复用 `SelectPermission.vue` 模式）

#### 部门管理（`/system/department/index.vue`）

- **树形视图**：`el-tree` 组件展示部门层级
- **创建/编辑弹窗**：表单含 name、code、parent_id 选择器
- **用户分配**：点击部门 → 抽屉展示已分配用户，支持添加/移除
- **来源标记**：外部同步的部门显示"钉钉"/"企微"标签

### 7.2 修改页面

#### 用户管理（`/system/user/User.vue`）

- 用户编辑表单新增"角色"和"部门"区块
- 角色：多选下拉框，数据源 `GET /role`
- 部门：树形选择器，数据源 `GET /department/tree`
- 用户列表表格展示角色/部门信息（Tag 形式）

#### 权限配置（`/system/permission/index.vue`）

**步骤二"选择受限用户"改为"选择目标"，3 个 Tab：**

| Tab | 组件 | 数据源 |
|-----|------|--------|
| 用户 | 现有 `SelectPermission.vue` | `workspaceUserList` API |
| 角色 | 新增 `SelectRole.vue` | `GET /role` API |
| 部门 | 新增 `SelectDepartment.vue`（带复选框的树） | `GET /department/tree` API |

**卡片展示**：规则组卡片显示计数 `3 用户, 2 角色, 1 部门`

**保存载荷**：

```json
{
  "id": 1,
  "name": "华南区数据规则",
  "permissions": [...],
  "users": [1, 5],
  "roles": [3, 7],
  "departments": [2]
}
```

---

## 8. 外部同步架构

### 8.1 同步策略

每个外部平台（钉钉、企微、LDAP）提供适配器，实现统一接口：

```python
class SyncAdapter(ABC):
    @abstractmethod
    async def get_departments(self) -> list[SyncDepartment]: ...

    @abstractmethod
    async def get_roles(self) -> list[SyncRole]: ...

    @abstractmethod
    async def get_users(self) -> list[SyncUser]: ...

    @abstractmethod
    async def get_user_roles(self) -> list[SyncUserRole]: ...

    @abstractmethod
    async def get_user_departments(self) -> list[SyncUserDept]: ...
```

### 8.2 标准化同步模型

```python
class SyncDepartment(BaseModel):
    code: str          # 外部唯一ID（如钉钉 dept_id）
    name: str
    parent_code: str   # 父节点外部ID，空串表示根

class SyncRole(BaseModel):
    code: str          # 外部唯一ID（如钉钉 role_id）
    name: str

class SyncUser(BaseModel):
    code: str          # 外部唯一用户ID
    name: str
    email: str
    role_codes: list[str] = []
    dept_codes: list[str] = []
```

### 8.3 同步流程

1. 管理员点击"从钉钉同步"（或定时任务触发）
2. 后端调用钉钉适配器 → 获取部门、角色、用户及其映射关系
3. **Upsert 部门**：按 `code` 匹配，新建或更新名称
4. **Upsert 角色**：按 `code` 弹配，同上
5. **Upsert 用户**：按 `sys_user_platform.platform_uid` 匹配，更新 name/email
6. **更新用户-角色映射**：清除受影响用户的 `sys_user_role` 记录，插入新映射
7. **更新用户-部门映射**：清除受影响用户的 `sys_user_dept` 记录，插入新映射
8. **刷新冗余字段**：批量刷新受影响用户的 `role_ids`/`dept_ids`
9. 返回同步摘要：`{created: N, updated: M, deleted: 0}`

### 8.4 前端同步 UI

扩展现有 `SyncUserDing.vue` 为标签页对话框：

| Tab | 说明 |
|-----|------|
| 用户 | 现有功能（从组织树选择用户） |
| 部门 | 开关：同步全部 / 选择特定部门 |
| 角色 | 开关：同步全部 / 选择特定角色 |

或添加"全量同步"按钮，一键同步所有数据。

---

## 9. 数据库迁移计划

```python
# 068_role_department_tables.py

def upgrade():
    # sys_role
    op.create_table('sys_role',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('code', sa.String(128), nullable=False),
        sa.Column('description', sa.String(512), nullable=True),
        sa.Column('origin', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('create_time', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code')
    )

    # sys_department
    op.create_table('sys_department',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('code', sa.String(128), nullable=False),
        sa.Column('parent_id', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('origin', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('create_time', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # sys_user_role
    op.create_table('sys_user_role',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('uid', sa.BigInteger(), nullable=False),
        sa.Column('role_id', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uid', 'role_id')
    )

    # sys_user_dept
    op.create_table('sys_user_dept',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('uid', sa.BigInteger(), nullable=False),
        sa.Column('dept_id', sa.BigInteger(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uid', 'dept_id')
    )

    # ds_rules 新增字段
    op.add_column('ds_rules', sa.Column('role_list', sa.Text(), nullable=True, server_default='[]'))
    op.add_column('ds_rules', sa.Column('dept_list', sa.Text(), nullable=True, server_default='[]'))

    # sys_user 新增冗余字段
    op.add_column('sys_user', sa.Column('role_ids', sa.JSONB(), nullable=True, server_default='[]'))
    op.add_column('sys_user', sa.Column('dept_ids', sa.JSONB(), nullable=True, server_default='[]'))
```

---

## 10. 实施步骤

### 第一阶段：后端基础（模型与迁移）

| 步骤 | 文件 | 说明 |
|------|------|------|
| 1.1 | `backend/apps/system/models/role_model.py` | 新建 `SysRole`、`SysUserRole` 模型 |
| 1.2 | `backend/apps/system/models/department_model.py` | 新建 `SysDepartment`、`SysUserDept` 模型 |
| 1.3 | `backend/apps/system/models/user.py` | 新增 `role_ids`、`dept_ids` 字段 |
| 1.4 | `backend/alembic/versions/068_role_department_tables.py` | 迁移文件 |
| 1.5 | `backend/apps/system/schemas/system_schema.py` | DTO 中新增 `role_ids`、`dept_ids` |

### 第二阶段：后端 CRUD API

| 步骤 | 文件 | 说明 |
|------|------|------|
| 2.1 | `backend/apps/system/crud/role.py` | 角色 CRUD + 用户分配 |
| 2.2 | `backend/apps/system/crud/department.py` | 部门 CRUD + 用户分配 |
| 2.3 | `backend/apps/system/api/role.py` | 角色 REST API |
| 2.4 | `backend/apps/system/api/department.py` | 部门 REST API |
| 2.5 | `backend/apps/system/api/user.py` | 扩展用户创建/更新，支持角色部门 |
| 2.6 | `backend/apps/api.py` | 注册新路由 |

### 第三阶段：权限匹配逻辑

| 步骤 | 文件 | 说明 |
|------|------|------|
| 3.1 | `backend/apps/datasource/crud/permission.py` | 重构匹配逻辑支持 role_list 和 dept_list |
| 3.2 | `backend/apps/system/schemas/system_schema.py` | 确保 `UserInfoDTO` 包含 `role_ids`/`dept_ids` |
| 3.3 | 认证中间件 | 构建 current_user 时填充 `role_ids`/`dept_ids` |

### 第四阶段：前端管理页面

| 步骤 | 文件 | 说明 |
|------|------|------|
| 4.1 | `frontend/src/views/system/role/index.vue` | 角色管理页（CRUD + 用户分配） |
| 4.2 | `frontend/src/views/system/department/index.vue` | 部门管理页（树形 CRUD + 用户分配） |
| 4.3 | `frontend/src/views/system/user/User.vue` | 用户编辑表单新增角色/部门选择器 |
| 4.4 | `frontend/src/api/role.ts` | 角色 API 客户端 |
| 4.5 | `frontend/src/api/department.ts` | 部门 API 客户端 |
| 4.6 | `frontend/src/router/` | 新增角色/部门路由 |

### 第五阶段：权限规则分配 UI

| 步骤 | 文件 | 说明 |
|------|------|------|
| 5.1 | `frontend/src/views/system/permission/SelectRole.vue` | 角色选择组件 |
| 5.2 | `frontend/src/views/system/permission/SelectDepartment.vue` | 部门树选择组件 |
| 5.3 | `frontend/src/views/system/permission/index.vue` | 步骤二改为用户/角色/部门 Tab 选择 |
| 5.4 | `frontend/src/views/system/permission/Card.vue` | 卡片展示用户/角色/部门计数 |
| 5.5 | `frontend/src/api/permissions.ts` | 扩展保存载荷支持 roles/departments |

### 第六阶段：外部同步

| 步骤 | 文件 | 说明 |
|------|------|------|
| 6.1 | `backend/apps/system/sync/adapter.py` | 同步适配器基类 |
| 6.2 | `backend/apps/system/sync/dingtalk.py` | 钉钉适配器实现 |
| 6.3 | `backend/apps/system/api/sync.py` | 同步 API 端点 |
| 6.4 | `frontend/src/views/system/user/SyncUserDing.vue` | 扩展部门/角色同步 Tab |

### 第七阶段：国际化与完善

| 步骤 | 文件 | 说明 |
|------|------|------|
| 7.1 | `frontend/src/i18n/zh-CN.json` | 补全角色/部门/同步相关文案 |
| 7.2 | `frontend/src/i18n/en.json` | 英文翻译 |
| 7.3 | `frontend/src/i18n/zh-TW.json` | 繁体中文翻译 |

---

## 11. 改动文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `backend/apps/system/models/system_variable_model.py` | 修改（✅ 已完成） | 新增 `value_type`、`match_mode` 字段 |
| `backend/alembic/versions/067_system_variable_value_type.py` | 新增（✅ 已完成） | 数据库迁移：加 `value_type`、`match_mode` 列 |
| `backend/apps/datasource/crud/row_permission.py` | 修改（✅ 已完成） | `user_attr+list` 支持逗号多值；按 `match_mode` 生成 IN 或 LIKE OR |
| `frontend/src/views/system/variables/index.vue` | 修改（✅ 已完成） | 新增 `list` 类型、值来源切换、匹配模式选项 |
| `frontend/src/views/system/user/User.vue` | 修改（✅ 已完成） | 新增扩展属性区块、user_attr 只读提示 |
| `frontend/src/views/system/permission/auth-tree/FilterFiled.vue` | 修改（✅ 已完成） | list 变量自动锁定操作符；user_attr 显示标签 |
| `frontend/src/i18n/zh-CN.json` | 修改（✅ 已完成） | 变量扩展相关文案 |
| `frontend/src/i18n/en.json` | 修改（✅ 已完成） | 变量扩展相关文案 |
| `frontend/src/i18n/zh-TW.json` | 修改（✅ 已完成） | 变量扩展相关文案 |
| `backend/apps/system/models/role_model.py` | **新建** | `SysRole`、`SysUserRole` 模型 |
| `backend/apps/system/models/department_model.py` | **新建** | `SysDepartment`、`SysUserDept` 模型 |
| `backend/apps/system/models/user.py` | 修改 | 新增 `role_ids`、`dept_ids` JSONB 字段 |
| `backend/apps/system/schemas/system_schema.py` | 修改 | DTO 新增角色/部门字段 |
| `backend/alembic/versions/068_role_department_tables.py` | **新建** | 迁移：建表 + 加字段 |
| `backend/apps/system/crud/role.py` | **新建** | 角色 CRUD 逻辑 |
| `backend/apps/system/crud/department.py` | **新建** | 部门 CRUD 逻辑 |
| `backend/apps/system/api/role.py` | **新建** | 角色 REST API |
| `backend/apps/system/api/department.py` | **新建** | 部门 REST API |
| `backend/apps/system/api/user.py` | 修改 | 扩展创建/更新支持角色/部门 |
| `backend/apps/system/api/sync.py` | **新建** | 外部同步 API |
| `backend/apps/system/sync/adapter.py` | **新建** | 同步适配器基类 |
| `backend/apps/system/sync/dingtalk.py` | **新建** | 钉钉适配器 |
| `backend/apps/datasource/crud/permission.py` | 修改 | 按角色/部门匹配规则 |
| `backend/apps/api.py` | 修改 | 注册新路由 |
| `frontend/src/views/system/role/index.vue` | **新建** | 角色管理页 |
| `frontend/src/views/system/department/index.vue` | **新建** | 部门管理页 |
| `frontend/src/views/system/permission/SelectRole.vue` | **新建** | 角色选择组件 |
| `frontend/src/views/system/permission/SelectDepartment.vue` | **新建** | 部门树选择组件 |
| `frontend/src/views/system/permission/index.vue` | 修改 | Tab 式目标选择 |
| `frontend/src/views/system/permission/Card.vue` | 修改 | 展示角色/部门计数 |
| `frontend/src/views/system/user/User.vue` | 修改 | 新增角色/部门字段 |
| `frontend/src/views/system/user/SyncUserDing.vue` | 修改 | 扩展角色/部门同步 |
| `frontend/src/api/role.ts` | **新建** | 角色 API 客户端 |
| `frontend/src/api/department.ts` | **新建** | 部门 API 客户端 |
| `frontend/src/i18n/*.json` | 修改 | 角色部门三语言补全（变量扩展部分 ✅ 已完成） |

---

## 12. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| **冗余数据漂移** | `sys_user` 上的 `role_ids`/`dept_ids` 与关联表不同步 | 每个变更路径（CRUD、同步、删除）都调用刷新函数。未来可加定期一致性检查任务 |
| **向后兼容** | 现有 `ds_rules` 无 `role_list`/`dept_list` | 默认 `[]`，现有规则行为不变 |
| **部门删除有子节点** | 子部门变为孤立 | v1 仅允许删除叶子节点。未来支持递归重分配或级联 |
| **同步冲突** | 外部源重命名/删除了被权限规则引用的实体 | 同步仅新增/更新，不自动删除被 `ds_rules.role_list`/`dept_list` 引用的实体，改为标记"已失效" |
| **性能** | 每次规则检查 `json.loads()` 解析 `role_list`/`dept_list` | 冗余字段避免 JOIN；小数组 JSON 解析开销极低。大规模部署可改用 JSONB 包含查询 |
| **xpack 兼容性** | `DsRules` 模型在编译 .so 中，无法直接访问新字段 | 新增列可正常添加（ORM 忽略未知列）。读取 `role_list`/`dept_list` 可能需 `getattr()` 降级或原生列访问 |

---

## 13. 待确认问题

1. **部门继承**：分配到父部门的规则是否自动适用于子部门？（建议 v1 不支持，后续加 `include_children` 标志）
2. **角色层级**：是否需要角色继承（如"超级管理员"继承"管理员"权限）？（建议 v1 不支持，扁平角色列表）
3. **Excel 批量导入**：用户 Excel 导入模板是否支持角色/部门列？（建议支持，新增 `role_code` 和 `dept_code` 列）
4. **审计日志**：角色/部门分配变更是否需要记录审计日志？（建议需要，复用 `@system_log` 装饰器）
5. **xpack 模型访问**：`DsRules` 模型编译在 xpack 中，能否读取新增的 `role_list`/`dept_list`？如果不能，需使用 `getattr()` 降级或原生 SQL 列访问
