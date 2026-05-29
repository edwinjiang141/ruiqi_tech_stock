from fastapi.testclient import TestClient

from app.main import app


def test_collection_config_and_tasks_are_visible() -> None:
    client = TestClient(app)

    config_response = client.get("/api/collections/config")
    config_payload = config_response.json()

    assert config_response.status_code == 200
    assert config_payload["success"] is True
    assert config_payload["data"]["api_url"]
    assert "token" not in config_payload["data"]

    tasks_response = client.get("/api/collections/tasks")
    tasks_payload = tasks_response.json()
    task_names = {item["task_name"] for item in tasks_payload["data"]}

    assert tasks_response.status_code == 200
    assert "collect_stock_pool" in task_names
    assert "collect_trading_day" in task_names


def test_collection_trigger_endpoint_is_documented_without_calling_external_api() -> None:
    client = TestClient(app)
    response = client.get("/api/collections/tasks")
    payload = response.json()
    trading_day_task = next(item for item in payload["data"] if item["task_name"] == "collect_trading_day")

    assert response.status_code == 200
    assert trading_day_task["method"] == "POST"
    assert "trade_date" in trading_day_task["required_params"]
