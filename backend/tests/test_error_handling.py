from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.exceptions import register_exception_handlers


def test_unexpected_errors_return_friendly_message() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("database password and raw sql should not leak")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")
    payload = response.json()

    assert response.status_code == 500
    assert payload["code"] == "INTERNAL_ERROR"
    assert payload["message"] == "系统内部异常，请查看任务日志或联系运维人员。"
    assert "database password" not in payload["message"]
