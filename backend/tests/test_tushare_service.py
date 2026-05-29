import pandas as pd
import pytest

from app.exceptions import AppException
from app.services import TushareService


class FakeProClient:
    def stock_basic(self, **_: object) -> pd.DataFrame:
        return pd.DataFrame([{"ts_code": "300001.SZ", "name": "阶段测试股票"}])


class RateLimitedProClient:
    def __init__(self) -> None:
        self.calls = 0

    def fina_indicator(self, **_: object) -> pd.DataFrame:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("抱歉，您访问接口(fina_indicator)频率超限(200次/分钟)")
        return pd.DataFrame([{"ts_code": "300001.SZ", "end_date": "20260331", "roe": 10.0}])


class DailyQuotaExceededProClient:
    def __init__(self) -> None:
        self.calls = 0

    def cashflow(self, **_: object) -> pd.DataFrame:
        self.calls += 1
        raise RuntimeError("抱歉，您访问接口(cashflow)频率超限(20000次/天)")


def test_tushare_service_validates_dataframe_result() -> None:
    service = TushareService(pro_client=FakeProClient())
    dataframe = service.stock_basic()

    assert len(dataframe) == 1
    assert dataframe.iloc[0]["ts_code"] == "300001.SZ"


def test_tushare_service_backs_off_when_rate_limited(monkeypatch) -> None:
    sleeps: list[float] = []
    pro_client = RateLimitedProClient()
    service = TushareService(pro_client=pro_client, retry_times=2)
    monkeypatch.setattr("app.services.tushare_service.time.sleep", lambda seconds: sleeps.append(seconds))

    dataframe = service.fina_indicator("300001.SZ", "20260331")

    assert len(dataframe) == 1
    assert pro_client.calls == 2
    assert any(seconds >= 60 for seconds in sleeps)


def test_tushare_service_does_not_back_off_for_daily_quota(monkeypatch) -> None:
    sleeps: list[float] = []
    pro_client = DailyQuotaExceededProClient()
    service = TushareService(pro_client=pro_client, retry_times=3)
    monkeypatch.setattr("app.services.tushare_service.time.sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(AppException) as exc_info:
        service.cashflow("300001.SZ", "20260331")

    assert exc_info.value.code == "TUSHARE_DAILY_QUOTA_EXCEEDED"
    assert pro_client.calls == 1
    assert sleeps == []
