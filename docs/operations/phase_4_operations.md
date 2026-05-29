# 阶段 4 数据采集运维步骤

适用范围：Tushare 采集框架、股票池构建、行情/财务/资金流采集、数据质量检查  
运行目录：`/ruiqi_tech_stock`  
业务 schema：`stock_research_v12`

## 1. 前置条件

阶段 4 的真实采集依赖 `TUSHARE_TOKEN`。

配置方式：

```bash
cd /ruiqi_tech_stock
cp backend/.env.example backend/.env
```

编辑 `backend/.env`：

```text
TUSHARE_TOKEN=你的TushareToken
TUSHARE_API_URL=http://api.waditu.com/dataapi
TUSHARE_TIMEOUT=30
```

配置加载规则：

- 后端会读取 `/ruiqi_tech_stock/.env`。
- 后端也会读取 `/ruiqi_tech_stock/backend/.env`。
- 两处同时存在时，`backend/.env` 中的同名配置优先生效。
- 修改 `.env` 后必须重启后端服务，因为当前后端默认使用非 reload 模式运行。

未配置 token 时，采集触发接口会返回：

```text
TUSHARE_TOKEN_MISSING
```

这是预期行为，用于避免误报采集成功。

可通过接口检查配置状态：

```bash
curl http://127.0.0.1:8000/api/collections/config
```

预期结果：

- `token_configured` 表示是否已配置 token。
- `api_url` 显示当前 Tushare API 地址。
- 不返回 token 明文。

如果 `backend/.env` 已配置但页面仍显示未配置，请重启后端：

```bash
cd /ruiqi_tech_stock
scripts/run_backend.sh
```

## 2. 启动服务

后端：

```bash
cd /ruiqi_tech_stock
scripts/run_backend.sh
```

前端：

```bash
cd /ruiqi_tech_stock
scripts/run_frontend.sh
```

访问：

- `http://127.0.0.1:5173/`
- `http://127.0.0.1:8000/`

## 3. 手工触发采集

当前支持的采集任务可通过接口查看：

```bash
curl http://127.0.0.1:8000/api/collections/tasks
```

前端页面也可以手工触发采集：

- 访问 `http://127.0.0.1:5173/`
- 查看“Tushare 配置与采集触发”区域
- 可点击“采集股票池”“采集该日交易基础数据”“采集财务数据”
- 未配置 token 时，页面会展示 `TUSHARE_TOKEN_MISSING`

### 3.1 股票池采集

```bash
curl -X POST http://127.0.0.1:8000/api/collections/stock-pool
```

预期结果：

- 配置 token 后返回 `success=true`。
- 写入或更新 `stock_research_v12.dwd_stock_basic`。
- 写入任务日志 `stock_research_v12.sys_task_log`。

### 3.2 行情、复权和每日指标采集

```bash
curl -X POST "http://127.0.0.1:8000/api/collections/daily-market?trade_date=20260524"
```

预期结果：

- 写入或更新：
  - `stock_research_v12.dwd_stock_daily`
  - `stock_research_v12.dwd_stock_adj_factor`
  - `stock_research_v12.dwd_stock_daily_basic`

### 3.3 单日交易基础数据采集

```bash
curl -X POST "http://127.0.0.1:8000/api/collections/trading-day?trade_date=20260524"
```

预期结果：

- 一次采集指定交易日：
  - 日线行情 `daily`
  - 复权因子 `adj_factor`
  - 每日基础指标 `daily_basic`
  - 个股资金流 `moneyflow`
- 重复触发同一个 `trade_date` 必须幂等，不产生重复数据。

### 3.4 财务指标和现金流采集

```bash
curl -X POST "http://127.0.0.1:8000/api/collections/financial?period=20260331"
```

预期结果：

- 写入或更新：
  - `stock_research_v12.dwd_stock_financial_indicator`
  - `stock_research_v12.dwd_stock_cashflow`

### 3.5 资金流采集

```bash
curl -X POST "http://127.0.0.1:8000/api/collections/moneyflow?trade_date=20260524"
```

预期结果：

- 写入或更新 `stock_research_v12.dwd_stock_moneyflow`。

## 4. 数据质量检查

```bash
curl http://127.0.0.1:8000/api/collections/quality/stock-basic
```

预期结果：

- 返回股票基础表质量报告。
- 指标包含：
  - `total_count`
  - `missing_name_count`
  - `duplicate_ts_code_count`
  - `stock_pool_count`

如果尚未采集股票池，`total_count` 和 `stock_pool_count` 可能为 0，此时质量检查会显示未通过。

## 5. 数据库安全检查

每次采集后执行：

```bash
cd /ruiqi_tech_stock
scripts/check_db_schema.sh
```

预期结果：

- `public` 表数量保持 44。
- 新数据只写入 `stock_research_v12`。

## 6. 幂等性检查

重复采集同一天数据必须满足：

- `dwd_stock_daily` 以 `ts_code + trade_date` 幂等。
- `dwd_stock_adj_factor` 以 `ts_code + trade_date` 幂等。
- `dwd_stock_daily_basic` 以 `ts_code + trade_date` 幂等。
- `dwd_stock_moneyflow` 以 `ts_code + trade_date` 幂等。
- 重复执行不会新增重复行，只会更新同一主键记录。

自动化验证命令：

```bash
cd /ruiqi_tech_stock/backend
PYTHONPATH=/ruiqi_tech_stock/backend python3 -m pytest -q tests/test_market_collection.py tests/test_stock_collection.py
```

预期结果：

- 测试通过。
- 测试样例数据执行后自动清理。

## 7. 大批量写入与错误处理

股票池采集可能返回数千条股票基础数据。为避免 PostgreSQL 单条 SQL 参数上限，系统按 1000 条/批执行 upsert。

验证命令：

```bash
cd /ruiqi_tech_stock/backend
PYTHONPATH=/ruiqi_tech_stock/backend python3 -m pytest -q tests/test_stock_collection.py
```

预期结果：

- 1100 条测试股票可以分批写入。
- 重复写入不产生重复股票。
- 测试结束后自动清理样例数据。

错误处理原则：

- 页面不显示 SQL、数据库连接、驱动参数、堆栈等内部细节。
- 未知异常统一显示“采集任务执行失败，系统已记录失败日志，请在最近任务日志中查看任务状态”。
- 失败任务写入 `stock_research_v12.sys_task_log`，前端最近任务日志展示状态和摘要信息。

## 8. 回归验证

阶段 4 完成后必须执行：

```bash
cd /ruiqi_tech_stock/backend
PYTHONPATH=/ruiqi_tech_stock/backend python3 -m pytest -q
```

```bash
cd /ruiqi_tech_stock/frontend
npm run build
```

```bash
cd /ruiqi_tech_stock
scripts/check_db_schema.sh
```

预期结果：

- 后端测试全部通过。
- 前端构建成功。
- `public` schema 不受影响。

## 9. 故障处理

### 9.1 返回 `TUSHARE_TOKEN_MISSING`

原因：

- 未配置 `TUSHARE_TOKEN`。

处理：

1. 检查 `backend/.env` 是否存在。
2. 检查 `TUSHARE_TOKEN` 是否为空。
3. 重启后端服务。

### 9.2 Tushare 接口连续失败

处理：

1. 检查网络和 Tushare token 权限。
2. 查看接口返回的错误信息。
3. 降低采集频率，避免触发接口限流。
4. 检查任务日志中失败时间和失败接口。

### 9.3 数据质量检查未通过

处理：

1. 查看未通过指标。
2. 若 `total_count=0`，先执行股票池采集。
3. 若名称缺失或股票池数量异常，检查 Tushare 返回字段是否变化。
4. 未定位原因前，不进入因子计算阶段。
