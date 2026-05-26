# SQLBot 技术栈

## 项目版本

- 项目名：`sqlbot`
- 版本：`1.8.0`

---

## 后端

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.11 | 运行时（`requires-python == 3.11.*`） |
| FastAPI | >=0.115.12, <1.0.0 | Web 框架，含 `fastapi[standard]` |
| SQLModel | >=0.0.21, <1.0.0 | ORM（SQLAlchemy + Pydantic 融合） |
| Pydantic | >2.0 | 数据校验与序列化 |
| Pydantic Settings | >=2.2.1, <3.0.0 | 环境变量/配置管理 |
| Alembic | >=1.12.1, <2.0.0 | 数据库迁移 |
| PostgreSQL | — | 主数据库 |
| psycopg[binary] | >=3.1.13, <4.0.0 | PostgreSQL 驱动（async） |
| psycopg2-binary | >=2.9.10, <3.0.0 | PostgreSQL 驱动（sync） |
| pgvector | >=0.4.1 | 向量搜索扩展 |
| PyJWT | >=2.8.0, <3.0.0 | JWT 认证 |
| passlib[bcrypt] | >=1.7.4, <2.0.0 | 密码哈希 |
| Redis | >=6.2.0 | 缓存 |
| fastapi-cache2 | >=0.2.2 | API 缓存 |
| Sentry SDK | >=1.40.6, <2.0.0 | 错误监控（含 FastAPI 集成） |

### AI / LLM 相关

| 技术 | 版本 | 说明 |
|------|------|------|
| LangChain | >=0.3, <0.4 | LLM 编排框架 |
| langchain-core | >=0.3, <0.4 | LangChain 核心 |
| langchain-openai | >=0.3, <0.4 | OpenAI 集成 |
| langchain-community | >=0.3, <0.4 | 社区集成 |
| langchain-huggingface | >=0.2.0 | HuggingFace 集成 |
| LangGraph | >=0.3, <0.4 | Agent 工作流图 |
| LlamaIndex | >=0.12.35 | 知识库索引 |
| sentence-transformers | >=2.7 / >=4.0.2 | 文本向量化 |
| DashScope | >=1.14.0, <2.0.0 | 阿里云 AI 服务 |
| NumPy | 2.3.5 | 数值计算 |

### 多数据库连接驱动

| 技术 | 版本 | 说明 |
|------|------|------|
| pymysql | >=1.1.1, <2.0.0 | MySQL |
| pymssql | >=2.3.4, <3.0.0 | SQL Server（非 Darwin） |
| oracledb | >=3.1.1, <4.0.0 | Oracle |
| clickhouse-sqlalchemy | >=0.3.2 | ClickHouse |
| redshift-connector | >=2.1.8 | AWS Redshift |
| pyhive[hive_pure_sasl] | >=0.7.0 | Hive |
| dmpython | 2.5.22 | 达梦（非 Darwin） |
| elasticsearch | >=7.10, <8.0 | Elasticsearch |
| ldap3 | >=2.9.1 | LDAP 目录访问 |

### 工具库

| 技术 | 版本 | 说明 |
|------|------|------|
| httpx | >=0.25.1, <1.0.0 | HTTP 客户端 |
| pandas | >=2.2.3, <3.0.0 | 数据处理 |
| openpyxl | >=3.1.5, <4.0.0 | Excel 读写 |
| xlsxwriter | >=3.2.5 | Excel 写入 |
| xlrd | >=2.0.2 | Excel 旧格式读取 |
| python-calamine | >=0.4.0 | Excel 快速读取 |
| sqlparse | >=0.5.3 | SQL 解析与格式化 |
| sqlglot | >=28.6.0 | SQL 方言转换 |
| pycryptodome | >=3.22.0 | 加密 |
| PyYAML | >=6.0.2 | YAML 配置 |
| dicttoxml | >=1.7.16 | dict → XML |
| tabulate | >=0.9.0 | 表格格式化 |
| fastapi-mcp | >=0.3.4, <0.4.0 | MCP 协议集成 |
| tenacity | >=8.2.3, <9.0.0 | 重试策略 |

### 商业扩展包

| 技术 | 版本 | 说明 |
|------|------|------|
| sqlbot-xpack | >=0.0.5.13, <0.0.6.0 | 编译为 .so 的商业扩展包，部分功能被开源版引用 |

### 开发工具

| 技术 | 版本 | 说明 |
|------|------|------|
| uv | — | Python 依赖管理（pyproject.toml） |
| pytest | >=7.4.3, <8.0.0 | 测试框架 |
| mypy | >=1.8.0, <2.0.0 | 类型检查 |
| ruff | >=0.2.2, <1.0.0 | Lint + 格式化 |
| pre-commit | >=3.6.2, <4.0.0 | Git hooks |
| coverage | >=7.4.3, <8.0.0 | 测试覆盖率 |
| hatchling | — | 构建后端 |

---

## 前端

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | ^3.5.13 | UI 框架 |
| Vite | ^6.3.1 | 构建工具 |
| TypeScript | ~5.7.2 | 类型系统 |
| Element Plus | ^2.10.1 | UI 组件库 |
| Vue Router | ^4.5.0 | 路由 |
| Pinia | ^3.0.2 | 状态管理 |
| vue-i18n | ^9.14.4 | 国际化 |
| axios | ^1.8.4 | HTTP 客户端 |
| Less | 4.4.2 | CSS 预处理器 |

### 可视化与富文本

| 技术 | 版本 | 说明 |
|------|------|------|
| @antv/g2 | ^5.3.3 | 图表库 |
| @antv/s2 | ^2.4.3 | 透视表 |
| @antv/x6 | ^3.1.3 | 图编辑 |
| highlight.js | ^11.11.1 | 代码高亮 |
| TinyMCE | ^7.9.1 | 富文本编辑器 |
| markdown-it | ^14.1.0 | Markdown 渲染 |
| html2canvas | ^1.4.1 | 截图 |

### 工具库

| 技术 | 版本 | 说明 |
|------|------|------|
| lodash / lodash-es | ^4.17.21 | 工具函数 |
| dayjs | ^1.11.13 | 日期处理 |
| json-bigint | ^1.0.0 | BigInt JSON 序列化 |
| snowflake-id | ^1.1.0 | 雪花 ID 生成 |
| @vueuse/core | ^14.1.0 | Vue 组合式工具 |
| crypto-js | ^4.2.0 | 前端加密 |
| web-storage-cache | ^1.1.1 | 本地存储缓存 |
| vue-dompurify-html | ^5.3.0 | HTML 消毒 |

### 开发工具

| 技术 | 版本 | 说明 |
|------|------|------|
| ESLint | ^9.28.0 | Lint |
| Prettier | ^3.5.3 | 格式化 |
| vue-tsc | ^2.2.8 | Vue 类型检查 |
| unplugin-auto-import | ^19.1.2 | 自动导入 |
| unplugin-vue-components-secondary | ^0.24.6 | 组件自动注册 |
| vite-plugin-svg-icons | ^2.0.1 | SVG 图标 |
| vite-svg-loader | ^5.1.0 | SVG 组件加载 |

---

## 部署

| 技术 | 说明 |
|------|------|
| Docker | 多阶段构建：前端 npm build → 后端 uv sync → 运行镜像 |
| docker-compose | 单容器编排，含 PostgreSQL 数据卷 |
| 端口 | 8000（后端 API）、8001（前端/MCP） |
| 基础镜像 | `registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest` |
| 向量模型 | `ghcr.io/1panel-dev/maxkb-vector-model:v1.0.1` |

---

## 项目结构概览

```
SQLBot/
├── backend/           # FastAPI 后端
│   ├── apps/          # 业务模块（system, datasource, chat, dashboard, ...）
│   ├── common/        # 公共工具（core, utils, audit）
│   ├── alembic/       # 数据库迁移
│   ├── locales/       # 后端国际化
│   └── main.py        # 入口
├── frontend/          # Vue 3 前端
│   └── src/
│       ├── api/       # API 客户端
│       ├── views/     # 页面
│       ├── i18n/      # 国际化
│       └── router/    # 路由
├── g2-ssr/            # G2 图表服务端渲染
├── installer/         # 安装脚本
└── docker-compose.yaml
```
