# 行权限规则增强 — 角色与部门支持实施计划

本文档提供详细的分步实施指令，供 AI 开发者逐步实现角色与部门权限功能。
**核心原则**：每个功能模块前后端一起完成并测试通过后，再进入下一个模块。

---

## 前置条件

在开始实施前，确认以下环境已就绪：

1. PostgreSQL 数据库可连接且运行正常
2. 后端开发服务器可通过 `uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload` 启动
3. 前端开发服务器可通过 `npm run dev` 启动
4. Alembic 迁移工具配置正确
5. 已阅读并理解 `design-document.md` 和 `tech-stack.md`

---

## 第一阶段：基础设施（模型、迁移、共享工具）

> 本阶段为所有功能模块的共享基础，必须最先完成。

### 步骤 1.1：创建角色模型文件

**文件路径**：`backend/apps/system/models/role_model.py`

**指令**：
1. 创建新文件 `role_model.py`
2. 导入 SQLModel、Field、BigInteger 相关依赖
3. 定义 `SysRole` 模型类，继承 SQLModel 和表模型
4. 配置表名为 `sys_role`
5. 定义以下字段：
   - `id`: BigInteger 主键
   - `name`: varchar(128)，非空，唯一约束
   - `code`: varchar(128)，非空，唯一约束
   - `description`: varchar(512)，可为空
   - `origin`: Integer，非空，默认值 0
   - `create_time`: BigInteger，非空
6. 定义 `SysUserRole` 关联模型类
7. 配置表名为 `sys_user_role`
8. 定义字段：`id`（主键）、`uid`（BigInteger，非空）、`role_id`（BigInteger，非空）
9. 为 `SysUserRole` 添加唯一约束 `(uid, role_id)`

**验证测试**：
- 启动 Python 解释器，导入 `SysRole` 和 `SysUserRole` 类
- 验证可以实例化 `SysRole(id=1, name='test', code='TEST', origin=0, create_time=1234567890)`
- 验证实例化后字段值正确
- 检查模型类包含 `__tablename__` 属性且值为 `sys_role` 和 `sys_user_role`

---

### 步骤 1.2：创建部门模型文件

**文件路径**：`backend/apps/system/models/department_model.py`

**指令**：
1. 创建新文件 `department_model.py`
2. 导入 SQLModel、Field、BigInteger 相关依赖
3. 定义 `SysDepartment` 模型类
4. 配置表名为 `sys_department`
5. 定义字段：
   - `id`: BigInteger 主键
   - `name`: varchar(128)，非空
   - `code`: varchar(128)，非空，唯一约束
   - `parent_id`: BigInteger，非空，默认值 0
   - `origin`: Integer，非空，默认值 0
   - `create_time`: BigInteger，非空
6. 定义 `SysUserDept` 关联模型类
7. 配置表名为 `sys_user_dept`
8. 定义字段：`id`（主键）、`uid`（BigInteger，非空）、`dept_id`（BigInteger，非空）、`is_primary`（Boolean，非空，默认值 False）
9. 为 `SysUserDept` 添加唯一约束 `(uid, dept_id)`

**验证测试**：
- 导入 `SysDepartment` 和 `SysUserDept` 类
- 实例化 `SysDepartment(id=1, name='技术部', code='TECH', parent_id=0, origin=0, create_time=1234567890)`
- 验证实例化后所有字段值正确
- 检查 `is_primary` 默认值为 False

---

### 步骤 1.3：扩展用户模型

**文件路径**：`backend/apps/system/models/user.py`

**指令**：
1. 打开 `user.py` 文件
2. 在 `UserModel` 或 `SysUser` 类中定位字段定义区域
3. 新增字段 `role_ids`，类型为 JSONB，默认值为空数组 `[]`
4. 新增字段 `dept_ids`，类型为 JSONB，默认值为空数组 `[]`
5. 确保这两个字段可为空（nullable=True）

**验证测试**：
- 导入 `UserModel` 类
- 实例化用户对象，不传入 `role_ids` 和 `dept_ids`
- 验证这两个字段的默认值为 `[]` 或 `None`
- 手动传入 `role_ids=[1, 2]` 和 `dept_ids=[3]`，验证赋值成功

---

### 步骤 1.4：创建数据库迁移文件

**文件路径**：`backend/alembic/versions/068_role_department_tables.py`

**指令**：
1. 在 `backend/alembic/versions/` 目录下创建新文件
2. 文件名格式：`068_role_department_tables.py`
3. 定义 `upgrade()` 函数：
   - 使用 `op.create_table()` 创建 `sys_role` 表，包含所有字段和约束
   - 使用 `op.create_table()` 创建 `sys_department` 表，包含所有字段和约束
   - 使用 `op.create_table()` 创建 `sys_user_role` 表，包含唯一约束
   - 使用 `op.create_table()` 创建 `sys_user_dept` 表，包含唯一约束
   - 使用 `op.add_column()` 为 `ds_rules` 表添加 `role_list` 列（Text 类型，默认 `'[]'`）
   - 使用 `op.add_column()` 为 `ds_rules` 表添加 `dept_list` 列（Text 类型，默认 `'[]'`）
   - 使用 `op.add_column()` 为 `sys_user` 表添加 `role_ids` 列（JSONB 类型，默认 `'[]'`）
   - 使用 `op.add_column()` 为 `sys_user` 表添加 `dept_ids` 列（JSONB 类型，默认 `'[]'`）
4. 定义 `downgrade()` 函数，按相反顺序删除所有表和列

**验证测试**：
- 执行 `alembic upgrade head`，确认无错误
- 连接 PostgreSQL 数据库，验证以下表已创建：`sys_role`、`sys_department`、`sys_user_role`、`sys_user_dept`
- 验证 `ds_rules` 表包含 `role_list` 和 `dept_list` 列
- 验证 `sys_user` 表包含 `role_ids` 和 `dept_ids` 列
- 执行 `alembic downgrade -1`，确认回滚成功
- 再次执行 `alembic upgrade head`，确保可重复执行

---

### 步骤 1.5：扩展系统 Schema DTO

**文件路径**：`backend/apps/system/schemas/system_schema.py`

**指令**：
1. 打开 `system_schema.py` 文件
2. 找到 `UserInfoDTO` 或用户相关的 DTO 类
3. 在类定义中添加字段：
   - `role_ids`: List[int] 或 JSON 类型，默认值 `[]`
   - `dept_ids`: List[int] 或 JSON 类型，默认值 `[]`
4. 创建角色相关 DTO：
   - `RoleCreate`：包含 `name`、`code`、`description`（可选）
   - `RoleUpdate`：包含 `id`、`name`（可选）、`code`（可选）、`description`（可选）
   - `RoleResponse`：包含所有角色字段
5. 创建部门相关 DTO：
   - `DepartmentCreate`：包含 `name`、`code`、`parent_id`
   - `DepartmentUpdate`：包含 `id`、`name`（可选）、`code`（可选）、`parent_id`（可选）
   - `DepartmentResponse`：包含所有部门字段
   - `DepartmentTreeNode`：包含部门字段 + `children?: DepartmentTreeNode[]`

**验证测试**：
- 导入新创建的 DTO 类
- 实例化 `RoleCreate(name='测试角色', code='TEST_ROLE')`，验证序列化后包含正确的字段
- 实例化 `DepartmentTreeNode(id=1, name='技术部', code='TECH', parent_id=0, children=[])`，验证嵌套结构正确

---

### 步骤 1.6：实现冗余字段刷新函数

**文件路径**：`backend/apps/system/crud/user_role_dept.py`（新建）或添加到现有用户 CRUD 文件

**指令**：
1. 创建文件或在现有用户 CRUD 文件中添加函数
2. 实现 `refresh_user_role_ids()` 函数：
   - 接受 `session` 和 `uid`（用户 ID）
   - 使用 `select(SysUserRole.role_id).where(SysUserRole.uid == uid)` 查询
   - 获取所有角色 ID 列表
   - 使用 `session.get(UserModel, uid)` 获取用户对象
   - 设置 `user.role_ids = role_ids_list`
   - 使用 `session.add(user)` 标记为脏数据
   - 注意：不在这里 commit，由调用方负责
3. 实现 `refresh_user_dept_ids()` 函数：
   - 接受 `session` 和 `uid`
   - 查询 `SysUserDept.dept_id` 列表
   - 更新 `user.dept_ids`
   - 标记为脏数据
4. 实现 `refresh_user_ids_batch()` 函数（可选优化）：
   - 接受 `session` 和用户 ID 列表
   - 批量查询所有用户的角色和部门
   - 批量更新 `role_ids` 和 `dept_ids`

**验证测试**：
- 创建一个用户（初始 `role_ids=[]`）
- 在 `sys_user_role` 表中手动插入两条记录
- 调用 `refresh_user_role_ids(session, user_id)`，提交事务
- 查询 `sys_user.role_ids`，验证包含两个角色 ID
- 删除一条 `sys_user_role` 记录
- 再次刷新，验证 `role_ids` 只包含剩余的角色 ID

---

### 步骤 1.7：注册路由到 API 主文件

**文件路径**：`backend/apps/api.py`

**指令**：
1. 打开 `api.py` 文件
2. 在文件顶部预留角色和部门路由器的导入位置（后续步骤创建路由后补充）
3. 使用 `app.include_router()` 预留路由注册位置
4. 确保路由注册在正确的位置（通常在其他系统路由附近）
5. 检查是否有路由冲突或重复前缀

> 注意：实际的 import 语句和注册在后续每个功能模块的路由创建后补充。

**验证测试**：
- 启动后端服务器，确认无导入错误
- 访问 Swagger 文档，确认现有端点正常

---

**第一阶段验收检查点**：
- [x] 所有 4 张新表在数据库中存在（`sys_role`、`sys_department`、`sys_user_role`、`sys_user_dept`）
- [x] `ds_rules` 表包含 `role_list` 和 `dept_list` 列
- [x] `sys_user` 表包含 `role_ids` 和 `dept_ids` 列
- [x] 冗余字段刷新函数可正常调用
- [x] 后端服务器可正常启动

> **Phase 1 Status**: ✅ COMPLETED (2026-05-26)
> - All models created and verified
> - Migration 068 applied successfully
> - All DTOs implemented and tested
> - Refresh functions implemented
> - Ready for Phase 2

---

## 第二阶段：部门管理（前后端完整实现）

> 从本阶段开始，每个功能模块前后端一起完成并测试，确保端到端可用。

### 步骤 2.1：实现部门 CRUD 逻辑

**文件路径**：`backend/apps/system/crud/department.py`

**指令**：
1. 创建新文件 `department.py`
2. 导入数据库 Session、`SysDepartment`、`SysUserDept` 模型
3. 实现 `get_department_tree()` 函数：
   - 查询所有部门
   - 构建树形结构：`parent_id=0` 的为根节点
   - 递归或迭代填充 `children` 字段
   - 返回树形列表
4. 实现 `get_department()` 函数：
   - 接受 `session` 和 `dept_id`
   - 获取并返回部门详情
5. 实现 `create_department()` 函数：
   - 检查 `code` 是否唯一
   - 验证 `parent_id` 对应的父部门是否存在（如果非 0）
   - 生成 ID 和时间戳，插入数据库
6. 实现 `update_department()` 函数：
   - 更新部门信息
   - 如果修改了 `parent_id`，验证不能形成循环引用
   - 提交更改
7. 实现 `delete_department()` 函数：
   - 检查该部门是否有子部门，如果有则拒绝删除并返回错误
   - 检查是否有用户关联，如果有则拒绝或提示先移除用户
   - 删除部门记录
   - 提交更改
8. 实现 `assign_users_to_department()` 函数：
   - 接受 `session`、`dept_id` 和用户 ID 列表（可选包含 `is_primary` 标记）
   - 清除该部门现有的用户关联
   - 插入新的 `SysUserDept` 记录
   - 刷新受影响用户的 `dept_ids`
   - 提交更改
9. 实现 `remove_users_from_department()` 函数：
   - 删除指定的用户部门关联
   - 刷新受影响用户的 `dept_ids`
10. 实现 `get_department_users()` 函数：
    - 查询该部门下的所有用户
    - 返回用户列表及 `is_primary` 标记

**验证测试**：
- 在 Python 解释器中测试各函数
- 创建根部门（`parent_id=0`）
- 创建子部门（`parent_id` 指向根部门）
- 验证部门树构建正确
- 尝试删除有子部门的部门，验证返回错误

---

### 步骤 2.2：创建部门 REST API

**文件路径**：`backend/apps/system/api/department.py`

**指令**：
1. 创建新文件 `department.py`
2. 创建路由器：`router = APIRouter(prefix="/department", tags=["department"])`
3. 实现 `GET /department/tree` 端点：调用 `get_department_tree()`，返回树形结构
4. 实现 `GET /department/{id}` 端点：返回部门详情
5. 实现 `POST /department` 端点：接受 `DepartmentCreate` 请求体，调用 `create_department()`
6. 实现 `PUT /department` 端点：接受更新请求体，调用 `update_department()`
7. 实现 `DELETE /department/{id}` 端点：验证叶子节点限制，调用 `delete_department()`
8. 实现 `GET /department/{id}/users` 端点：返回部门下的用户列表
9. 实现 `POST /department/{id}/users` 端点：接受 `{user_ids: [1, 2, 3]}`，调用 `assign_users_to_department()`
10. 实现 `DELETE /department/{id}/users` 端点：调用 `remove_users_from_department()`
11. 所有端点需要验证 admin 权限

**验证测试**：
- 启动后端服务器
- 使用 curl/Postman 测试 `POST /api/department`，创建根部门 `{"name": "技术部", "code": "TECH", "parent_id": 0}`
- 测试创建子部门 `{"name": "后端组", "code": "BE", "parent_id": <根部门ID>}`
- 测试 `GET /api/department/tree`，验证返回嵌套结构
- 测试分配用户到部门 `POST /api/department/<id>/users`
- 尝试删除有子部门的部门，验证返回 400 错误
- 删除叶子部门，验证成功
- 验证 `sys_user.dept_ids` 冗余字段已刷新

---

### 步骤 2.3：注册部门路由

**文件路径**：`backend/apps/api.py`

**指令**：
1. 打开 `api.py` 文件
2. 添加导入：`from apps.system.api.department import router as dept_router`
3. 注册路由：`app.include_router(dept_router, prefix="/api")`
4. 确保无路由冲突

**验证测试**：
- 重启后端服务器
- 访问 Swagger 文档（`http://localhost:8000/docs`）
- 验证 `/api/department` 相关端点出现在文档中
- 调用任意端点，确认路由正确注册且无 404 错误

---

### 步骤 2.4：创建部门 API 客户端

**文件路径**：`frontend/src/api/department.ts`

**指令**：
1. 创建新文件 `department.ts`
2. 导入 axios 实例或封装的请求方法
3. 定义 TypeScript 接口：
   - `Department`：包含 `id`、`name`、`code`、`parent_id`、`origin`、`create_time`
   - `DepartmentTreeNode`：继承 `Department`，新增 `children?: DepartmentTreeNode[]`
   - `DepartmentCreate`：包含 `name`、`code`、`parent_id`
   - `DepartmentUserAssign`：包含 `user_ids: number[]`
4. 实现 API 函数：
   - `getDepartmentTree()`: GET 请求，返回部门树
   - `getDepartmentDetail(id)`: GET 请求
   - `createDepartment(data)`: POST 请求
   - `updateDepartment(data)`: PUT 请求
   - `deleteDepartment(id)`: DELETE 请求
   - `getDepartmentUsers(id)`: GET 请求
   - `assignDepartmentUsers(id, data)`: POST 请求
   - `removeDepartmentUsers(id, data)`: DELETE 请求

**验证测试**：
- 在 Vue 组件中导入 `getDepartmentTree`
- 调用该函数，验证能成功获取部门列表
- 调用 `createDepartment`，验证创建成功
- 检查 TypeScript 编译无错误

---

### 步骤 2.5：创建部门管理页面

**文件路径**：`frontend/src/views/system/department/index.vue`

**指令**：
1. 创建新文件 `index.vue`
2. 使用 `<template>`、`<script setup lang="ts">`、`<style scoped>` 结构
3. 在 `<template>` 中：
   - 添加顶部工具栏，包含"新建部门"按钮
   - 添加 `el-tree` 组件：
     - 配置 `node-key="id"`
     - 配置 `props` 为 `{children: 'children', label: 'name'}`
     - 启用 `default-expand-all`
     - 每个节点显示操作按钮：编辑、删除、管理用户（通过插槽或 render-content）
   - 添加创建/编辑弹窗（`el-dialog`）：
     - 表单包含：名称、编码、父部门选择器（`el-tree-select`）
     - 父部门选择器展示树形结构
     - 表单验证：名称和编码必填
   - 添加用户分配抽屉（`el-drawer`）：
     - 显示已分配用户列表
     - 提供添加/移除功能
4. 在 `<script setup>` 中：
   - 导入部门 API 函数
   - 定义响应式数据：`treeData`、`loading`、`dialogVisible`、`formData`、`drawerVisible`
   - 实现 `loadDepartmentTree()` 函数
   - 实现 `handleCreate()` 函数：打开弹窗，父部门默认为选中节点或根节点
   - 实现 `handleEdit(data, node)` 函数：填充表单
   - 实现 `handleDelete(data)` 函数：检查子节点 → 确认 → 调用删除 API
   - 实现 `handleSubmit()` 函数：提交创建或更新
   - 实现 `handleManageUsers(data)` 函数：打开用户分配抽屉
   - 实现用户添加/移除逻辑
   - 处理树形数据更新：操作成功后重新加载树

**验证测试**：
- 在浏览器中访问部门管理页面
- 验证树形结构正确显示
- 创建根部门，验证出现在树中
- 选中根部门，创建子部门，验证嵌套显示
- 展开/折叠节点，验证交互正常
- 编辑部门名称，验证更新成功
- 尝试删除有子部门的部门，验证显示错误提示
- 删除叶子部门，验证成功
- 管理用户：添加用户到部门，验证用户出现在抽屉列表中
- 移除用户，验证成功

---

### 步骤 2.6：添加部门管理路由

**文件路径**：`frontend/src/router/` 下的路由配置文件

**指令**：
1. 打开路由配置文件
2. 在系统管理路由下新增：
   - 路径：`/system/department`
   - 组件：懒加载 `() => import('@/views/system/department/index.vue')`
   - 元信息：`{ title: '部门管理', icon: '...' }`
3. 确保路由嵌套在系统管理父路由下
4. 检查路由名称不冲突

**验证测试**：
- 启动前端开发服务器
- 在浏览器中访问 `/system/department`，验证部门管理页面正确加载
- 检查侧边栏菜单是否显示新路由
- 验证路由切换时页面无刷新（SPA 行为）

---

**第二阶段验收检查点 — 部门端到端测试**：
- [x] 后端 `GET /api/department/tree` 返回正确树形结构
- [x] 后端 CRUD 操作（创建、读取、更新、删除）均正常
- [x] 删除有子部门的部门返回 400 错误
- [x] 分配/移除用户到部门后 `sys_user.dept_ids` 正确刷新
- [x] 前端部门管理页面可正常访问和操作
- [x] 前端树形组件正确显示层级
- [x] 前端用户分配抽屉正常工作
- [x] 前端调用后端 API 无报错

> **Phase 2 Status**: ✅ COMPLETED & TESTED (2026-05-26)
> - Department CRUD logic implemented with tree building
> - Department REST API with admin-only protection
> - Router registered in api.py
> - Frontend API client created
> - Department management page with el-tree, create/edit dialog, user management drawer
> - Route added to frontend router
> - i18n translations added (zh-CN, en, zh-TW)
> - Tree building verified with multi-level test
> - E2E browser tested: Create, Edit, Delete, Manage Users all working
> - Fixed ElMessage/ElMessageBox import bug (was using window fallback, now imports from element-plus-secondary)
> - Fixed FilterFiled.vue unused operators variable
> - Zero TypeScript compilation errors
> - Ready for Phase 3

---

## 第三阶段：角色管理（前后端完整实现）

### 步骤 3.1：实现角色 CRUD 逻辑

**文件路径**：`backend/apps/system/crud/role.py`

**指令**：
1. 创建新文件 `role.py`
2. 导入数据库 Session、SQLModel select 语句、`SysRole`、`SysUserRole` 模型
3. 实现 `list_roles()` 函数：接受 `session` 和分页参数，按创建时间倒序，返回角色列表和总数
4. 实现 `get_role()` 函数：接受 `session` 和 `role_id`，不存在则抛出 404
5. 实现 `create_role()` 函数：检查 `name`/`code` 唯一性，生成雪花 ID，设置 `create_time`
6. 实现 `update_role()` 函数：更新非空字段，检查唯一性冲突
7. 实现 `delete_role()` 函数：删除 `sys_user_role` 关联 → 删除角色 → 刷新受影响用户的 `role_ids`
8. 实现 `assign_users_to_role()` 函数：清除现有关联 → 插入新关联 → 刷新 `role_ids`
9. 实现 `remove_users_from_role()` 函数：删除指定关联 → 刷新 `role_ids`
10. 实现 `get_role_users()` 函数：通过 JOIN 查询该角色下的所有用户

**验证测试**：
- 在 Python 解释器中测试各函数
- 创建角色，验证数据库中有记录
- 更新角色名称，验证更新成功
- 删除角色，验证角色和关联记录都被删除
- 分配用户到角色，验证 `sys_user_role` 表有记录，`sys_user.role_ids` 已刷新

---

### 步骤 3.2：创建角色 REST API

**文件路径**：`backend/apps/system/api/role.py`

**指令**：
1. 创建新文件 `role.py`
2. 创建路由器：`router = APIRouter(prefix="/role", tags=["role"])`
3. 实现 `GET /role` 端点：分页列表，admin 权限
4. 实现 `GET /role/{id}` 端点：角色详情，admin 权限
5. 实现 `POST /role` 端点：创建角色，admin 权限
6. 实现 `PUT /role` 端点：更新角色，admin 权限
7. 实现 `DELETE /role/{id}` 端点：删除角色，admin 权限
8. 实现 `GET /role/{id}/users` 端点：角色下的用户列表
9. 实现 `POST /role/{id}/users` 端点：接受 `{user_ids: [1, 2, 3]}`，分配用户
10. 实现 `DELETE /role/{id}/users` 端点：接受 `{user_ids: [1, 2]}`，移除用户

**验证测试**：
- 使用 curl/Postman 测试 `POST /api/role`，创建角色
- 验证返回 200 状态码和角色数据
- 测试 `GET /api/role`，验证返回角色列表
- 测试 `PUT /api/role`，更新角色名称
- 测试 `DELETE /api/role/{id}`，删除角色
- 测试非 admin 用户访问返回 403

---

### 步骤 3.3：注册角色路由

**文件路径**：`backend/apps/api.py`

**指令**：
1. 打开 `api.py` 文件
2. 添加导入：`from apps.system.api.role import router as role_router`
3. 注册路由：`app.include_router(role_router, prefix="/api")`
4. 确保无路由冲突

**验证测试**：
- 重启后端服务器
- 访问 Swagger 文档，验证 `/api/role` 相关端点出现
- 调用任意端点，确认路由正确注册且无 404 错误

---

### 步骤 3.4：创建角色 API 客户端

**文件路径**：`frontend/src/api/role.ts`

**指令**：
1. 创建新文件 `role.ts`
2. 导入 axios 实例或封装的请求方法
3. 定义 TypeScript 接口：
   - `Role`：包含 `id`、`name`、`code`、`description`、`origin`、`create_time`
   - `RoleCreate`：包含 `name`、`code`、`description?`
   - `RoleUpdate`：包含 `id`、`name?`、`code?`、`description?`
   - `RoleUserAssign`：包含 `user_ids: number[]`
4. 实现 API 函数：
   - `getRoleList(params)`: GET 请求
   - `getRoleDetail(id)`: GET 请求
   - `createRole(data)`: POST 请求
   - `updateRole(data)`: PUT 请求
   - `deleteRole(id)`: DELETE 请求
   - `getRoleUsers(id)`: GET 请求
   - `assignRoleUsers(id, data)`: POST 请求
   - `removeRoleUsers(id, data)`: DELETE 请求

**验证测试**：
- 在 Vue 组件中导入 `getRoleList`
- 调用该函数，验证能成功获取角色列表
- 调用 `createRole`，验证创建成功
- 检查 TypeScript 编译无错误

---

### 步骤 3.5：创建角色管理页面

**文件路径**：`frontend/src/views/system/role/index.vue`

**指令**：
1. 创建新文件 `index.vue`
2. 使用 `<template>`、`<script setup lang="ts">`、`<style scoped>` 结构
3. 在 `<template>` 中：
   - 添加顶部工具栏，包含"新建角色"按钮和搜索框
   - 添加 `el-table` 组件，列包括：角色名称、编码、描述、用户数、来源、操作列
   - 添加 `el-pagination` 组件
   - 添加创建/编辑弹窗（`el-dialog`）：表单含名称、编码、描述，验证规则
   - 添加用户分配抽屉（`el-drawer`）：已分配用户列表、添加/移除按钮
4. 在 `<script setup>` 中：
   - 导入角色 API 函数
   - 定义响应式数据：`tableData`、`loading`、`pagination`、`dialogVisible`、`formData`
   - 实现 `loadRoles()`、`handleCreate()`、`handleEdit()`、`handleDelete()`、`handleSubmit()`
   - 实现 `handleManageUsers()`、`handleAddUsers()`、`handleRemoveUser()`
   - 添加表单验证和加载状态管理

**验证测试**：
- 在浏览器中访问角色管理页面
- 点击"新建角色"，填写表单并提交，验证表格中显示新角色
- 点击"编辑"，修改名称，验证更新成功
- 点击"管理用户"，打开抽屉，添加/移除用户
- 点击"删除"，确认后验证角色从表格中消失
- 测试分页和搜索功能

---

### 步骤 3.6：添加角色管理路由

**文件路径**：`frontend/src/router/` 下的路由配置文件

**指令**：
1. 打开路由配置文件
2. 在系统管理路由下新增：
   - 路径：`/system/role`
   - 组件：懒加载 `() => import('@/views/system/role/index.vue')`
   - 元信息：`{ title: '角色管理', icon: '...' }`

**验证测试**：
- 访问 `/system/role`，验证角色管理页面正确加载
- 检查侧边栏菜单显示新路由
- 验证路由切换无刷新

---

**第三阶段验收检查点 — 角色端到端测试**：
- [x] 后端 `GET /api/role` 返回角色列表
- [x] 后端 CRUD 操作均正常
- [x] 分配/移除用户到角色后 `sys_user.role_ids` 正确刷新
- [x] 删除角色后关联记录清除、冗余字段刷新
- [x] 前端角色管理页面可正常访问和操作
- [x] 前端用户分配抽屉正常工作
- [x] 前端调用后端 API 无报错

> **Phase 3 Status**: ✅ COMPLETED & TESTED (2026-05-26)
> - Role CRUD logic with pagination, keyword search, name/code uniqueness checks
> - Role REST API with 9 endpoints under /system/role, admin-only protection
> - Delete role also removes user associations and refreshes role_ids
> - Router registered in api.py
> - Frontend API client (role.ts) with typed interfaces
> - Role management page with el-table, search, pagination, create/edit dialog, user drawer
> - Route added to frontend router (/system/role)
> - i18n translations added (zh-CN, en, zh-TW) — 13 keys each
> - E2E browser tested: Create, Edit, Manage Users, Delete all working
> - Zero TypeScript compilation errors
> - Ready for Phase 4

---

## 第四阶段：用户管理扩展（角色/部门只读展示）

> 设计决策：角色和部门的分配操作统一在角色管理、部门管理页面完成（从角色/部门侧分配用户），用户管理页面仅做只读展示，不在用户表单中提供可写的选择器。这样避免了双向操作带来的数据一致性风险，也简化了用户管理页面的复杂度。

### 步骤 4.1：用户列表表格增加角色/部门列

**文件路径**：`frontend/src/views/system/user/User.vue`

**指令**：
1. 打开 `User.vue` 文件
2. 在用户列表 `el-table` 中新增两列：
   - **角色列**：`prop="role_ids"`，使用 `el-tag`（`type="primary"`）展示每个角色 ID 对应的名称
   - **部门列**：`prop="dept_ids"`，使用 `el-tag`（`type="success"`）展示每个部门 ID 对应的名称
3. 实现 `getRoleName(rid)` 辅助函数：从 `roleOptions` 缓存中查找角色名称，找不到则显示 ID
4. 实现 `getDeptName(did)` 辅助函数：递归搜索 `deptTreeOptions` 树，查找部门名称
5. 在 `onMounted` 中加载角色列表（`roleApi.all()`）和部门树（`departmentApi.tree()`），缓存到 `roleOptions` 和 `deptTreeOptions`
6. 空值时显示 `-`

**验证测试**：
- 用户列表表格正确显示角色和部门标签
- 未分配角色/部门的用户显示 `-`
- 通过角色管理页面分配角色后，用户列表自动刷新显示角色名称

---

### 步骤 4.2：用户编辑表单增加角色/部门只读展示

**文件路径**：`frontend/src/views/system/user/User.vue`

**指令**：
1. 打开 `User.vue` 文件
2. 在编辑用户的 `el-drawer` 表单中，在"用户来源"字段下方新增两个只读展示区域：
   - **角色展示**：使用 `el-tag`（`type="primary"`）展示 `state.form.role_ids` 对应的角色名称，仅编辑时显示（`v-if="state.form.id"`）
   - **部门展示**：使用 `el-tag`（`type="success"`）展示 `state.form.dept_ids` 对应的部门名称，仅编辑时显示（`v-if="state.form.id"`）
3. 无角色/部门时显示 `-`
4. 不提供选择器，用户需通过角色管理或部门管理页面进行分配

**验证测试**：
- 编辑已有用户时，表单中正确显示已分配的角色和部门标签
- 新建用户时不显示角色/部门区域
- 标签名称与角色/部门管理页面一致

---

### 步骤 4.3：用户列表 API 返回角色/部门 ID

**文件路径**：`backend/apps/system/schemas/system_schema.py`、`backend/apps/system/api/user.py`

**指令**：
1. 确保 `UserGrid` DTO 包含 `role_ids: Optional[list[int]]` 和 `dept_ids: Optional[list[int]]` 字段（已在 Phase 1 完成）
2. 用户分页查询 API 返回的数据中包含 `role_ids` 和 `dept_ids`（`UserModel` 已有这些 JSONB 字段，自动序列化）
3. 不需要在 `UserCreator` 或 `UserEditor` 中添加这些字段（分配操作不通过用户 API）
4. 不需要新增 `PUT /user/{id}/roles` 或 `PUT /user/{id}/departments` 端点（分配通过角色/部门管理 API 完成）

**验证测试**：
- 调用 `GET /api/user/pager/1/20` 返回的每条用户记录包含 `role_ids` 和 `dept_ids` 数组
- 创建用户时不需要传入 `role_ids`/`dept_ids`
- 更新用户时不需要传入 `role_ids`/`dept_ids`

---

**第四阶段验收检查点 — 用户管理展示测试**：
- [x] 用户列表表格显示角色/部门标签
- [x] 编辑用户时可查看角色和部门（只读）
- [x] 未分配角色/部门的用户显示 `-`
- [x] 通过角色/部门管理页面分配后，用户列表刷新显示正确
- [x] 数据库中 `sys_user.role_ids` 和 `sys_user.dept_ids` 冗余字段正确刷新（由角色/部门管理 API 维护）

> **Phase 4 Status**: ✅ COMPLETED & TESTED (2026-05-26)
> - User table displays role_ids and dept_ids as el-tag columns with name resolution
> - User edit form shows roles and departments as read-only tags (v-if="state.form.id")
> - getRoleName() and getDeptName() helper functions for ID-to-name resolution
> - Role options and department tree loaded on mount for display
> - No writable selectors in user form — assignment done via Role/Dept management pages
> - No separate PUT /user/{id}/roles or /user/{id}/departments endpoints needed
> - Design decision: unidirectional assignment (Role/Dept → User) avoids data consistency issues
---

## 第五阶段：权限匹配逻辑

### 步骤 5.1：扩展 UserInfoDTO 填充角色和部门 ID

**文件路径**：认证中间件或用户信息构建函数（可能在 `backend/common/core/` 或 `backend/apps/system/` 中）

**指令**：
1. 定位构建 `current_user` 对象的代码
2. 找到从数据库加载用户信息的地方
3. 在构建 `UserInfoDTO` 时：从 `sys_user.role_ids` 和 `sys_user.dept_ids` 读取值并赋值
4. 如果值为 `None`，设置为空数组 `[]`
5. 确保这些字段在 JWT token 刷新或用户信息缓存时也正确填充

**验证测试**：
- 登录一个已分配角色和部门的用户
- 在任意 API 端点中打印 `current_user.role_ids` 和 `current_user.dept_ids`
- 验证返回的值与数据库中存储的一致
- 修改用户的角色分配 → 重新登录 → 验证新的 `role_ids` 已生效
- 测试未分配角色/部门的用户，验证返回空数组而非 `None`

---

### 步骤 5.2：重构权限匹配逻辑

**文件路径**：`backend/apps/datasource/crud/permission.py`

**指令**：
1. 打开 `permission.py` 文件
2. 找到匹配规则的核心函数（可能是 `get_row_permission_filters()` 或类似名称）
3. 定位当前匹配逻辑：检查 `current_user.id` 是否在 `user_list` 中
4. 将匹配逻辑重构为独立函数 `match_rule(rule, current_user, permission_id)`
5. 在新函数中实现以下逻辑（按顺序）：
   - 解析 `rule.permission_list`，检查 `permission_id` 是否在其中，不在则返回 False
   - 解析 `rule.user_list`，检查 `current_user.id` 是否在其中（同时检查整数和字符串形式），匹配则返回 True
   - 解析 `rule.role_list`（使用 `getattr(rule, 'role_list', None)` 兼容旧模型），与 `current_user.role_ids` 求交集，有交集则返回 True
   - 解析 `rule.dept_list`（同样使用 `getattr` 兼容），与 `current_user.dept_ids` 求交集，有交集则返回 True
   - 以上都不匹配，返回 False
6. 在原有的规则遍历循环中，调用新的 `match_rule()` 函数
7. 保留原有 `user_list` 匹配逻辑确保向后兼容

**验证测试**：
- 创建规则 `user_list=[1], role_list=[], dept_list=[]`，用用户 ID 1 测试匹配，ID 2 测试不匹配
- 创建规则 `role_list=[3]`，创建用户 `role_ids=[3]`，验证通过角色匹配
- 创建规则 `dept_list=[5]`，创建用户 `dept_ids=[5]`，验证通过部门匹配
- 创建规则同时设置 `user_list`、`role_list`、`dept_list`，测试满足任一条件即匹配
- 测试旧规则（无 `role_list`/`dept_list`）仍然正常工作

---

### 步骤 5.3：扩展权限规则 API 支持角色和部门

**文件路径**：`backend/apps/datasource/api/permission.py` 或类似文件

**指令**：
1. 打开权限规则的 API 文件
2. 找到保存权限规则的端点
3. 修改请求体 schema，新增可选字段：`roles: List[int]`（默认 `[]`）、`departments: List[int]`（默认 `[]`）
4. 在保存逻辑中：将 `roles` 序列化后存储到 `ds_rules.role_list`，`departments` 存储到 `ds_rules.dept_list`
5. 使用 `json.dumps()` 将数组转换为 JSON 字符串
6. 如果字段不存在于模型中（xpack 编译问题），使用 `setattr()` 或原生 SQL 更新
7. 在返回规则详情时，反序列化 `role_list` 和 `dept_list` 为数组

**验证测试**：
- 调用保存 API，传入 `{"users": [1], "roles": [2, 3], "departments": [4]}`
- 查询 `ds_rules` 表，验证 `role_list="[2, 3]"`，`dept_list="[4]"`
- 获取规则详情，验证返回 `roles` 和 `departments` 是数组格式
- 更新规则只修改 `users`，验证 `roles` 和 `departments` 保持不变
- 测试向后兼容：保存不带 `roles`/`departments` 的请求，验证默认为 `[]`

---

**第五阶段验收检查点 — 权限匹配测试**：
- [ ] `current_user.role_ids` 和 `current_user.dept_ids` 在运行时正确填充
- [ ] 规则通过用户 ID 匹配（向后兼容）
- [ ] 规则通过角色 ID 匹配（新功能）
- [ ] 规则通过部门 ID 匹配（新功能）
- [ ] 用户 OR 角色 OR 部门语义正确
- [ ] 权限规则 API 支持保存 `roles` 和 `departments`
- [ ] 旧规则无 `role_list`/`dept_list` 时不报错

---

## 第六阶段：权限规则分配 UI

### 步骤 6.1：创建角色选择组件

**文件路径**：`frontend/src/views/system/permission/SelectRole.vue`

**指令**：
1. 创建新文件 `SelectRole.vue`，参考现有 `SelectPermission.vue` 的结构
2. 在 `<template>` 中：搜索框、角色列表（`el-table` + 复选框）、分页、底部操作栏（已选数量 + 确定/取消）
3. 在 `<script setup>` 中：
   - 定义 `props`：`visible`、`selectedIds`
   - 定义 `emits`：`update:visible`、`confirm`（返回选中的角色 ID 数组）
   - 导入 `getRoleList` API，实现列表加载和搜索
   - 实现复选框选中/取消逻辑和分页
   - 确定 → `confirm` 事件，取消 → `update:visible` 事件

**验证测试**：
- 引入组件并打开，验证角色列表正确显示
- 搜索角色，验证过滤功能正常
- 勾选多个角色，翻页后已选状态保持
- 点击"确定"，验证 `confirm` 事件返回正确的 ID 数组
- 点击"取消"，验证组件关闭且不返回数据

---

### 步骤 6.2：创建部门树选择组件

**文件路径**：`frontend/src/views/system/permission/SelectDepartment.vue`

**指令**：
1. 创建新文件 `SelectDepartment.vue`
2. 在 `<template>` 中：搜索框、`el-tree`（启用 `show-checkbox`）、底部操作栏
3. 在 `<script setup>` 中：
   - 定义 `props`：`visible`、`selectedIds`
   - 定义 `emits`：`update:visible`、`confirm`
   - 导入 `getDepartmentTree` API，加载树数据
   - 使用 `setCheckedKeys()` 初始化已选，`getCheckedKeys()` 获取选中 ID
   - 实现搜索过滤逻辑

**验证测试**：
- 引入组件并打开，验证部门树正确显示
- 勾选不同层级部门，验证复选框状态正确
- 点击"确定"，验证返回的 ID 数组包含所有勾选节点
- 传入 `selectedIds` 预填已选部门，验证树中对应节点已勾选
- 搜索部门，验证过滤后树结构正确

---

### 步骤 6.3：修改权限配置页面为 Tab 选择

**文件路径**：`frontend/src/views/system/permission/index.vue`

**指令**：
1. 打开 `index.vue` 文件
2. 找到"步骤二：选择受限用户"或类似部分
3. 将该部分改为 `el-tabs`，包含三个 Tab：
   - Tab 1：用户 — 保留现有 `SelectPermission.vue`
   - Tab 2：角色 — 使用 `SelectRole.vue`
   - Tab 3：部门 — 使用 `SelectDepartment.vue`
4. 新增状态：`selectedRoles: number[]`、`selectedDepartments: number[]`
5. 每个选择组件的 `confirm` 事件更新对应状态
6. 保存时将 `selectedUsers`、`selectedRoles`、`selectedDepartments` 都包含在请求体中
7. 编辑已有规则时：从后端数据解析 `users`、`roles`、`departments`，分别填充

**验证测试**：
- 打开权限配置页面，验证显示三个 Tab
- 各 Tab 选择功能正常
- 保存规则，检查请求体包含 `users`、`roles`、`departments` 三个字段
- 编辑已有规则，三个 Tab 都正确显示已选项
- 修改某 Tab 选择后保存，验证更新成功
- 清空某 Tab 选择后保存，验证后端正确更新

---

### 步骤 6.4：扩展权限卡片展示计数

**文件路径**：`frontend/src/views/system/permission/Card.vue`

**指令**：
1. 打开 `Card.vue` 文件
2. 找到展示规则组信息的部分，修改计数显示
3. 逻辑：`users` 数组长度 > 0 显示 `X 用户`，`roles` > 0 显示 `Y 角色`，`departments` > 0 显示 `Z 部门`
4. 用逗号连接，例如：`3 用户, 2 角色, 1 部门`
5. 某数组为空则不显示该项，全部为空显示"未分配"
6. 可用不同颜色标签区分类型

**验证测试**：
- 规则分配 2 用户、1 角色、3 部门 → 验证卡片显示 `2 用户, 1 角色, 3 部门`
- 只分配用户 → 只显示 `X 用户`
- 不分配任何目标 → 显示"未分配"
- 移除所有角色 → 卡片不再显示角色计数

---

### 步骤 6.5：扩展权限 API 客户端

**文件路径**：`frontend/src/api/permissions.ts` 或类似文件

**指令**：
1. 打开权限相关的 API 文件
2. 更新保存权限规则的 TypeScript 类型定义，新增：`roles?: number[]`、`departments?: number[]`
3. 更新获取规则详情的返回类型，新增：`roles: number[]`、`departments: number[]`
4. 确保后端返回的 `role_list` 和 `dept_list` 被正确解析为数组

**验证测试**：
- TypeScript 编译检查：运行 `npm run build` 或 `vue-tsc --noEmit`，验证无类型错误
- 调用保存 API，传入包含 `roles` 和 `departments` 的数据，验证请求成功
- 调用获取详情 API，验证 `roles` 和 `departments` 是数组类型且数值正确

---

**第六阶段验收检查点 — 权限分配 UI 测试**：
- [ ] 角色选择组件正常工作（搜索、分页、多选）
- [ ] 部门树选择组件正常工作（树形、复选框、搜索）
- [ ] 权限配置页面三个 Tab 正常显示和切换
- [ ] 保存规则时三个字段正确提交
- [ ] 编辑规则时三个 Tab 正确回显
- [ ] 卡片正确显示用户/角色/部门计数
- [ ] TypeScript 无编译错误

---

## 第七阶段：外部同步（可选，可后续实现）

> 此阶段为扩展功能，可在核心功能完成后实施。

### 步骤 7.1：创建同步适配器基类

**文件路径**：`backend/apps/system/sync/adapter.py`

**指令**：
1. 创建 `sync` 目录（如果不存在）
2. 创建 `adapter.py`，定义 `SyncAdapter` 抽象类和 Pydantic 数据模型
3. 抽象方法：`get_departments()`、`get_roles()`、`get_users()`、`get_user_roles()`、`get_user_departments()`
4. 数据模型：`SyncDepartment(code, name, parent_code)`、`SyncRole(code, name)`、`SyncUser(code, name, email, role_codes, dept_codes)`、`SyncUserRole(user_code, role_code)`、`SyncUserDept(user_code, dept_code, is_primary)`

**验证测试**：
- 导入 `SyncAdapter`，尝试实例化（应失败）
- 创建子类实现所有方法，实例化成功

---

### 步骤 7.2：实现钉钉同步适配器（示例）

**文件路径**：`backend/apps/system/sync/dingtalk.py`

**指令**：
1. 创建 `DingTalkAdapter` 类，继承 `SyncAdapter`
2. 实现 `__init__()`：接受钉钉 API 凭据，初始化 HTTP 客户端，获取 token
3. 实现各抽象方法：调用钉钉 API → 解析响应 → 映射到标准化模型

> 注意：此步骤需要钉钉开放平台 API 文档。

**验证测试**：
- 使用钉钉测试凭据，验证各方法返回正确数据

---

### 步骤 7.3：创建同步 API 端点

**文件路径**：`backend/apps/system/api/sync.py`

**指令**：
1. 创建路由器：`router = APIRouter(prefix="/sync", tags=["sync"])`
2. 实现各 `POST /sync/{origin}/...` 端点：users、roles、departments、user-roles、user-departments
3. 每个端点执行 upsert 逻辑（按 `code` 匹配）
4. 同步完成后刷新受影响用户的冗余字段

**验证测试**：
- 发送同步请求，验证数据正确创建/更新
- 验证冗余字段已刷新
- 测试重复同步，验证幂等性

---

### 步骤 7.4：扩展前端同步 UI

**文件路径**：`frontend/src/views/system/user/SyncUserDing.vue`

**指令**：
1. 将现有用户同步功能改造为 `el-tabs`：用户同步、部门同步、角色同步
2. 各 Tab 提供同步选项和"开始同步"按钮
3. 同步完成后显示结果摘要

**验证测试**：
- 打开同步对话框，验证三个 Tab
- 各 Tab 同步功能正常
- 同步后部门/角色管理页面显示同步的数据

---

**第七阶段验收检查点 — 外部同步测试**：
- [ ] 同步适配器基类可正常继承和实例化
- [ ] 钉钉适配器各方法返回正确数据
- [ ] 同步 API 端点正确执行 upsert
- [ ] 同步后冗余字段正确刷新
- [ ] 前端同步 UI 三个 Tab 正常工作
- [ ] 重复同步幂等

---

## 第八阶段：国际化与完善

### 步骤 8.1：补全中文翻译

**文件路径**：`frontend/src/i18n/zh-CN.json`

**指令**：
1. 在适当的命名空间下添加以下键值对：
   - `role.management`: "角色管理"、`role.create`: "创建角色"、`role.edit`: "编辑角色"、`role.delete`: "删除角色"
   - `role.name`: "角色名称"、`role.code`: "角色编码"、`role.description`: "描述"、`role.users`: "用户"、`role.manageUsers`: "管理用户"
   - `department.management`: "部门管理"、`department.create`: "创建部门"、`department.edit`: "编辑部门"、`department.delete`: "删除部门"
   - `department.name`: "部门名称"、`department.code`: "部门编码"、`department.parent`: "父部门"、`department.root`: "根部门"、`department.manageUsers`: "管理用户"
   - `permission.targetUsers`: "目标用户"、`permission.targetRoles`: "目标角色"、`permission.targetDepartments`: "目标部门"
   - `sync.department`: "同步部门"、`sync.role`: "同步角色"
   - `common.manual`: "手动"、`common.dingtalk`: "钉钉"、`common.wechat`: "企微"、`common.ldap`: "LDAP"
2. 确保键名与现有风格一致

**验证测试**：
- 访问角色管理页面，验证所有文本显示为中文
- 访问部门管理页面，验证所有文本显示为中文
- 权限配置页面 Tab 标签显示为"用户"、"角色"、"部门"
- 检查无硬编码中文字符串

---

### 步骤 8.2：补全英文翻译

**文件路径**：`frontend/src/i18n/en.json`

**指令**：
1. 添加与 `zh-CN.json` 对应的英文翻译：
   - `role.management`: "Role Management"、`role.create`: "Create Role"、`role.edit`: "Edit Role"、`role.delete`: "Delete Role"
   - `role.name`: "Role Name"、`role.code`: "Role Code"、`role.description`: "Description"、`role.users`: "Users"、`role.manageUsers`: "Manage Users"
   - `department.management`: "Department Management"、`department.create`: "Create Department"、`department.edit`: "Edit Department"、`department.delete`: "Delete Department"
   - `department.name`: "Department Name"、`department.code`: "Department Code"、`department.parent`: "Parent Department"、`department.root`: "Root Department"、`department.manageUsers`: "Manage Users"
   - `permission.targetUsers`: "Target Users"、`permission.targetRoles`: "Target Roles"、`permission.targetDepartments`: "Target Departments"
   - `sync.department`: "Sync Departments"、`sync.role`: "Sync Roles"
   - `common.manual`: "Manual"、`common.dingtalk`: "DingTalk"、`common.wechat`: "WeCom"、`common.ldap`: "LDAP"
2. 确保键名与中文文件完全一致

**验证测试**：
- 切换为英文，验证所有页面文本显示为英文
- 检查无混合语言显示

---

### 步骤 8.3：补全繁体中文翻译

**文件路径**：`frontend/src/i18n/zh-TW.json`

**指令**：
1. 添加繁体中文翻译（键名与其他语言文件一致）：
   - `role.management`: "角色管理"、`role.create`: "建立角色"、`role.edit`: "編輯角色"、`role.delete`: "刪除角色"
   - `department.management`: "部門管理"、`department.create`: "建立部門"、`department.edit`: "編輯部門"、`department.delete`: "刪除部門"
   - 其他键参照简体翻译转为繁体用词

**验证测试**：
- 切换为繁体中文，验证所有文本显示正确
- 检查用词符合繁体中文习惯，无简体字符混入

---

**第八阶段验收检查点 — 国际化测试**：
- [ ] 三种语言文件键名完全一致
- [ ] 中文页面无硬编码文本
- [ ] 英文页面无混合语言
- [ ] 繁体中文页面用词正确

---

## 集成测试与验收

### 测试场景 1：角色权限端到端测试

**指令**：
1. 创建角色"销售经理"，code 为 `SALES_MANAGER`
2. 创建用户 `user1`，分配角色"销售经理"
3. 创建行权限规则"销售数据规则"，过滤条件 `region IN ('华南', '华东')`
4. 将规则分配给角色"销售经理"（不分配给用户或部门）
5. 使用 `user1` 登录，发起数据查询
6. 验证查询 SQL 中自动附加了 `region IN ('华南', '华东')` 条件

---

### 测试场景 2：部门权限端到端测试

**指令**：
1. 创建部门树：根部门"总公司" → 子部门"华南分公司"、"华北分公司"
2. 创建用户 `user2`，分配到"华南分公司"
3. 创建行权限规则，分配给部门"华南分公司"
4. 使用 `user2` 登录，发起查询
5. 验证 SQL 中附加了部门相关过滤条件

---

### 测试场景 3：混合分配测试

**指令**：
1. 创建规则"综合规则"，分配：用户 `user1`、角色 `role1`、部门 `dept1`
2. 创建四个测试用户：
   - `userA`：不在用户列表，无角色，无部门 → 不应匹配
   - `userB`：在用户列表中 → 应匹配
   - `userC`：不在用户列表，但有 `role1` → 应匹配
   - `userD`：不在用户列表，无角色，但有 `dept1` → 应匹配
3. 分别使用四个用户发起查询，验证匹配结果

---

### 测试场景 4：冗余字段一致性测试

**指令**：
1. 创建用户 `user1`，验证 `role_ids=[]`
2. 通过角色管理页面分配 `role1` 和 `role2`
3. 验证 `sys_user.role_ids=[role1.id, role2.id]`，`sys_user_role` 有两条记录
4. 通过角色管理页面移除 `role1`（在角色用户管理中移除该用户）
5. 验证 `role_ids` 只包含 `role2.id`
6. 删除 `role2`，验证 `role_ids=[]`，`sys_user_role` 无记录

---

### 测试场景 5：向后兼容性测试

**指令**：
1. 查找系统中已有的权限规则（新功能前创建的）
2. 验证 `role_list` 和 `dept_list` 为 `[]` 或 `null`
3. 使用原有分配了用户的规则发起查询
4. 验证规则仍然正常匹配（通过 `user_list`）
5. 编辑旧规则不修改任何内容直接保存，验证保存成功

---

### 测试场景 6：部门树形结构测试

**指令**：
1. 创建多层级部门树：
   ```
   总公司 (id=1, parent_id=0)
   ├── 技术部 (id=2, parent_id=1)
   │   ├── 后端组 (id=3, parent_id=2)
   │   └── 前端组 (id=4, parent_id=2)
   └── 市场部 (id=5, parent_id=1)
   ```
2. 调用部门树 API，验证返回正确嵌套
3. 前端页面验证树形组件正确显示层级
4. 将用户分配到"后端组"
5. 创建规则分配给"技术部"，验证"后端组"用户不匹配（v1 不支持部门继承）

---

### 测试场景 7：删除保护测试

**指令**：
1. 创建部门"测试部" → 子部门"子测试部" → 尝试删除"测试部" → 验证返回错误
2. 给用户分配"测试部" → 尝试删除 → 验证返回错误或警告
3. 创建角色"测试角色" → 给用户分配 → 删除角色 → 验证关联清除、冗余字段刷新

---

### 性能测试

**指令**：
1. 创建 100 个角色、100 个部门
2. 创建 1000 个用户，随机分配 1-5 个角色和 1-3 个部门
3. 创建 50 条权限规则，随机分配给用户、角色、部门
4. 模拟 100 个并发用户发起查询
5. 验证响应时间不超过基线的 150%
6. 检查数据库慢查询日志

---

## 常见问题与排错指南

### 问题 1：迁移执行失败

**症状**：`alembic upgrade head` 报错

**排查步骤**：
1. 检查数据库中是否已存在同名的表
2. 检查 `alembic_version` 表确认当前版本号
3. 检查字段类型是否与数据库兼容
4. 如果是 JSONB 类型，确认 PostgreSQL 版本支持
5. 检查是否有未提交的事务锁定了表

---

### 问题 2：xpack 模型字段访问失败

**症状**：读取 `ds_rules.role_list` 时报错 `AttributeError`

**排查步骤**：
1. 确认 `ds_rules` 表确实包含 `role_list` 列
2. 使用 `getattr(rule, 'role_list', None)` 代替直接访问
3. 如果仍失败，使用原生 SQL 查询该列
4. 检查 xpack 编译的模型是否缓存了旧的 schema

---

### 问题 3：前端选择组件不显示已选项

**症状**：编辑规则时，Tab 中的选择组件为空

**排查步骤**：
1. 检查后端返回数据中 `users`、`roles`、`departments` 是否存在
2. 检查前端是否正确解析并填充到状态数组
3. 检查选择组件的 `selectedIds` prop 是否正确传入
4. 检查选择组件内部是否正确调用 `setCheckedKeys()` 或等价方法

---

### 问题 4：权限规则不生效

**症状**：分配了角色/部门，但用户查询时无权限过滤

**排查步骤**：
1. 检查 `ds_rules` 表中 `role_list`/`dept_list` 是否正确存储
2. 检查 `sys_user` 表中 `role_ids`/`dept_ids` 是否正确
3. 在 `match_rule()` 函数中添加日志，打印匹配过程
4. 验证 `current_user.role_ids` 和 `current_user.dept_ids` 在运行时不为空
5. 验证类型匹配（整数 vs 字符串）

---

### 问题 5：部门树显示异常

**症状**：部门树出现循环引用或层级错误

**排查步骤**：
1. 查询 `sys_department` 表，检查 `parent_id` 是否有环
2. 验证根部门的 `parent_id` 为 0
3. 检查构建树的递归逻辑，确认有终止条件
4. 添加最大深度限制，防止无限递归

---

## 验收标准

在所有步骤完成后，验证以下标准：

1. ✅ 角色 CRUD 功能正常，API 和前端页面均可用
2. ✅ 部门 CRUD 功能正常，支持树形结构
3. ✅ 用户可通过角色/部门管理页面分配多个角色和多个部门，用户管理页面只读展示
4. ✅ 权限规则可以分配给用户、角色、部门的任意组合
5. ✅ 运行时匹配逻辑正确，满足 OR 语义
6. ✅ 冗余字段与关联表保持一致
7. ✅ 前端页面完整，包含角色管理、部门管理、权限配置扩展
8. ✅ 三语言国际化完整
9. ✅ 向后兼容，旧规则仍然生效
10. ✅ 所有测试场景通过
11. ✅ 性能无明显下降
12. ✅ 无控制台错误或后端异常日志

---

## 下一步建议

实施完成后，可考虑以下增强功能：

1. **部门继承**：添加 `include_children` 标志，支持规则分配到父部门时自动应用于子部门
2. **角色层级**：实现角色继承机制
3. **Excel 批量导入**：在用户导入模板中新增 `role_code` 和 `dept_code` 列
4. **审计日志**：为角色/部门分配变更添加审计日志记录
5. **定时同步任务**：实现从钉钉/企微的定时自动同步
6. **权限可视化**：图形化展示用户通过哪些路径获得了哪些权限
7. **批量操作**：支持批量为用户分配角色/部门

---

**文档版本**：2.0  
**创建日期**：2026-05-26  
**最后更新**：2026-05-26  
**变更说明**：按功能模块重组实施顺序，每个功能前后端一起完成并测试后再进入下一模块