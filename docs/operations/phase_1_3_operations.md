# 阶段 1-3 系统运维步骤

适用范围：阶段 1 项目骨架、阶段 2 数据库迁移、阶段 3 前后端基础接口  
运行目录：`/ruiqi_tech_stock`  
数据库：`ruiqi_stock`  
业务 schema：`stock_research_v12`  
注意事项：不得删除、覆盖或改造已有 `public` schema。

## 1. 当前可访问结论

当前阶段前、后端均可以启动，并可以进行阶段性访问。

访问地址：

- 后端 API 健康检查：`http://127.0.0.1:8000/api/health`
- 后端托管的前端页面：`http://127.0.0.1:8000/`
- 前端开发服务：`http://127.0.0.1:5173/`

当前验证结果：

```text
http://127.0.0.1:8000/api/health 200 application/json
http://127.0.0.1:8000/ 200 text/html; charset=utf-8
http://127.0.0.1:5173/ 200 text/html
```

## 2. 启动前检查

### 2.1 检查 Python 依赖

```bash
cd /ruiqi_tech_stock
python3 - <<'PY'
import importlib.util

packages = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "psycopg",
    "alembic",
    "pydantic",
    "pydantic_settings",
    "pandas",
    "numpy",
    "tushare",
    "apscheduler",
    "dotenv",
    "pytest",
    "httpx",
]

for package in packages:
    print(f"{package}: {'OK' if importlib.util.find_spec(package) else 'MISSING'}")
PY
```

预期结果：

- 所有包显示 `OK`。

### 2.2 检查数据库隔离

```bash
cd /ruiqi_tech_stock
scripts/check_db_schema.sh
```

预期结果：

```text
schema_name
stock_research_v12

table_schema          table_count
public                44
stock_research_v12    13
```

说明：

- `public` 表数量必须保持不变。
- 后续阶段如新增业务表，只允许新增到 `stock_research_v12`。

### 2.3 检查 Alembic 版本

```bash
cd /ruiqi_tech_stock
PYTHONPATH=/ruiqi_tech_stock/backend alembic -c backend/alembic.ini current
```

预期结果：

```text
202605240001 (head)
```

## 3. 启动服务

### 3.1 启动后端

```bash
cd /ruiqi_tech_stock
scripts/run_backend.sh
```

预期结果：

- Uvicorn 启动成功。
- 监听地址包含 `http://0.0.0.0:8000`。
- 访问 `http://127.0.0.1:8000/api/health` 返回 `200`。
- 默认使用非 reload 模式，避免开发环境中 reload 子进程被系统回收导致服务不稳定。

### 3.2 启动前端开发服务

```bash
cd /ruiqi_tech_stock
scripts/run_frontend.sh
```

预期结果：

- Vite 启动成功。
- 本机访问地址为 `http://127.0.0.1:5173/` 或终端输出中的 `Local` 地址。
- 前端页面可以展示健康状态、模块状态和任务日志。

### 3.3 启动调度服务

当前阶段调度服务仅提供骨架入口，尚未注册实际采集、评分和复盘任务。

```bash
cd /ruiqi_tech_stock
scripts/run_scheduler.sh
```

预期结果：

- APScheduler 可以启动。
- 日志提示后续阶段将注册采集、评分和复盘任务。

## 4. 阶段性访问验证

### 4.1 使用浏览器访问

访问：

- `http://127.0.0.1:5173/`

预期页面内容：

- 页面标题为“创业板与科技板块优质股票研究推荐系统”。
- 能看到系统健康状态。
- 能看到股票池、推荐结果、因子评分、模拟复盘模块状态。
- 能看到任务状态区域。

访问：

- `http://127.0.0.1:8000/`

预期页面内容：

- FastAPI 返回构建后的前端页面。
- 若刚执行过 `npm run build`，页面应与开发服务展示的基础状态面板一致。

### 4.2 使用命令行验证

```bash
cd /ruiqi_tech_stock
python3 - <<'PY'
from urllib.request import urlopen

for url in [
    "http://127.0.0.1:8000/api/health",
    "http://127.0.0.1:8000/",
    "http://127.0.0.1:5173/",
]:
    with urlopen(url, timeout=5) as response:
        print(url, response.status, response.getheader("content-type"))
PY
```

预期结果：

```text
http://127.0.0.1:8000/api/health 200 application/json
http://127.0.0.1:8000/ 200 text/html; charset=utf-8
http://127.0.0.1:5173/ 200 text/html
```

## 5. API 冒烟检查

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

```text
/api/health 200
/api/stocks 200
/api/recommendations 200
/api/factors 200
/api/simulations 200
/api/tasks 200
/ 200
```

## 6. 回归验证

每次阶段性开发完成后必须执行：

```bash
cd /ruiqi_tech_stock/backend
PYTHONPATH=/ruiqi_tech_stock/backend python3 -m pytest -q
```

预期结果：

- 所有后端测试通过。

```bash
cd /ruiqi_tech_stock/frontend
npm run build
```

预期结果：

- TypeScript 检查通过。
- Vite 构建成功。

```bash
cd /ruiqi_tech_stock
scripts/check_db_schema.sh
```

预期结果：

- `public` 表数量不变。
- 新增对象只出现在 `stock_research_v12`。

对应验证报告必须写入：

- `docs/regression_validation/`

## 7. 停止服务

开发环境下，服务由终端进程运行。

推荐停止方式：

1. 在运行后端或前端的终端中按 `Ctrl+C`。
2. 确认进程不再存在：

```bash
ps -ef | awk '/uvicorn|vite --host|npm run dev/ && !/awk/ {print}'
```

预期结果：

- 无 `uvicorn`、`vite --host`、`npm run dev` 相关进程。

## 8. 常见问题处理

### 8.1 后端健康检查失败

检查项：

1. PostgreSQL 是否可连接。
2. `DATABASE_URL` 是否指向 `ruiqi_stock`。
3. `DATABASE_SCHEMA` 是否为 `stock_research_v12`。
4. Alembic 是否已执行到 `head`。

验证命令：

```bash
cd /ruiqi_tech_stock
PYTHONPATH=/ruiqi_tech_stock/backend python3 - <<'PY'
from app.database import check_database
print(check_database())
PY
```

### 8.2 前端页面无法访问

检查项：

1. `scripts/run_frontend.sh` 是否已启动。
2. `npm install` 是否成功。
3. 当前 Node.js 版本是否满足已固定的 Vite 版本。
4. 如访问 `http://127.0.0.1:8000/`，需先执行 `npm run build` 生成 `frontend/dist`。

### 8.3 数据库表数量异常

处理原则：

1. 先停止开发，禁止继续迁移。
2. 执行 `scripts/check_db_schema.sh` 保存现场结果。
3. 检查最新 Alembic 迁移是否包含 `DROP`、`TRUNCATE`、`public` 等危险操作。
4. 未确认原因前不得进入下一阶段。

## 9. 后续阶段运维补充要求

阶段 4 起，每完成一个阶段必须同步更新运维文档，至少补充：

1. 新增服务或任务的启动方式。
2. 新增 API 的访问方式和预期响应。
3. 新增数据库对象和数据安全检查。
4. 新增定时任务或采集任务的手工触发方式。
5. 新增故障场景和恢复步骤。
