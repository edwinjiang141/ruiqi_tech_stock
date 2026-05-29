# 02 数据库 Schema 设计（V1.2 第1周初稿）

## 1. 分层说明
- `ods`：原始落库层（对齐 Tushare 原始字段）。
- `dwd`：清洗标准层（统一主键、时间、空值策略）。
- `dm`：主题分析层（因子、评分、推荐、复盘指标）。
- `sys`：系统层（任务日志、质检报告、参数版本）。

## 2. 核心表（首批）

### ods 层
- `ods.stock_basic`
- `ods.daily`
- `ods.daily_basic`
- `ods.moneyflow`
- `ods.fina_indicator`

### dwd 层
- `dwd.stock_pool`
- `dwd.market_daily`
- `dwd.financial_quarterly`
- `dwd.moneyflow_daily`

### dm 层
- `dm.factor_snapshot`
- `dm.score_snapshot`
- `dm.recommendation_daily`
- `dm.backtest_nav`

### sys 层
- `sys.job_run_log`
- `sys.data_quality_report`
- `sys.model_version`

## 3. 主键与索引策略（草案）
- 行情类主键：`(ts_code, trade_date)`。
- 财务类主键：`(ts_code, end_date, ann_date)`。
- 推荐类主键：`(trade_date, ts_code, model_version)`。
- 高频查询索引：`trade_date`、`score desc`、`level`。

## 4. 迁移策略
- Alembic 统一管理 schema 和表变更。
- 版本命名规范：`YYYYMMDD_HHMM_<topic>`。
- 所有 DDL 先在 `dev` 验证，再进入 `test/prod`。
