from app.database import check_database


def test_database_connection_uses_expected_database() -> None:
    status = check_database()

    assert status["database"] == "ruiqi_stock"
    assert status["schema"] == "stock_research_v12"
