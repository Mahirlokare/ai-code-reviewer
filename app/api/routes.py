"""HTTP routes for diff review, PR management, metrics, remote repo reviews, and webhooks."""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
import httpx

from app.core.config import settings
from app.integrations.github_webhook import verify_github_signature
from app.review.engine import ReviewEngine
from app.schemas.review import (
    DirectCodeRequest,
    RemoteReviewRequest,
    ReviewRequest,
    ReviewResponse,
)
from app.storage.repository import storage_repo
from app.worker import pipeline_worker

router = APIRouter()
engine = ReviewEngine()

GITHUB_PR_URL_RE = re.compile(r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<pr>\d+)")


@router.post("/reviews", response_model=ReviewResponse, tags=["reviews"])
async def review_diff(request: ReviewRequest) -> ReviewResponse:
    """Analyze a submitted diff with the multi-agent engine and return actionable findings."""
    rules = storage_repo.get_repo_patterns(request.repository or "default")
    return engine.review(request, repo_rules=rules)


@router.post("/code/analyze", response_model=ReviewResponse, tags=["code"])
async def analyze_direct_code(request: DirectCodeRequest) -> ReviewResponse:
    """Analyze raw source code in any language with multi-agent security, bug, and style checks."""
    diff_lines = [f"diff --git a/{request.filename} b/{request.filename}", "--- /dev/null", f"+++ b/{request.filename}", "@@ -0,0 +1 @@"]
    for line in request.code.splitlines():
        diff_lines.append("+" + line)

    wrapped_diff = "\n".join(diff_lines)
    review_req = ReviewRequest(
        diff=wrapped_diff,
        language=request.language,
        repository="direct/code-run",
    )
    return engine.review(review_req)


@router.post("/repos/fetch-and-review", tags=["remote-repos"])
async def fetch_and_review_remote_repo(request: RemoteReviewRequest) -> dict[str, Any]:
    """Fetch any public GitHub pull request diff across the internet and run multi-agent review."""
    input_str = request.repo_url_or_slug.strip()
    match = GITHUB_PR_URL_RE.search(input_str)

    if match:
        owner = match.group("owner")
        repo = match.group("repo")
        pr_number = int(match.group("pr"))
    else:
        parts = input_str.split("/")
        if len(parts) == 2 and request.pr_number:
            owner = parts[0]
            repo = parts[1]
            pr_number = request.pr_number
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide a valid GitHub PR URL (e.g. 'https://github.com/owner/repo/pull/1') or slug 'owner/repo' with pr_number.",
            )

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-Code-Reviewer-Agent",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Fetch PR metadata
        meta_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        meta_resp = await client.get(meta_url, headers=headers)
        if meta_resp.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Pull Request #{pr_number} not found in {owner}/{repo}.")
        if meta_resp.status_code != 200:
            raise HTTPException(status_code=meta_resp.status_code, detail="GitHub API error while fetching PR.")
        pr_data = meta_resp.json()

        # Fetch PR unified diff
        diff_resp = await client.get(meta_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"})
        if diff_resp.status_code != 200:
            raise HTTPException(status_code=diff_resp.status_code, detail="Failed to fetch PR diff from GitHub.")
        diff_text = diff_resp.text

    if not diff_text.strip():
        raise HTTPException(status_code=400, detail="The fetched pull request diff is empty.")

    # Execute multi-agent review
    review_req = ReviewRequest(
        diff=diff_text,
        language="unknown",
        repository=f"{owner}/{repo}",
        pull_request_number=pr_number,
    )
    rules = storage_repo.get_repo_patterns(f"{owner}/{repo}")
    review_res = engine.review(review_req, repo_rules=rules)

    # Save to persistent storage repository
    record = storage_repo.save_pr_review(
        repo=f"{owner}/{repo}",
        number=pr_number,
        title=pr_data.get("title", f"Pull Request #{pr_number}"),
        author=pr_data.get("user", {}).get("login", "contributor"),
        head_sha=pr_data.get("head", {}).get("sha", "remote"),
        review_res=review_res,
    )

    return {
        "status": "success",
        "pull_request": f"{owner}/{repo}#{pr_number}",
        "title": pr_data.get("title"),
        "author": pr_data.get("user", {}).get("login"),
        "summary": review_res.summary,
        "score": record.score,
        "findings": [f.model_dump() for f in review_res.findings],
        "analyzed_lines": review_res.analyzed_lines,
        "engine": review_res.engine,
    }


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

    if not verify_github_signature(raw_body, signature, settings.github_webhook_secret):
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
