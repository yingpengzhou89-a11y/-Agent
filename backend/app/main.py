from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import install_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    install_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()

