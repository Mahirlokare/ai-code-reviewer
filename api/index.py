"""Vercel serverless function entrypoint for FastAPI."""
from app.main import app

# Export app for Vercel WSGI/ASGI handler
__all__ = ["app"]
