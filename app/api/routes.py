"""HTTP routes for diff review and GitHub webhook intake."""
from fastapi import APIRouter, HTTPException, Request
from app.core.config import settings
from app.integrations.github_webhook import verify_github_signature
from app.review.engine import ReviewEngine
from app.schemas.review import ReviewRequest, ReviewResponse

router = APIRouter()
engine = ReviewEngine()

@router.post("/reviews", response_model=ReviewResponse, tags=["reviews"])
async def review_diff(request: ReviewRequest) -> ReviewResponse:
    """Analyze a submitted diff and return actionable findings."""
    return engine.review(request)

@router.post("/webhooks/github", tags=["webhooks"])
async def github_webhook(request: Request) -> dict[str, str]:
    """Verify signature and acknowledge webhook event; processing is not queued yet."""
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_github_signature(raw_body, signature, settings.github_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    event = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")
    if event == "ping":
        return {"status": "accepted", "event": event, "delivery_id": delivery_id}
    if event == "pull_request":
        return {"status": "received", "event": event, "delivery_id": delivery_id,
                "note": "Signature verified; automated review pipeline is not connected yet."}
    return {"status": "ignored", "event": event, "delivery_id": delivery_id}
