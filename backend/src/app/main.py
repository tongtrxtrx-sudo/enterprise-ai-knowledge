import os

from fastapi import FastAPI

from app.db import Base, get_engine
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.editing import router as editing_router
from app.routers.permissions import router as permissions_router
from app.routers.upload import router as upload_router


DEFAULT_SERVICE_NAME = "kb-backend"
DEFAULT_VERSION = "2.1.0"


def runtime_metadata() -> dict[str, str]:
    return {
        "service_name": os.getenv("BACKEND_SERVICE_NAME", DEFAULT_SERVICE_NAME),
        "version": os.getenv("BACKEND_VERSION", DEFAULT_VERSION),
    }


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=get_engine())
    app = FastAPI(title="kb-backend")
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(editing_router)
    app.include_router(permissions_router)
    app.include_router(upload_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return runtime_metadata()

    return app


app = create_app()
