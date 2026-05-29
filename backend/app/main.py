from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.routers.collection_router import router as collection_router
from app.routers.factor_router import router as factor_router
from app.routers.health_router import router as health_router
from app.routers.portfolio_router import router as portfolio_router
from app.routers.recommendation_router import router as recommendation_router
from app.routers.simulation_router import router as simulation_router
from app.routers.stock_router import router as stock_router
from app.routers.task_router import router as task_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name, version=settings.app_version)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(collection_router)
    app.include_router(stock_router)
    app.include_router(recommendation_router)
    app.include_router(factor_router)
    app.include_router(simulation_router)
    app.include_router(portfolio_router)
    app.include_router(task_router)

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()
