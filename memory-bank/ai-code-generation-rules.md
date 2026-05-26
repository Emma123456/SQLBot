# SQLBot AI 代码生成规则

## 目的
本文件建立一套规则，用于正确引导大语言模型（LLM）为 SQLBot 项目生成代码。这些规则确保代码的一致性、质量和符合项目标准。

## 核心原则

### 1. 项目上下文感知
- **单一事实来源**：始终参考 `design-document.md` 获取功能规范，参考 `tech-stack.md` 获取技术细节
- **理解架构**：认识 FastAPI + SQLModel + PostgreSQL 后端架构与 Vue 3 + Element Plus 前端架构
- **尊重现有代码**：在不理解其目的和依赖关系之前，绝不修改现有代码

### 2. 代码质量标准
- **类型安全**：为所有函数和变量使用正确的类型提示
- **安全优先**：实现适当的身份验证、授权和输入验证
- **性能考虑**：优化数据库查询和 API 响应
- **可维护性**：编写清晰、易读且文档完善的代码

## 后端代码生成规则

### 1. FastAPI 实现
- 遵循 RESTful API 设计原则
- 使用依赖注入进行身份验证和数据库会话管理
- 使用 HTTPException 实现适当的错误处理
- 使用 Pydantic 模型进行请求/响应验证

```python
# API 端点示例模式
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from apps.system.deps import get_current_user, get_db

router = APIRouter()

@router.get("/items")
def get_items(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 实现代码
    pass
```

### 2. SQLModel/ORM 模式
- 对所有数据库操作使用 SQLModel
- 在模型之间定义适当的关系
- 根据上下文适当使用异步/同步
- 为性能实现适当的索引

```python
# 模型示例模式
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional

class SysRole(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str = Field(max_length=128, unique=True)
    code: str = Field(max_length=128, unique=True)
    description: Optional[str] = Field(max_length=512, default=None)
    origin: int = Field(default=0)  # 0=手动, 1=钉钉, 2=企微, 3=LDAP
    create_time: int = Field()
```

### 3. 数据库迁移规则
- 为所有模式更改创建 Alembic 迁移
- 包含 `upgrade()` 和 `downgrade()` 函数
- 部署前测试迁移
- 遵循命名约定：`{序列号}_{描述}.py`

### 4. 业务逻辑组织
- 将 CRUD 操作放在 `crud/` 目录
- 将 API 端点保持在 `api/` 目录
- 对复杂业务逻辑使用服务层
- 在数据库操作前实现适当的验证

## 前端代码生成规则

### 1. Vue 3 组合式 API
- 对所有新组件使用组合式 API（`setup()` 语法）
- 使用 `<script setup lang="ts">` 实现类型安全的组件
- 遵循 Vue 3 响应式模式

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Role } from '@/types/role'

const roles = ref<Role[]>([])

const fetchRoles = async () => {
  // API 调用实现
}

onMounted(() => {
  fetchRoles()
})
</script>
```

### 2. Element Plus 集成
- 一致使用 Element Plus 组件
- 遵循 Element Plus 文档以正确使用
- 使用 Element Plus 规则实现适当的表单验证

### 3. TypeScript 使用
- 为所有数据结构定义适当的接口/类型
- 避免使用 `any` 类型 - 使用特定类型或 `unknown`
- 在适当的地方对可复用组件使用泛型

### 4. API 客户端模式
- 将 API 调用集中在 `api/` 目录
- 使用带有适当拦截器的 axios 处理认证令牌
- 实现适当的错误处理和加载状态

```typescript
// API 客户端示例模式
import request from '@/utils/request'
import type { Role } from '@/types/role'

export const getRoles = async () => {
  return request.get<Role[]>('/api/role')
}

export const createRole = async (data: Partial<Role>) => {
  return request.post<Role>('/api/role', data)
}
```

## 安全规则

### 1. 身份验证与授权
- 在处理请求前始终验证用户身份验证
- 实现基于角色的访问控制（RBAC）
- 对敏感操作验证权限
- 正确使用带过期检查的 JWT 令牌

### 2. 输入验证
- 在前端和后端验证所有用户输入
- 清理数据以防止 XSS 和 SQL 注入
- 对复杂验证规则使用 Pydantic 验证器

### 3. 数据保护
- 绝不在 API 响应中暴露敏感信息
- 实现适当的 CORS 策略
- 对静态和传输中的敏感数据进行加密

## 性能规则

### 1. 数据库优化
- 对频繁查询的字段使用适当的索引
- 对大数据集实现分页
- 使用适当的连接或预加载避免 N+1 查询问题
- 适当使用连接池

### 2. API 性能
- 对频繁访问的数据实现缓存
- 使用适当的 HTTP 缓存头
- 通过选择性字段响应最小化负载大小
- 在适当的地方实现速率限制

### 3. 前端性能
- 懒加载组件和路由
- 优化包大小
- 在 v-for 循环中使用适当的 key 属性
- 对昂贵操作进行防抖/节流

## 测试规则

### 1. 后端测试
- 为业务逻辑编写单元测试
- 为 API 端点实现集成测试
- 使用 pytest fixtures 进行测试数据设置
- 测试成功和失败场景

### 2. 前端测试
- 为工具函数编写单元测试
- 为关键 UI 组件实现组件测试
- 在测试中对 API 调用使用模拟

## 文档规则

### 1. 代码文档
- 为所有公共函数和类添加文档字符串
- 包含参数描述、返回类型和异常
- 用内联注释记录复杂的业务逻辑

### 2. API 文档
- 使用 FastAPI 的自动 OpenAPI 文档
- 为端点和参数提供清晰的描述
- 包含示例请求和响应

## 错误处理规则

### 1. 后端错误处理
- 使用适当的 HTTP 状态码
- 返回一致的错误响应格式
- 适当记录错误以进行调试
- 优雅处理数据库异常

### 2. 前端错误处理
- 显示用户友好的错误消息
- 实现适当的加载状态
- 优雅处理网络故障
- 在适当的地方提供重试机制

## 国际化规则

### 1. 后端 i18n
- 使用翻译键而不是硬编码字符串
- 支持所有需要的语言（zh-CN, en, zh-TW, ko-KR）
- 根据用户偏好加载翻译

### 2. 前端 i18n
- 对所有面向用户的文本使用 vue-i18n
- 逻辑地组织翻译文件
- 提供备用翻译

## 部署规则

### 1. Docker 集成
- 确保所有更改在 Docker 环境中工作
- 添加新服务时更新 docker-compose.yaml
- 部署前测试构建

### 2. 环境配置
- 使用环境变量进行配置
- 绝不硬编码敏感信息
- 为非敏感配置提供默认值

## 代码审查清单

在生成任何代码之前，请确保：
- [ ] 遵循项目架构模式
- [ ] 实现适当的安全措施
- [ ] 包含适当的错误处理
- [ ] 具有正确的类型注解
- [ ] 遵循命名约定
- [ ] 包含必要的文档
- [ ] 考虑性能影响
- [ ] 尊重现有代码结构
- [ ] 适当处理边界情况
- [ ] 实现适当的验证

## AI 特定指南

### 1. 上下文理解
- 在生成新代码前阅读相关现有文件
- 理解代码库的当前状态
- 认识模块间的依赖关系
- 识别与现有功能的潜在冲突

### 2. 增量更改
- 进行小的、专注的更改而不是大规模重写
- 在继续前测试每个更改
- 尽可能保持向后兼容性
- 清晰记录破坏性更改

### 3. 质量保证
- 验证生成的代码编译无错误
- 检查安全漏洞
- 确保适当的错误处理
- 验证类型安全
- 确认性能考虑

## 遵循的通用模式

### 1. CRUD 操作模式
```python
# 标准 CRUD 结构
def create_item(db: Session, item: ItemCreate) -> Item:
    db_item = Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_item(db: Session, item_id: int) -> Optional[Item]:
    return db.get(Item, item_id)

def get_items(db: Session, skip: int = 0, limit: int = 100) -> list[Item]:
    return db.query(Item).offset(skip).limit(limit).all()

def update_item(db: Session, item_id: int, item: ItemUpdate) -> Optional[Item]:
    db_item = db.get(Item, item_id)
    if db_item:
        for key, value in item.dict(exclude_unset=True).items():
            setattr(db_item, key, value)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int) -> bool:
    db_item = db.get(Item, item_id)
    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False
```

### 2. 前端组件模式
```vue
<template>
  <div class="component-wrapper">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ title }}</span>
          <el-button type="primary" @click="handleCreate">
            {{ $t('common.create') }}
          </el-button>
        </div>
      </template>
      
      <el-table :data="dataList" v-loading="loading">
        <!-- 表格列 -->
      </el-table>
      
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        @current-change="handlePageChange"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// 状态
const dataList = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 方法
const fetchData = async () => {
  loading.value = true
  try {
    // API 调用
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>
```

## 经验教训（Phase 1-2 实战总结）

### 1. 前端 Element Plus 组件导入规则（严重 Bug 教训）

**禁止使用** `window` 全局变量回退模式导入 Element Plus 组件：

```typescript
// ❌ 严禁：window 回退模式 — 导致静默运行时故障
const ElMessage = (window as any).ElMessage || (() => {})
const ElMessageBox = (window as any).ElMessageBox || { confirm: () => Promise.reject() }

// ✅ 正确：从 element-plus-secondary 导入
import { ElMessage, ElMessageBox } from 'element-plus-secondary'
```

**原因**：`window.ElMessage` 在 SQLBot 运行时为 `undefined`，回退函数 `(() => {})` 没有 `.success()` 方法，
调用 `ElMessage.success()` 会抛出 TypeError，被 try-catch 静默捕获，导致后续逻辑（对话框关闭、树刷新）被跳过。
用户看到的现象：对话框不关闭、树不刷新、无提示消息 — 但编译无任何错误。

**所有 Element Plus 组件均需从 `element-plus-secondary` 导入**：
- `ElMessage`, `ElMessageBox`, `ElLoading`
- `ElButton`, `ElForm`, `ElTable` 等
- 类型：`FormInstance`, `FormRules`, `CheckboxValueType` 等

### 2. TypeScript TS6133 错误处理规则

- **下划线前缀（`_operators`）不能抑制 TS6133**，必须完全删除未使用的变量或导入
- 生成代码前检查所有导入是否实际使用
- 生成代码后运行 `vue-tsc --noEmit` 验证零错误

### 3. SVG 图标导入

```typescript
// SVG 导入会产生 TS 模块声明警告，但这是项目预存问题
// Vite 构建时会正确处理，不影响编译和运行
import IconName from '@/assets/svg/icon_name.svg'
```

### 4. SQLBot 后端 API 端点标准模式

```python
# api/{feature}.py 标准模式
from fastapi import APIRouter
from apps.system.crud.{feature} import create_xxx, get_xxx, ...
from apps.system.schemas.system_schema import XxxCreate, XxxUpdate
from common.core.deps import CurrentUser, SessionDep

router = APIRouter(tags=["system_{feature}"], prefix="/system/{feature}")

# 读取端点无需管理员保护
@router.get("/list")
async def list_items(session: SessionDep, current_user: CurrentUser):
    return get_all_items(session)

# 写入端点必须检查管理员权限
@router.post("")
async def create_item(session: SessionDep, current_user: CurrentUser, dto: XxxCreate):
    if not current_user.isAdmin:
        raise HTTPException(status_code=403, detail="Admin only")
    return create_xxx(session, dto)
```

**注册路由**：在 `apps/api.py` 中导入并注册
```python
from apps.system.api import {feature}
api_router.include_router({feature}.router)
```

### 5. SQLBot 前端页面标准模式

```
frontend/src/
  api/{feature}.ts          # API 客户端（typed interfaces + request 封装）
  views/system/{feature}/index.vue  # 管理页面
  router/index.ts           # 添加路由
  i18n/{locale}.json        # 三语翻译（zh-CN, en, zh-TW）
```

### 6. 编译通过 ≠ 运行正常（必须 E2E 测试）

| 检查方式 | 能发现的问题 | 不能发现的问题 |
|---------|------------|-------------|
| `vue-tsc` | 类型错误、未使用变量 | 运行时静默故障（如 ElMessage 回退） |
| Python import | 导入错误 | 循环导入（仅服务器启动时暴露） |
| Alembic migrate | 表结构创建 | 约束逻辑错误 |
| **浏览器 E2E 测试** | **以上所有** | — |

**最低测试清单**：
- [ ] `vue-tsc --noEmit` 零错误
- [ ] 后端服务器启动无导入错误
- [ ] 前端 dev 服务器启动无 TS 错误
- [ ] 浏览器 E2E：导航到页面，执行所有 CRUD 操作
- [ ] 验证对话框关闭、列表刷新、成功/错误消息显示

### 7. 数据库模型冗余字段刷新模式

当关联表（如 `sys_user_role`、`sys_user_dept`）变更时，必须刷新父模型上的冗余 JSONB 字段（如 `role_ids`、`dept_ids`）：

```python
# apps/system/crud/user_role_dept.py
# 调用者负责 session.commit()
def refresh_user_role_ids(session: Session, uid: int) -> None:
    stmt = select(SysUserRole.role_id).where(SysUserRole.uid == uid)
    role_ids = list(session.exec(stmt).all())
    user = session.get(UserModel, uid)
    if user:
        user.role_ids = role_ids
        session.add(user)
```

### 8. Alembic 迁移链接规则

- 迁移文件必须正确设置 `down_revision` 链接到上一个迁移
- 使用 `alembic current` 确认当前版本后再创建新迁移
- 迁移后运行 `alembic upgrade head` 并验证

---

## 最终说明

- 这些规则应随着项目发展而更新
- 始终优先考虑安全和性能
- 与现有代码库模式保持一致
- 有疑问时，查阅设计文档和技术栈文件
- 根据经验教训定期审查和完善这些指南
- **新增经验教训必须同步更新本文件**
