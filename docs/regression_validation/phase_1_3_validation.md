# 阶段 1-3 回归验证报告

验证日期：2026-05-24  
验证范围：阶段 1 项目骨架与环境适配、阶段 2 数据库 schema 与迁移、阶段 3 前后端基础能力  
结论：通过，可以进入阶段 4。

## 1. 对照依据

主方案：

- `docs/创业板科技股优质股票研究推荐系统_V1.2实施开发计划_纯量化版.md`
- 重点对照第 4 节技术选型、第 5 节项目目录结构、第 6 节基础环境搭建、第 7 节数据库 Schema 设计、第 19 节开发计划、第 20 节中文文档要求。

执行计划：

- `.cursor/plans/v12开发计划_1d30c427.plan.md`
- 重点对照阶段 1、阶段 2、阶段 3，以及当前环境约束：当前目录开发、复用已有 PostgreSQL、只新建 `stock_research_v12`、不使用 Nginx、不创建 Python 虚拟环境。

## 2. 范围核对

| 阶段 | 方案/计划要求 | 当前实现 | 结论 |
|---|---|---|---|
| 阶段 1 | 建立 `backend`、`frontend`、`scripts` 目录，后端按 FastAPI 分层，前端使用 Vue3 + TypeScript + Vite + ECharts，运行脚本放在当前目录内 | 已创建 `backend/`、`frontend/`、`scripts/`；后端包含 `app/models`、`app/schemas`、`app/routers`、`app/services`、`app/jobs` 等；前端包含 Vite/Vue 基础工程；脚本包含后端、前端、调度和数据库检查 | 通过 |
| 阶段 1 | 配置读取数据库 URL、Tushare token、schema、运行模式和日志级别 | `backend/app/config.py` 已提供 `DATABASE_URL`、`DATABASE_SCHEMA`、`TUSHARE_TOKEN`、`APP_ENV`、`LOG_LEVEL` | 通过 |
| 阶段 1 | 不使用 Nginx，改用其他方式替代 | 开发期通过 Vite proxy 代理 `/api`；构建后由 FastAPI 挂载 `frontend/dist` | 通过 |
| 阶段 1 | 不创建 Python 虚拟环境，在当前目录运行 | 运行脚本均以 `/ruiqi_tech_stock` 为根目录，通过 `PYTHONPATH` 指向 `backend` | 通过 |
| 阶段 2 | 不新建数据库，不动已有数据，只新增独立 schema | 使用已有 `ruiqi_stock` 数据库；迁移只创建 `stock_research_v12` | 通过 |
| 阶段 2 | 保留 `ods/dwd/dm/sys` 分层语义 | 单 schema 内使用 `dwd_`、`dm_`、`sys_` 表名前缀；当前阶段尚未需要 `ods_` 表 | 通过 |
| 阶段 2 | 建立核心表：股票、行情、复权、每日指标、财务、现金流、资金流、因子、推荐、模拟、任务日志 | Alembic 初始迁移已创建 13 张核心表 | 通过 |
| 阶段 2 | 迁移脚本不得包含破坏性 SQL | `downgrade()` 不执行删除；测试检查迁移脚本不包含 `DROP TABLE`、`DROP SCHEMA`、`TRUNCATE`、`public` | 通过 |
| 阶段 3 | 实现 FastAPI 应用入口、数据库连接、SQLAlchemy session、统一响应、异常处理和日志 | 已实现 `app/main.py`、`app/database.py`、`app/schemas/common_schema.py`、`app/exceptions.py`、`app/logging_config.py` | 通过 |
| 阶段 3 | 实现健康检查，返回数据库和 schema 状态 | `/api/health` 返回统一响应，包含数据库、用户、schema 和 schema 是否存在 | 通过 |
| 阶段 3 | 实现任务日志写入能力 | `TaskLogService` 与 `/api/tasks` 支持任务日志创建和查询，写入 `stock_research_v12.sys_task_log` | 通过 |
| 阶段 3 | 实现股票、推荐、因子、模拟、任务状态基础 API | 已实现 `/api/stocks`、`/api/recommendations`、`/api/factors`、`/api/simulations`、`/api/tasks` 基础路由 | 通过 |
| 阶段 3 | 增加最小测试 | 当前后端测试覆盖配置、数据库连接、健康检查、迁移安全、基础 API 和任务日志写入 | 通过 |
| 阶段 3 前端扩展 | 提供基础接口联调视图，方便后续阶段回归 | 首页已展示健康状态、模块接口状态和任务日志列表 | 通过 |

## 3. 必跑验证步骤与预期结果

### 3.1 后端测试

命令：

```bash
cd /ruiqi_tech_stock/backend
PYTHONPATH=/ruiqi_tech_stock/backend python3 -m pytest -q
```

预期结果：

- 所有测试通过。
- 至少覆盖配置、数据库连接、健康检查、基础 API、任务日志写入和迁移安全。

本次实际结果：

```text
6 passed in 1.20s
```

### 3.2 前端构建

命令：

```bash
cd /ruiqi_tech_stock/frontend
npm run build
```

预期结果：

- TypeScript 检查通过。
- Vite 构建成功。
- 生成 `frontend/dist/index.html` 和静态资源。

本次实际结果：

```text
vite v6.4.2 building for production...
15 modules transformed.
dist/index.html
dist/assets/index-DzHq4iUP.css
dist/assets/index-VHX7m756.js
built in 1.27s
```

### 3.3 数据库隔离检查

命令：

```bash
cd /ruiqi_tech_stock
scripts/check_db_schema.sh
```

预期结果：

- 能查询到 `stock_research_v12`。
- `public` 表数量保持原有 44 张。
- `stock_research_v12` 当前为 13 张表。

本次实际结果：

```text
schema_name
stock_research_v12

table_schema          table_count
public                44
stock_research_v12    13
```

### 3.4 API 与静态页面冒烟检查

命令：

```bash
cd /ruiqi_tech_stock
PYTHONPATH=/ruiqi_tech_stock/backend python3 - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
for path in [
    "/api/health",
    "/api/stocks",
    "/api/recommendations",
    "/api/factors",
    "/api/simulations",
    "/api/tasks",
    "/",
]:
    response = client.get(path)
    print(f"{path} {response.status_code}")
PY
```

预期结果：

- 所有接口和静态首页返回 `200`。
- `/api/*` 接口返回统一响应结构：`success`、`code`、`message`、`data`。

本次实际结果：

```text
/api/health 200
/api/stocks 200
/api/recommendations 200
/api/factors 200
/api/simulations 200
/api/tasks 200
/ 200
```

### 3.5 Linter 检查

验证方式：

- 使用 IDE linter 诊断检查 `backend/`、`frontend/`、`scripts/`。

预期结果：

- 无新增 linter 错误。

本次实际结果：

```text
No linter errors found.
```

## 4. 阶段专项验证

| 验证项 | 验证方式 | 预期结果 | 实际结果 |
|---|---|---|---|
| 当前目录运行 | 检查 `scripts/run_backend.sh`、`scripts/run_frontend.sh`、`scripts/run_scheduler.sh` | 均从 `/ruiqi_tech_stock` 或其子目录启动，不依赖 `/opt` | 符合 |
| Nginx 替代方案 | 检查 `backend/app/main.py` 和 `frontend/vite.config.ts` | FastAPI 挂载 `frontend/dist`；Vite 开发代理 `/api` | 符合 |
| schema 隔离 | 执行 `scripts/check_db_schema.sh` | `public` 仍为 44 张表，新增对象在 `stock_research_v12` | 符合 |
| Alembic 版本 | 执行 `alembic -c backend/alembic.ini current` | 当前版本为 `202605240001 (head)` | 符合 |
| 任务日志写入 | 运行后端测试 `test_task_log_can_be_created_and_listed` | 能写入并查询 `sys_task_log` | 符合 |
| 统一响应结构 | 运行后端测试和 API 冒烟检查 | API 响应包含 `success/code/message/data` | 符合 |

## 5. 已确认的设计适配项

| 原方案内容 | 当前环境调整 | 是否已纳入验证 |
|---|---|---|
| 原方案建议使用 Nginx | 当前不使用 Nginx，改为 Vite proxy + FastAPI 静态托管 | 是 |
| 原方案建议 Python venv | 当前不创建 venv，直接使用系统 Python 3.11 | 是 |
| 原方案建议新建数据库 | 当前复用已有 `ruiqi_stock` 数据库，只新增独立 schema | 是 |
| 原方案使用 `ods/dwd/dm/sys` 多 schema | 当前使用单 schema `stock_research_v12`，表名前缀保留分层语义 | 是 |
| 原方案列出 `psycopg2-binary` | 当前环境使用 SQLAlchemy 2.x 支持的 `psycopg` 驱动，避免网络下载阻塞 | 是 |

## 6. 数据安全结论

- 未创建新数据库。
- 未删除、覆盖或改造已有 `public` schema。
- `public` 表数量保持 44。
- 迁移脚本未包含 `DROP TABLE`、`DROP SCHEMA`、`TRUNCATE` 或对 `public` 的操作。
- 阶段 3 的任务日志写入发生在 `stock_research_v12.sys_task_log`。

## 7. 后续阶段回归要求

从阶段 4 开始，每个阶段完成后必须新增一个独立验证文档，建议命名为：

```text
docs/regression_validation/phase_4_validation.md
docs/regression_validation/phase_5_validation.md
docs/regression_validation/phase_6_validation.md
docs/regression_validation/phase_7_validation.md
docs/regression_validation/phase_8_validation.md
```

每份验证文档必须包含：

1. 对照主方案与执行计划的范围核对。
2. 可复制执行的验证命令。
3. 明确的预期结果。
4. 本次实际结果。
5. 数据库隔离与数据安全结论。
6. 是否允许进入下一阶段的结论。

## 8. 总结

阶段 1-3 的实现与当前执行计划一致，并已按原 V1.2 方案完成必要适配。当前基础工程、数据库迁移、后端基础能力、前端基础联调面板均满足进入阶段 4 的前置条件。
