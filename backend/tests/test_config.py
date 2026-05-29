from app.config import get_settings


def test_default_schema_is_isolated() -> None:
    settings = get_settings()

    assert settings.database_schema == "stock_research_v12"
    assert "ruiqi_stock" in settings.database_url
