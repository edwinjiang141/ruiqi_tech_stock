from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import StockBasic
from app.schemas import QualityMetric, QualityReport


class DataQualityService:
    """数据质量检查服务，覆盖缺失率、重复主键和股票池标记等基础规则。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def check_stock_basic(self) -> QualityReport:
        total = self.db.scalar(select(func.count()).select_from(StockBasic)) or 0
        missing_name = self.db.scalar(select(func.count()).select_from(StockBasic).where(StockBasic.name.is_(None))) or 0
        in_pool = (
            self.db.scalar(
                select(func.count())
                .select_from(StockBasic)
                .where((StockBasic.is_gem.is_(True)) | (StockBasic.is_star.is_(True)) | (StockBasic.is_tech_industry.is_(True)))
            )
            or 0
        )
        duplicate_codes = (
            self.db.scalar(
                select(func.count()).select_from(
                    select(StockBasic.ts_code)
                    .group_by(StockBasic.ts_code)
                    .having(func.count(StockBasic.ts_code) > 1)
                    .subquery()
                )
            )
            or 0
        )

        metrics = [
            QualityMetric(name="total_count", value=total, passed=total > 0, message="股票基础表记录数必须大于 0"),
            QualityMetric(name="missing_name_count", value=missing_name, passed=missing_name == 0, message="股票名称不应缺失"),
            QualityMetric(name="duplicate_ts_code_count", value=duplicate_codes, passed=duplicate_codes == 0, message="股票代码不应重复"),
            QualityMetric(name="stock_pool_count", value=in_pool, passed=in_pool > 0, message="股票池内股票数量必须大于 0"),
        ]

        return QualityReport(
            target="dwd_stock_basic",
            passed=all(metric.passed for metric in metrics),
            metrics=metrics,
        )
