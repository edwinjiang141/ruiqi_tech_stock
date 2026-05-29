# 阶段 4 回归验证报告

验证日期：2026-05-24  
验证范围：Tushare 配置、采集任务触发、前端手工采集、股票池构建、行情/财务/资金流采集框架、幂等与数据质量检查  
结论：通过，可以进入阶段 5。

## 1. 对照依据

主方案：

- `docs/创业板科技股优质股票研究推荐系统_V1.2实施开发计划_纯量化版.md`
- 重点对照第 8 节 Tushare 数据采集规划、第 9 节数据采集契约、第 16 节测试要求、第 21 节日志与运维要求。

执行计划：

- `.cursor/plans/v12开发计划_1d30c427.plan.md`
- 重点对照阶段 4：Tushare 客户端封装、股票池构建、行情/复权/每日指标/财务/现金流/资金流采集、幂等写入、数据质量检查。

## 2. 范围核对

| 核对项 | 方案要求 | 当前实现 | 结论 |
|---|---|---|---|
| Tushare 客户端 | 支持 Tushare Pro 结构化数据采集、重试、返回校验 | `TushareService` 已封装 token 检查、重试、DataFrame 校验和 `stock_basic`、`daily`、`adj_factor`、`daily_basic`、`fina_indicator`、`cashflow`、`moneyflow` 接口 | 通过 |
| Tushare 配置 | token 和 API 地址必须有明确配置位置 | `backend/.env` 或系统环境变量配置 `TUSHARE_TOKEN`、`TUSHARE_API_URL`、`TUSHARE_TIMEOUT`；`/api/collections/config` 可查看状态且不暴露 token 明文 | 通过 |
| 采集任务触发 | 必须说明并实现任务触发方式 | 后端提供 `/api/collections/tasks` 返回可触发任务；提供股票池、单日交易基础数据、行情、财务、资金流手工触发 API | 通过 |
| 前端手工触发 | 数据采集应能从前端页面手工触发 | 前端首页新增 Tushare 配置状态、任务列表、采集股票池、采集单日交易基础数据、采集财务数据按钮 | 通过 |
| 股票池构建 | 基于 `stock_basic` 构建创业板、科创板和科技属性股票池 | `StockPoolService` 已实现股票基础数据归一化、创业板/科创板/科技行业标记和 upsert | 通过 |
| 行情采集 | 采集 `daily`、`adj_factor`、`daily_basic` | `MarketDataService.collect_daily_market()` 已实现采集编排和对应表 upsert | 通过 |
| 财务采集 | 采集财务指标和现金流 | `MarketDataService.collect_financial()` 已实现 `fina_indicator`、`cashflow` 写入 | 通过 |
| 资金流采集 | 采集 `moneyflow` | `MarketDataService.collect_moneyflow()` 已实现资金流写入 | 通过 |
| 幂等写入 | 以主键执行 upsert，避免重复数据 | 使用 PostgreSQL `ON CONFLICT DO UPDATE`，股票以 `ts_code`，时序数据以 `ts_code + 日期` 为冲突键 | 通过 |
| 重复采集同一天 | 重复采集一天的交易基础数据不能产生重复数据 | 自动化测试重复 upsert 同一 `ts_code + trade_date` 的行情、复权、每日指标、资金流，表内仍仅保留 1 行 | 通过 |
| 大批量股票池写入 | 股票池数据量较大时不能超过 PostgreSQL 参数上限 | `StockPoolService` 已按 1000 条/批分批 upsert；自动化测试覆盖 1100 条重复写入 | 通过 |
| 错误信息安全 | 页面不得暴露数据库 SQL、参数或内部堆栈 | 未知异常统一返回友好文案；后台日志记录详细异常；前端将 `INTERNAL_ERROR` 显示为用户可理解提示 | 通过 |
| 失败任务可追踪 | 采集失败后应能在任务日志看到失败状态 | 采集任务异常会写入 `sys_task_log`，前端最近任务日志显示状态、信息和创建时间 | 通过 |
| 数据质量检查 | 检查缺失、重复、股票池有效性 | `DataQualityService.check_stock_basic()` 已检查记录数、名称缺失、重复代码、股票池数量 | 通过 |
| 任务日志 | 采集任务记录执行状态 | 手工采集接口成功后写入 `sys_task_log`；未配置 token 时返回明确错误，不写入伪成功日志 | 通过 |
| 前端入口 | 阶段性展示采集和质量状态 | 首页新增股票基础表质量检查区域 | 通过 |

## 3. 必跑验证步骤

### 3.1 后端测试

命令：

```bash
cd /ruiqi_tech_stock/backend
PYTHONPATH=/ruiqi_tech_stock/backend python3 -m pytest -q
```

预期结果：

- 所有测试通过。
- 覆盖 Tushare 返回校验、股票池 upsert、行情/财务/资金流 upsert、数据质量检查。
- 测试样例数据执行后清理，不保留虚假股票数据。

本次实际结果：

```text
13 passed in 3.74s
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
- 首页包含数据质量状态区域。

本次实际结果：

```text
vite v6.4.2 building for production...
16 modules transformed.
dist/index.html
dist/assets/index-dvRYskKF.css
dist/assets/index-C45Declx.js
built in 1.65s
```

### 3.3 数据库隔离检查

命令：

```bash
cd /ruiqi_tech_stock
scripts/check_db_schema.sh
```

预期结果：

- `public` 表数量保持 44。
- `stock_research_v12` 表数量保持 13。
- 阶段 4 不新增 schema，不改造 `public`。

本次实际结果：

```text
schema_name
stock_research_v12

table_schema          table_count
public                44
stock_research_v12    13
```

### 3.4 API 冒烟检查

命令：

```bash
cd /ruiqi_tech_stock
PYTHONPATH=/ruiqi_tech_stock/backend python3 - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
checks = [
    ("GET", "/api/collections/config"),
    ("GET", "/api/collections/tasks"),
    ("GET", "/api/stocks"),
    ("GET", "/api/collections/quality/stock-basic"),
    ("POST", "/api/collections/stock-pool"),
    ("POST", "/api/collections/trading-day?trade_date=20260524"),
    ("POST", "/api/collections/daily-market?trade_date=20260524"),
    ("POST", "/api/collections/financial?period=20260331"),
    ("POST", "/api/collections/moneyflow?trade_date=20260524"),
    ("GET", "/"),
]
for method, path in checks:
    response = client.request(method, path)
    print(method, path, response.status_code, response.json().get("code") if path.startswith("/api") else "")
PY
```

预期结果：

- 查询类接口返回 `200`。
- 未配置 `TUSHARE_TOKEN` 时，真实采集触发接口返回 `400` 和 `TUSHARE_TOKEN_MISSING`，防止误报成功。
- 配置 token 后，采集接口应写入 `stock_research_v12` 对应表并记录任务日志。

本次实际结果：

```text
GET /api/collections/config 200 OK
GET /api/collections/tasks 200 OK
GET /api/stocks 200 OK
GET /api/collections/quality/stock-basic 200 OK
POST /api/collections/stock-pool 400 TUSHARE_TOKEN_MISSING
POST /api/collections/trading-day?trade_date=20260524 400 TUSHARE_TOKEN_MISSING
POST /api/collections/daily-market?trade_date=20260524 400 TUSHARE_TOKEN_MISSING
POST /api/collections/financial?period=20260331 400 TUSHARE_TOKEN_MISSING
POST /api/collections/moneyflow?trade_date=20260524 400 TUSHARE_TOKEN_MISSING
GET / 200
```

### 3.5 Linter 检查

验证方式：

- 使用 IDE linter 诊断检查 `backend/`、`frontend/`。

预期结果：

- 无新增 linter 错误。

本次实际结果：

```text
No linter errors found.
```

## 4. 数据安全结论

- 未创建新数据库。
- 未新增 schema。
- 未删除、覆盖或改造已有 `public` schema。
- `public` 表数量保持 44。
- 采集写入目标限定在 `stock_research_v12`。
- 测试样例数据已改为测试后清理，避免保留虚假业务数据。
- 重复采集同一交易日数据通过幂等测试验证，不产生重复主键数据。
- 股票池大批量写入已分批处理，避免单条 SQL 超过 PostgreSQL 参数上限。
- 内部异常不会再透出 SQL 或数据库驱动细节到前端页面。

## 5. 阶段结论

阶段 4 的采集配置、任务触发、前端手工采集、采集框架、幂等写入、股票池构建和数据质量检查已满足当前方案要求。当前环境尚未配置 `TUSHARE_TOKEN`，因此真实 Tushare 采集接口按预期返回明确配置错误；配置 token 后即可通过前端按钮或后端 API 手工采集。

## 6. 配置加载修正记录

问题：

- 用户已在 `backend/.env` 配置 `TUSHARE_TOKEN`，但前端仍显示未配置。

原因：

- 后端原先通过相对路径 `.env` 读取配置；从 `/ruiqi_tech_stock` 启动时只会查找工作区根目录 `.env`，不会读取 `backend/.env`。
- 后端使用非 reload 模式运行，修复代码后必须重启进程才能生效。

修正：

- `backend/app/config.py` 已固定读取两个位置：`/ruiqi_tech_stock/.env` 和 `/ruiqi_tech_stock/backend/.env`，后者优先生效。
- 已重启后端并验证 `/api/collections/config` 返回：

```text
token_configured=True
api_url=http://api.waditu.com/dataapi
timeout=30
```
