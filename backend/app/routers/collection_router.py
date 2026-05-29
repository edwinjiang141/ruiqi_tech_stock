from datetime import datetime, timedelta
from typing import Callable

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.exceptions import AppException
from app.schemas import CollectionResult, CollectionTask, TaskLogCreate, TushareConfigStatus, success_response
from app.services import DataQualityService, MarketDataService, ScoringDataCollectionService, StockPoolService, TaskLogService

router = APIRouter(prefix="/api/collections", tags=["数据采集"])


@router.get("/config")
def get_tushare_config_status() -> dict[str, object]:
    """查看 Tushare 配置状态，不返回 token 明文。"""

    settings = get_settings()
    return success_response(
        data=TushareConfigStatus(
            token_configured=bool(settings.tushare_token),
            api_url=settings.tushare_api_url,
            timeout=settings.tushare_timeout,
        ).model_dump(),
        message="Tushare 配置状态查询成功",
    )


def _date_range(start_date: str, end_date: str, max_days: int) -> list[str]:
    start = datetime.strptime(start_date, "%Y%m%d").date()
    end = datetime.strptime(end_date, "%Y%m%d").date()
    if start > end:
        raise AppException("开始日期不能晚于结束日期", code="INVALID_DATE_RANGE", status_code=422)
    if (end - start).days + 1 > max_days:
        raise AppException(f"单次区间最多支持 {max_days} 天", code="DATE_RANGE_TOO_LARGE", status_code=422)

    return [(start + timedelta(days=offset)).strftime("%Y%m%d") for offset in range((end - start).days + 1)]


def _validate_date_order(start_date: str, end_date: str, message: str) -> None:
    start = datetime.strptime(start_date, "%Y%m%d").date()
    end = datetime.strptime(end_date, "%Y%m%d").date()
    if start > end:
        raise AppException(message, code="INVALID_DATE_RANGE", status_code=422)


def _quarter_periods(start_period: str, end_period: str) -> list[str]:
    start = datetime.strptime(start_period, "%Y%m%d").date()
    end = datetime.strptime(end_period, "%Y%m%d").date()
    if start > end:
        raise AppException("开始报告期不能晚于结束报告期", code="INVALID_PERIOD_RANGE", status_code=422)

    periods: list[str] = []
    for year in range(start.year, end.year + 1):
        for month, day in [(3, 31), (6, 30), (9, 30), (12, 31)]:
            current = datetime(year, month, day).date()
            if start <= current <= end:
                periods.append(current.strftime("%Y%m%d"))

    if not periods:
        raise AppException("区间内没有季度报告期末日", code="NO_FINANCIAL_PERIOD", status_code=422)
    if len(periods) > 12:
        raise AppException("单次最多支持 12 个季度报告期", code="PERIOD_RANGE_TOO_LARGE", status_code=422)
    return periods


@router.get("/tasks")
def list_collection_tasks() -> dict[str, object]:
    """列出当前支持手工触发的采集任务。"""

    tasks = [
        CollectionTask(
            task_name="collect_stock_pool",
            title="股票池采集",
            method="POST",
            endpoint="/api/collections/stock-pool",
            required_params=[],
            description="调用 stock_basic，写入 dwd_stock_basic，并执行股票基础表质量检查。",
            data_scope="股票代码、名称、地域、行业、市场、交易所、上市状态、上市日期、沪深港通标识，以及创业板/科创板/科技行业标记。",
            date_description="股票基础信息为低频基础资料，无需选择日期；建议每周或每月更新一次。",
            idempotency_key="ts_code",
            frequency="每周一次，或股票池口径调整后手工触发。",
        ),
        CollectionTask(
            task_name="collect_trading_day",
            title="单日交易基础数据采集",
            method="POST",
            endpoint="/api/collections/trading-day?trade_date=YYYYMMDD",
            required_params=["trade_date"],
            description="一次采集指定交易日 daily、adj_factor、daily_basic、moneyflow，重复触发保持幂等。",
            data_scope="日线行情、复权因子、每日估值/换手/市值指标、个股资金流。",
            date_description="选择交易日。若选择非交易日，Tushare 可能返回空数据；建议使用收盘后的交易日。",
            idempotency_key="ts_code + trade_date",
            frequency="每个交易日盘后采集，可手工补采。",
        ),
        CollectionTask(
            task_name="collect_trading_range",
            title="区间交易基础数据采集",
            method="POST",
            endpoint="/api/collections/trading-range?start_date=YYYYMMDD&end_date=YYYYMMDD",
            required_params=["start_date", "end_date"],
            description="按日期区间逐日采集交易基础数据，适合历史补采；单次最多 31 天。",
            data_scope="区间内每日的日线行情、复权因子、每日基础指标、个股资金流。",
            date_description="选择开始日期和结束日期，系统逐日触发采集；非交易日返回空数据时不产生重复记录。",
            idempotency_key="ts_code + trade_date",
            frequency="历史补采或数据修复时手工触发。",
        ),
        CollectionTask(
            task_name="collect_daily_market",
            title="单日行情与每日指标采集",
            method="POST",
            endpoint="/api/collections/daily-market?trade_date=YYYYMMDD",
            required_params=["trade_date"],
            description="采集 daily、adj_factor、daily_basic。",
            data_scope="日线行情、复权因子、每日估值/换手/市值指标。",
            date_description="选择交易日，建议盘后执行。",
            idempotency_key="ts_code + trade_date",
            frequency="每个交易日 17:30 后。",
        ),
        CollectionTask(
            task_name="collect_financial",
            title="财务指标和现金流采集",
            method="POST",
            endpoint="/api/collections/financial?period=YYYYMMDD",
            required_params=["period"],
            description="按当前股票池自动逐只采集 fina_indicator 和 cashflow。",
            data_scope="股票池内创业板、科创板和科技行业股票的财务指标和现金流量表，主要用于质量、成长、偿债和现金流质量因子。",
            date_description="选择财报期末日，不是交易日。常用为 0331、0630、0930、1231。",
            idempotency_key="ts_code + end_date",
            frequency="财报披露期增量检查，或按季度手工补采。",
        ),
        CollectionTask(
            task_name="collect_financial_range",
            title="区间财务数据采集",
            method="POST",
            endpoint="/api/collections/financial-range?start_period=YYYYMMDD&end_period=YYYYMMDD",
            required_params=["start_period", "end_period"],
            description="按当前股票池和季度报告期末日自动采集财务指标和现金流，适合历史财报补采。",
            data_scope="股票池内股票在区间内所有季度期末日的财务指标和现金流量表。",
            date_description="开始和结束日期会自动归集到季度期末日：0331、0630、0930、1231。",
            idempotency_key="ts_code + end_date",
            frequency="历史补采或财报披露后手工触发。",
        ),
        CollectionTask(
            task_name="collect_moneyflow",
            title="资金流采集",
            method="POST",
            endpoint="/api/collections/moneyflow?trade_date=YYYYMMDD",
            required_params=["trade_date"],
            description="采集 moneyflow。",
            data_scope="个股小单/中单/大单/特大单买卖金额、主力净流入等资金流字段。",
            date_description="选择交易日，建议 18:00 后执行。",
            idempotency_key="ts_code + trade_date",
            frequency="每个交易日 18:00 后。",
        ),
        CollectionTask(
            task_name="collect_scoring_financial_range",
            title="评分财务前置数据补齐",
            method="POST",
            endpoint="/api/collections/scoring-financial-range?start_period=YYYYMMDD&end_period=YYYYMMDD",
            required_params=["start_period", "end_period"],
            description="按股票池逐只补齐 income 和 balancesheet，不使用 5000 积分 VIP 全市场接口。",
            data_scope="利润表关键字段、资产负债表关键字段，用于 3 年营收 CAGR、季度环比改善、营收排名、净资产和商誉风险。",
            date_description="选择财报报告期区间，建议一次补齐最近 16 个季度，任务较慢但可重复执行。",
            idempotency_key="ts_code + end_date",
            frequency="阶段 5 评分前置补齐，历史数据补齐后按季度增量执行。",
        ),
        CollectionTask(
            task_name="collect_scoring_risk_data",
            title="评分风险前置数据补齐",
            method="POST",
            endpoint="/api/collections/scoring-risk-data?start_date=YYYYMMDD&end_date=YYYYMMDD",
            required_params=["start_date", "end_date"],
            description="补齐股权质押统计、交易日历和涨跌停价格，支持 warning 和重复补采。",
            data_scope="pledge_stat、trade_cal、stk_limit，用于质押风险、有效交易日窗口和后续模拟交易约束。",
            date_description="选择自然日区间；涨跌停单次最多 31 天，交易日历同步同一区间。",
            idempotency_key="ts_code + end_date / exchange + cal_date / ts_code + trade_date",
            frequency="阶段 5 评分前置补齐；交易日历和涨跌停可按月补齐。",
        ),
        CollectionTask(
            task_name="collect_index_weight_range",
            title="指数权重数据补齐",
            method="POST",
            endpoint="/api/collections/index-weight-range?index_codes=399006.SZ,000688.SH&start_date=YYYYMMDD&end_date=YYYYMMDD",
            required_params=["index_codes", "start_date", "end_date"],
            description="按指数代码和月份补齐 index_weight，用于龙头地位评分。",
            data_scope="核心指数成分股和权重，支持多个指数代码逗号分隔。",
            date_description="Tushare 指数权重为月度数据，建议按月或按季度补齐。",
            idempotency_key="index_code + con_code + trade_date",
            frequency="阶段 5 评分前置补齐；指数权重通常按月更新。",
        ),
    ]
    return success_response(data=[task.model_dump() for task in tasks], message="采集任务列表查询成功")


@router.post("/stock-pool")
def collect_stock_pool(db: Session = Depends(get_db)) -> dict[str, object]:
    """手工触发股票池基础数据采集。"""

    started_at = datetime.now()
    result = _run_collection_task(db, "collect_stock_pool", lambda: StockPoolService(db).collect_stock_pool(), started_at)
    quality_report = DataQualityService(db).check_stock_basic()

    if not quality_report.passed:
        TaskLogService(db).create_log(
            TaskLogCreate(
                task_name="check_stock_basic_quality",
                task_type="quality",
                status="warning",
                started_at=started_at,
                finished_at=datetime.now(),
                message="股票基础表质量检查存在异常",
            )
        )

    return success_response(
        data={
            "collection": result.model_dump(),
            "quality": quality_report.model_dump(),
        },
        message="股票池采集任务完成",
    )


@router.get("/quality/stock-basic")
def check_stock_basic_quality(db: Session = Depends(get_db)) -> dict[str, object]:
    """检查股票基础表数据质量。"""

    report = DataQualityService(db).check_stock_basic()
    return success_response(data=report.model_dump(), message="股票基础表质量检查完成")


@router.get("/quality/scoring-data")
def check_scoring_data_quality(db: Session = Depends(get_db)) -> dict[str, object]:
    """检查阶段 5 评分前置数据是否具备计算条件。"""

    report = ScoringDataCollectionService(db).check_scoring_data_quality()
    return success_response(data=report.model_dump(), message="评分前置数据质量检查完成")


@router.post("/trading-day")
def collect_trading_day(
    trade_date: str = Query(..., pattern=r"^\d{8}$"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """手工触发指定交易日全部交易基础数据采集。"""

    started_at = datetime.now()

    def action() -> CollectionResult:
        service = MarketDataService(db)
        market_result = service.collect_daily_market(trade_date)
        moneyflow_result = service.collect_moneyflow(trade_date)
        return CollectionResult(
            task_name="collect_trading_day",
            source=f"{market_result.source},{moneyflow_result.source}",
            fetched_count=market_result.fetched_count + moneyflow_result.fetched_count,
            inserted_or_updated_count=market_result.inserted_or_updated_count + moneyflow_result.inserted_or_updated_count,
            message=f"{trade_date} 交易基础数据采集完成，包含行情、复权、每日指标和资金流",
        )

    result = _run_collection_task(db, "collect_trading_day", action, started_at)
    return success_response(data=result.model_dump(), message="单日交易基础数据采集任务完成")


@router.post("/trading-range")
def collect_trading_range(
    start_date: str = Query(..., pattern=r"^\d{8}$"),
    end_date: str = Query(..., pattern=r"^\d{8}$"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """手工触发日期区间内的交易基础数据采集。"""

    dates = _date_range(start_date, end_date, max_days=31)
    started_at = datetime.now()

    def action() -> CollectionResult:
        fetched_count = 0
        changed_count = 0
        for trade_date in dates:
            service = MarketDataService(db)
            market_result = service.collect_daily_market(trade_date)
            moneyflow_result = service.collect_moneyflow(trade_date)
            fetched_count += market_result.fetched_count + moneyflow_result.fetched_count
            changed_count += market_result.inserted_or_updated_count + moneyflow_result.inserted_or_updated_count

        return CollectionResult(
            task_name="collect_trading_range",
            source="daily,adj_factor,daily_basic,moneyflow",
            fetched_count=fetched_count,
            inserted_or_updated_count=changed_count,
            message=f"{start_date} 至 {end_date} 交易基础数据区间采集完成，共处理 {len(dates)} 个自然日",
        )

    result = _run_collection_task(db, "collect_trading_range", action, started_at)
    return success_response(data=result.model_dump(), message="区间交易基础数据采集任务完成")


@router.post("/daily-market")
def collect_daily_market(
    trade_date: str = Query(..., pattern=r"^\d{8}$"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """手工触发行情、复权和每日指标采集。"""

    result = _run_collection_task(db, "collect_daily_market", lambda: MarketDataService(db).collect_daily_market(trade_date), datetime.now())
    return success_response(data=result.model_dump(), message="行情采集任务完成")


@router.post("/financial")
def collect_financial(
    period: str = Query(..., pattern=r"^\d{8}$"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """手工触发财务指标和现金流采集。"""

    result = _run_collection_task(db, "collect_financial", lambda: MarketDataService(db).collect_financial(period), datetime.now())
    return success_response(data=result.model_dump(), message="财务采集任务完成")


@router.post("/financial-range")
def collect_financial_range(
    start_period: str = Query(..., pattern=r"^\d{8}$"),
    end_period: str = Query(..., pattern=r"^\d{8}$"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """按季度报告期末日触发财务数据区间采集。"""

    periods = _quarter_periods(start_period, end_period)
    started_at = datetime.now()

    def action() -> CollectionResult:
        fetched_count = 0
        changed_count = 0
        warning_count = 0
        for period in periods:
            result = MarketDataService(db).collect_financial(period)
            fetched_count += result.fetched_count
            changed_count += result.inserted_or_updated_count
            if result.status == "warning":
                warning_count += 1

        warning_summary = f"，{warning_count} 个报告期存在部分股票跳过" if warning_count else ""
        return CollectionResult(
            task_name="collect_financial_range",
            source="fina_indicator,cashflow",
            fetched_count=fetched_count,
            inserted_or_updated_count=changed_count,
            status="warning" if warning_count else "success",
            message=f"{start_period} 至 {end_period} 财务数据区间采集完成，共处理 {len(periods)} 个报告期{warning_summary}",
        )

    result = _run_collection_task(db, "collect_financial_range", action, started_at)
    return success_response(data=result.model_dump(), message="区间财务数据采集任务完成")


@router.post("/moneyflow")
def collect_moneyflow(
    trade_date: str = Query(..., pattern=r"^\d{8}$"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """手工触发资金流采集。"""

    result = _run_collection_task(db, "collect_moneyflow", lambda: MarketDataService(db).collect_moneyflow(trade_date), datetime.now())
    return success_response(data=result.model_dump(), message="资金流采集任务完成")


@router.post("/scoring-financial-range")
def collect_scoring_financial_range(
    start_period: str = Query(..., pattern=r"^\d{8}$"),
    end_period: str = Query(..., pattern=r"^\d{8}$"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """按股票池补齐阶段 5 评分所需利润表和资产负债表历史数据。"""

    _validate_date_order(start_period, end_period, "开始报告期不能晚于结束报告期")
    result = _run_collection_task(
        db,
        "collect_scoring_financial_range",
        lambda: ScoringDataCollectionService(db).collect_scoring_financial_range(start_period, end_period),
        datetime.now(),
    )
    return success_response(data=result.model_dump(), message="评分财务前置数据补齐任务完成")


@router.post("/scoring-risk-data")
def collect_scoring_risk_data(
    start_date: str = Query(..., pattern=r"^\d{8}$"),
    end_date: str = Query(..., pattern=r"^\d{8}$"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """补齐股权质押、交易日历和涨跌停等评分风险前置数据。"""

    _date_range(start_date, end_date, max_days=31)
    result = _run_collection_task(
        db,
        "collect_scoring_risk_data",
        lambda: ScoringDataCollectionService(db).collect_scoring_risk_data(start_date, end_date),
        datetime.now(),
    )
    return success_response(data=result.model_dump(), message="评分风险前置数据补齐任务完成")


@router.post("/index-weight-range")
def collect_index_weight_range(
    index_codes: str = Query(..., min_length=1),
    start_date: str = Query(..., pattern=r"^\d{8}$"),
    end_date: str = Query(..., pattern=r"^\d{8}$"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """按指数列表补齐指数成分权重。"""

    _validate_date_order(start_date, end_date, "开始日期不能晚于结束日期")
    codes = [code.strip() for code in index_codes.split(",") if code.strip()]
    if not codes:
        raise AppException("至少需要填写一个指数代码", code="INDEX_CODES_EMPTY", status_code=422)
    result = _run_collection_task(
        db,
        "collect_index_weight_range",
        lambda: ScoringDataCollectionService(db).collect_index_weight_range(codes, start_date, end_date),
        datetime.now(),
    )
    return success_response(data=result.model_dump(), message="指数权重数据补齐任务完成")


def _run_collection_task(
    db: Session,
    task_name: str,
    action: Callable[[], CollectionResult],
    started_at: datetime,
) -> CollectionResult:
    task_service = TaskLogService(db)
    task_log = task_service.start_log(task_name, "collection", started_at, "任务已提交，正在执行。")
    try:
        result = action()
    except AppException as exc:
        db.rollback()
        task_service.finish_log(task_log, "failed", datetime.now(), exc.message)
        raise
    except Exception as exc:
        db.rollback()
        task_service.finish_log(task_log, "failed", datetime.now(), "系统内部异常，请查看后台日志。")
        raise

    task_service.finish_log(task_log, result.status, datetime.now(), result.message)
    return result


def _write_collection_log(db: Session, task_name: str, status: str, started_at: datetime, message: str) -> None:
    TaskLogService(db).create_log(
        TaskLogCreate(
            task_name=task_name,
            task_type="collection",
            status=status,
            started_at=started_at,
            finished_at=datetime.now(),
            message=message,
        )
    )
