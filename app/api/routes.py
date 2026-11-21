"""HTTP routes for diff review and service health."""
from fastapi import APIRouter

from app.review.engine import ReviewEngine
from app.schemas.review import ReviewRequest, ReviewResponse

router = APIRouter()
engine = ReviewEngine()


@router.post("/reviews", response_model=ReviewResponse, tags=["reviews"])
async def review_diff(request: ReviewRequest) -> ReviewResponse:
    """Analyze a submitted diff and return actionable findings."""
    return engine.review(request)
