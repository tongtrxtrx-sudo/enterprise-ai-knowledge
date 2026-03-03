import os

from fastapi import FastAPI


DEFAULT_SERVICE_NAME = "kb-backend"
DEFAULT_VERSION = "2.1.0"


def runtime_metadata() -> dict[str, str]:
    return {
        "service_name": os.getenv("BACKEND_SERVICE_NAME", DEFAULT_SERVICE_NAME),
        "version": os.getenv("BACKEND_VERSION", DEFAULT_VERSION),
    }


def create_app() -> FastAPI:
    app = FastAPI(title="kb-backend")

    @app.get("/health")
    def health() -> dict[str, str]:
        return runtime_metadata()

    return app


app = create_app()
