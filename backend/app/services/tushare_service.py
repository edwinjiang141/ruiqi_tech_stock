import time
from collections.abc import Callable
from typing import Any

import pandas as pd

from app.config import get_settings
from app.exceptions import AppException


RATE_LIMITED_APIS = {"fina_indicator", "cashflow", "income", "balancesheet", "pledge_stat", "index_weight", "stk_limit"}
RATE_LIMIT_MIN_INTERVAL_SECONDS = 0.36
RATE_LIMIT_BACKOFF_SECONDS = 65.0
LAST_CALL_AT: dict[str, float] = {}


class TushareService:
    """Tushare Pro 客户端封装，统一处理 token、重试和返回值校验。"""

    def __init__(self, pro_client: Any | None = None, retry_times: int = 3, retry_interval: float = 1.0) -> None:
        self.settings = get_settings()
        self.retry_times = retry_times
        self.retry_interval = retry_interval
        self._pro_client = pro_client

    @property
    def pro_client(self) -> Any:
        if self._pro_client is not None:
            return self._pro_client

        if not self.settings.tushare_token:
            raise AppException(
                "未配置 TUSHARE_TOKEN，无法调用 Tushare Pro。请先在 backend/.env 或环境变量中配置。",
                code="TUSHARE_TOKEN_MISSING",
                status_code=400,
            )

        import tushare as ts

        ts.set_token(self.settings.tushare_token)
        self._pro_client = ts.pro_api(token=self.settings.tushare_token, timeout=self.settings.tushare_timeout)
        setattr(self._pro_client, "_DataApi__http_url", self.settings.tushare_api_url.rstrip("/"))
        return self._pro_client

    def call(self, api_name: str, **params: Any) -> pd.DataFrame:
        """调用 Tushare API，并返回非 None 的 DataFrame。"""

        caller: Callable[..., pd.DataFrame] = getattr(self.pro_client, api_name)
        last_error: Exception | None = None

        for attempt in range(1, self.retry_times + 1):
            try:
                self._wait_for_rate_limit(api_name)
                result = caller(**params)
                if result is None:
                    raise AppException(f"Tushare 接口 {api_name} 返回 None", code="TUSHARE_EMPTY_RESULT")
                if not isinstance(result, pd.DataFrame):
                    raise AppException(f"Tushare 接口 {api_name} 返回类型异常", code="TUSHARE_INVALID_RESULT")
                return result
            except AppException:
                raise
            except Exception as exc:  # pragma: no cover - 真实网络异常依赖外部环境
                last_error = exc
                if self._is_daily_quota_exceeded(exc):
                    raise AppException(
                        f"Tushare 接口 {api_name} 日调用额度已用尽，请明天额度恢复后继续补采。",
                        code="TUSHARE_DAILY_QUOTA_EXCEEDED",
                        status_code=429,
                    ) from exc
                if attempt < self.retry_times:
                    time.sleep(self._retry_sleep_seconds(exc))

        raise AppException(
            f"Tushare 接口 {api_name} 连续失败：{last_error}",
            code="TUSHARE_CALL_FAILED",
            status_code=502,
        )

    def _wait_for_rate_limit(self, api_name: str) -> None:
        if api_name not in RATE_LIMITED_APIS:
            return
        now = time.monotonic()
        last_call_at = LAST_CALL_AT.get(api_name)
        if last_call_at is not None:
            elapsed = now - last_call_at
            if elapsed < RATE_LIMIT_MIN_INTERVAL_SECONDS:
                time.sleep(RATE_LIMIT_MIN_INTERVAL_SECONDS - elapsed)
        LAST_CALL_AT[api_name] = time.monotonic()

    def _retry_sleep_seconds(self, exc: Exception) -> float:
        message = str(exc)
        if "频率超限" in message or "每分钟" in message or "rate limit" in message.lower():
            return RATE_LIMIT_BACKOFF_SECONDS
        return self.retry_interval

    @staticmethod
    def _is_daily_quota_exceeded(exc: Exception) -> bool:
        message = str(exc).lower()
        return "次/天" in message or "每日" in message or "每天" in message or "daily quota" in message

    def stock_basic(self) -> pd.DataFrame:
        fields = "ts_code,symbol,name,area,industry,market,exchange,list_status,list_date,delist_date,is_hs"
        return self.call("stock_basic", exchange="", list_status="L", fields=fields)

    def daily(self, trade_date: str) -> pd.DataFrame:
        return self.call("daily", trade_date=trade_date)

    def adj_factor(self, trade_date: str) -> pd.DataFrame:
        return self.call("adj_factor", trade_date=trade_date)

    def daily_basic(self, trade_date: str) -> pd.DataFrame:
        return self.call("daily_basic", trade_date=trade_date)

    def fina_indicator(self, ts_code: str, period: str) -> pd.DataFrame:
        return self.call("fina_indicator", ts_code=ts_code, period=period)

    def cashflow(self, ts_code: str, period: str) -> pd.DataFrame:
        return self.call("cashflow", ts_code=ts_code, period=period)

    def income(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        fields = "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,total_revenue,revenue,operate_profit,total_profit,n_income,n_income_attr_p"
        return self.call("income", ts_code=ts_code, start_date=start_date, end_date=end_date, fields=fields)

    def balancesheet(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        fields = "ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,total_assets,total_liab,total_hldr_eqy_exc_min_int,total_hldr_eqy_inc_min_int,goodwill,total_cur_assets,total_cur_liab"
        return self.call("balancesheet", ts_code=ts_code, start_date=start_date, end_date=end_date, fields=fields)

    def pledge_stat(self, ts_code: str) -> pd.DataFrame:
        fields = "ts_code,end_date,pledge_count,unrest_pledge,rest_pledge,total_share,pledge_ratio"
        return self.call("pledge_stat", ts_code=ts_code, fields=fields)

    def index_weight(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self.call("index_weight", index_code=index_code, start_date=start_date, end_date=end_date)

    def trade_cal(self, start_date: str, end_date: str) -> pd.DataFrame:
        return self.call("trade_cal", exchange="", start_date=start_date, end_date=end_date)

    def stk_limit(self, trade_date: str) -> pd.DataFrame:
        return self.call("stk_limit", trade_date=trade_date)

    def moneyflow(self, trade_date: str) -> pd.DataFrame:
        return self.call("moneyflow", trade_date=trade_date)
