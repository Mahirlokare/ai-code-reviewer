"""HTTP routes for review requests."""
from fastapi import APIRouter

from app.review.engine import ReviewEngine
from app.schemas.review import ReviewRequest, ReviewResponse


router = APIRouter()
engine = ReviewEngine()


@router.post("/reviews", response_model=ReviewResponse, tags=["reviews"])
async def review_diff(request: ReviewRequest) -> ReviewResponse:
    """Review a supplied diff and return structured findings."""
    return engine.review(request)
