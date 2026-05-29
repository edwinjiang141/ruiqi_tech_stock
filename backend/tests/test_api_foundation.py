from fastapi.testclient import TestClient

from app.main import app


def test_foundation_list_endpoints_return_unified_response() -> None:
    client = TestClient(app)

    for path in ["/api/stocks", "/api/recommendations", "/api/factors", "/api/simulations"]:
        response = client.get(path)
        payload = response.json()

        assert response.status_code == 200
        assert payload["success"] is True
        assert isinstance(payload["data"]["items"], list)
        assert isinstance(payload["data"]["total"], int)

    task_response = client.get("/api/tasks")
    task_payload = task_response.json()

    assert task_response.status_code == 200
    assert task_payload["success"] is True
    assert isinstance(task_payload["data"]["items"], list)
    assert isinstance(task_payload["data"]["total"], int)


def test_task_log_can_be_created_and_listed() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/tasks",
        json={
            "task_name": "阶段3接口测试",
            "task_type": "test",
            "status": "success",
            "message": "验证任务日志写入能力",
        },
    )
    create_payload = create_response.json()

    assert create_response.status_code == 200
    assert create_payload["success"] is True
    assert create_payload["data"]["task_name"] == "阶段3接口测试"

    list_response = client.get("/api/tasks")
    list_payload = list_response.json()

    assert list_response.status_code == 200
    assert list_payload["data"]["total"] >= 1
