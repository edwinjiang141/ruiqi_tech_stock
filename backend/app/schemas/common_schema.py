from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """统一 API 响应结构。"""

    success: bool = True
    code: str = "OK"
    message: str = "请求成功"
    data: Any = None


def success_response(data: Any = None, message: str = "请求成功") -> dict[str, Any]:
    return ApiResponse(data=data, message=message).model_dump()


class ListResponse(BaseModel):
    """列表接口通用数据结构。"""

    items: list[Any] = Field(default_factory=list)
    total: int = 0
