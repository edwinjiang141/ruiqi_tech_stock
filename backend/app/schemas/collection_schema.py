from pydantic import BaseModel, Field


class CollectionResult(BaseModel):
    """数据采集结果。"""

    task_name: str
    source: str
    fetched_count: int = 0
    inserted_or_updated_count: int = 0
    status: str = "success"
    message: str = ""


class CollectionTask(BaseModel):
    """可手工触发的采集任务说明。"""

    task_name: str
    title: str
    method: str
    endpoint: str
    required_params: list[str] = Field(default_factory=list)
    description: str
    data_scope: str
    date_description: str
    idempotency_key: str
    frequency: str


class TushareConfigStatus(BaseModel):
    """Tushare 配置状态，永不返回 token 明文。"""

    token_configured: bool
    api_url: str
    timeout: int


class QualityMetric(BaseModel):
    """数据质量检查指标。"""

    name: str
    value: int | float | str | bool
    passed: bool
    message: str


class QualityReport(BaseModel):
    """数据质量检查报告。"""

    target: str
    passed: bool
    metrics: list[QualityMetric] = Field(default_factory=list)
