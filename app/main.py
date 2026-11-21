"""FastAPI application entry point."""
from fastapi import FastAPI

from app.core.config import settings
from app.api.routes import router

app = FastAPI(title=settings.app_name, version="0.1.0", description="Automated PR feedback API")
app.include_router(router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Simple liveness endpoint; does not test external services."""
    return {"status": "ok", "service": settings.app_name}
