"""HTTP routes for diff review, PR management, metrics, and GitHub webhook intake."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.core.config import settings
from app.integrations.github_webhook import verify_github_signature
from app.review.engine import ReviewEngine
from app.schemas.review import ReviewRequest, ReviewResponse
from app.storage.repository import storage_repo
from app.worker import pipeline_worker

router = APIRouter()
engine = ReviewEngine()


@router.post("/reviews", response_model=ReviewResponse, tags=["reviews"])
async def review_diff(request: ReviewRequest) -> ReviewResponse:
    """Analyze a submitted diff with the multi-agent engine and return actionable findings."""
    rules = storage_repo.get_repo_patterns(request.repository or "default")
    return engine.review(request, repo_rules=rules)


@router.get("/pull-requests", tags=["pull-requests"])
async def list_pull_requests() -> list[dict[str, Any]]:
    """List pull requests processed by the review pipeline."""
    return storage_repo.list_pull_requests()


@router.get("/metrics", tags=["metrics"])
async def get_metrics() -> dict[str, Any]:
    """Get system and code quality metrics across all processed reviews."""
    return storage_repo.get_metrics()


@router.post("/webhooks/github", tags=["webhooks"])
async def github_webhook(request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Verify HMAC signature and dispatch asynchronous multi-agent review."""
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    # If secret is set, enforce strict HMAC signature verification
    if settings.github_webhook_secret and not verify_github_signature(raw_body, signature, settings.github_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")

    if event == "ping":
        return {"status": "accepted", "event": event, "delivery_id": delivery_id}

    if event == "pull_request":
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

        # Dispatch async review pipeline in background
        background_tasks.add_task(pipeline_worker.process_pull_request_event, payload)

        action = payload.get("action")
        pr_number = payload.get("pull_request", {}).get("number")
        return {
            "status": "queued",
            "event": event,
            "action": action,
            "pull_request": pr_number,
            "delivery_id": delivery_id,
            "message": "Pull request event queued for multi-agent review pipeline.",
        }

    return {"status": "ignored", "event": event, "delivery_id": delivery_id}
