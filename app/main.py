from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def create_app() -> FastAPI:
    prefix = settings.api_prefix
    docs = settings.docs_enabled
    app = FastAPI(
        title="MAYASABHA API",
        docs_url=f"{prefix}/docs" if docs else None,
        redoc_url=None,
        openapi_url=f"{prefix}/openapi.json" if docs else None,
    )

    if settings.frontend_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.frontend_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Content-Type"],
        )

    @app.get(f"{prefix}/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
