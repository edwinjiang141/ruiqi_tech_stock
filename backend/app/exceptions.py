import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):
    """业务异常，统一转换为 API 错误响应。"""

    def __init__(self, message: str, code: str = "BUSINESS_ERROR", status_code: int = 400) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code


def error_response(message: str, code: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "code": code,
            "message": message,
            "data": None,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return error_response(exc.message, exc.code, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(_: Request, exc: RequestValidationError) -> JSONResponse:
        logging.warning("请求参数校验失败：%s", exc)
        return error_response("请求参数不符合要求，请检查输入。", "VALIDATION_ERROR", 422)

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(_: Request, exc: Exception) -> JSONResponse:
        logging.exception("系统内部异常：%s", exc)
        return error_response("系统内部异常，请查看任务日志或联系运维人员。", "INTERNAL_ERROR", 500)
