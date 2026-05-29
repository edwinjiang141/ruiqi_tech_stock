from pathlib import Path


def test_initial_migration_does_not_touch_public_schema() -> None:
    migration = Path("migrations/versions/202605240001_initial_schema.py").read_text(encoding="utf-8")
    lowered = migration.lower()

    assert "drop table" not in lowered
    assert "drop schema" not in lowered
    assert "truncate" not in lowered
    assert "public" not in lowered
    assert "stock_research_v12" in migration
