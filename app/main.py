"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router

app = FastAPI(title=settings.app_name, version="0.2.0", description="Automated PR feedback API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-GitHub-Event", "X-GitHub-Delivery", "X-Hub-Signature-256"],
)
app.include_router(router, prefix=settings.api_prefix)

@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Simple liveness endpoint; does not test external services."""
    return {"status": "ok", "service": settings.app_name}
