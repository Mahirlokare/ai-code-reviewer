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
from app.schemas.auth import (
    AuthResponse,
    SentEmailRecord,
    SignInRequest,
    SignUpRequest,
    UserProfile,
)
from app.schemas.review import (
    DirectCodeRequest,
    RemoteReviewRequest,
    ReviewRequest,
    ReviewResponse,
)
from app.services.auth_service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.services.email_service import (
    send_signin_notification_email,
    send_signup_confirmation_email,
)
from app.storage.repository import storage_repo
from app.worker import pipeline_worker

router = APIRouter()
engine = ReviewEngine()

GITHUB_PR_RE = re.compile(r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<pr>\d+)", re.I)
GITHUB_COMMIT_RE = re.compile(r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/commit/(?P<sha>[0-9a-fA-F]+)", re.I)
GITHUB_FILE_RE = re.compile(r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<filepath>.+)", re.I)
GITHUB_REPO_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?(?:/.*)?$", re.I)
SLUG_RE = re.compile(r"^(?P<owner>[a-zA-Z0-9_.-]+)/(?P<repo>[a-zA-Z0-9_.-]+)(?:#(?P<pr>\d+))?$")


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
    """Fetch any public GitHub repository, PR, commit, or file across the internet and run multi-agent review."""
    input_str = request.repo_url_or_slug.strip()

    owner: str | None = None
    repo: str | None = None
    pr_number: int | None = request.pr_number
    commit_sha: str | None = None
    file_info: tuple[str, str] | None = None  # (branch, filepath)

    # 1. Match specific target patterns
    pr_match = GITHUB_PR_RE.search(input_str)
    commit_match = GITHUB_COMMIT_RE.search(input_str)
    file_match = GITHUB_FILE_RE.search(input_str)

    if pr_match:
        owner = pr_match.group("owner")
        repo = pr_match.group("repo")
        pr_number = int(pr_match.group("pr"))
    elif commit_match:
        owner = commit_match.group("owner")
        repo = commit_match.group("repo")
        commit_sha = commit_match.group("sha")
    elif file_match:
        owner = file_match.group("owner")
        repo = file_match.group("repo")
        file_info = (file_match.group("branch"), file_match.group("filepath"))
    else:
        # Match general repo URL or slug 'owner/repo'
        slug_match = SLUG_RE.match(input_str)
        repo_match = GITHUB_REPO_RE.search(input_str)
        if slug_match:
            owner = slug_match.group("owner")
            repo = slug_match.group("repo")
            if slug_match.group("pr"):
                pr_number = int(slug_match.group("pr"))
        elif repo_match:
            owner = repo_match.group("owner")
            repo = repo_match.group("repo")
        else:
            parts = input_str.split("/")
            if len(parts) == 2:
                owner = parts[0]
                repo = parts[1]

    if not owner or not repo:
        raise HTTPException(
            status_code=400,
            detail="Could not parse GitHub target. Please provide a valid repository URL, PR URL, commit URL, or 'owner/repo' slug.",
        )

    # Strip any trailing .git or slashes from repo
    repo = repo.rstrip("/").removesuffix(".git")

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-Code-Reviewer-Agent",
    }
    if getattr(settings, "github_token", None):
        headers["Authorization"] = f"Bearer {settings.github_token}"

    diff_text = ""
    target_title = f"{owner}/{repo}"
    target_author = "contributor"
    target_sha = "remote"
    target_ref = f"{owner}/{repo}"
    audit_number = 1

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Case A: Specific File Review
        if file_info:
            branch, filepath = file_info
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}"
            file_resp = await client.get(raw_url, headers={"User-Agent": "AI-Code-Reviewer-Agent"})
            if file_resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"File '{filepath}' not found on branch '{branch}' in {owner}/{repo}.")
            if file_resp.status_code != 200:
                raise HTTPException(status_code=file_resp.status_code, detail="Failed to fetch source file from GitHub.")
            
            file_content = file_resp.text
            diff_lines = [
                f"diff --git a/{filepath} b/{filepath}",
                "--- /dev/null",
                f"+++ b/{filepath}",
                "@@ -0,0 +1 @@"
            ]
            for line in file_content.splitlines():
                diff_lines.append("+" + line)
            diff_text = "\n".join(diff_lines)
            target_title = f"File Audit: {filepath}"
            target_author = owner
            target_sha = branch
            target_ref = f"{owner}/{repo}/{filepath}"
            audit_number = abs(hash(filepath)) % 900000 + 100000

        # Case B: Specific Commit Review
        elif commit_sha:
            meta_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
            commit_resp = await client.get(meta_url, headers=headers)
            if commit_resp.status_code == 200:
                commit_data = commit_resp.json()
                diff_resp = await client.get(meta_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"})
                if diff_resp.status_code == 200:
                    diff_text = diff_resp.text
                target_title = commit_data.get("commit", {}).get("message", f"Commit {commit_sha[:8]}").splitlines()[0]
                target_author = commit_data.get("commit", {}).get("author", {}).get("name", "developer")

            # Fallback to direct public patch if rate-limited or diff empty
            if not diff_text.strip():
                patch_url = f"https://github.com/{owner}/{repo}/commit/{commit_sha}.patch"
                patch_resp = await client.get(patch_url, headers={"User-Agent": "Mozilla/5.0"})
                if patch_resp.status_code == 200 and patch_resp.text.strip():
                    diff_text = patch_resp.text
                    target_title = f"Commit {commit_sha[:8]}"
                    target_author = "developer"

            if not diff_text.strip() and commit_resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Commit '{commit_sha}' not found in {owner}/{repo}.")

            target_sha = commit_sha
            target_ref = f"{owner}/{repo}@{commit_sha[:8]}"
            try:
                audit_number = int(commit_sha[:6], 16) % 900000 + 100000
            except ValueError:
                audit_number = 100001

        # Case C: Pull Request Review (or explicit pr_number)
        elif pr_number:
            meta_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            meta_resp = await client.get(meta_url, headers=headers)
            if meta_resp.status_code == 200:
                pr_data = meta_resp.json()
                diff_resp = await client.get(meta_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"})
                if diff_resp.status_code == 200:
                    diff_text = diff_resp.text
                target_title = pr_data.get("title", f"Pull Request #{pr_number}")
                target_author = pr_data.get("user", {}).get("login", "contributor")
                target_sha = pr_data.get("head", {}).get("sha", "remote")

            # Fallback to direct public patch if rate-limited or diff empty
            if not diff_text.strip():
                patch_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}.patch"
                patch_resp = await client.get(patch_url, headers={"User-Agent": "Mozilla/5.0"})
                if patch_resp.status_code == 200 and patch_resp.text.strip():
                    diff_text = patch_resp.text
                    target_title = f"Pull Request #{pr_number}"
                    target_author = "contributor"
                    target_sha = "remote"

            if not diff_text.strip() and meta_resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Pull Request #{pr_number} not found in {owner}/{repo}.")

            target_ref = f"{owner}/{repo}#{pr_number}"
            audit_number = pr_number

        # Case D: Plain Repo URL or Slug (Auto-discover latest PR or commit)
        else:
            # 1. Try public GitHub API for open PRs if not rate limited
            pulls_url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=1"
            pulls_resp = await client.get(pulls_url, headers=headers)

            if pulls_resp.status_code == 200:
                open_prs = pulls_resp.json()
                if open_prs and isinstance(open_prs, list) and len(open_prs) > 0:
                    pr_item = open_prs[0]
                    p_num = pr_item.get("number")
                    meta_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{p_num}"
                    diff_resp = await client.get(meta_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"})
                    if diff_resp.status_code == 200 and diff_resp.text.strip():
                        diff_text = diff_resp.text
                        target_title = f"[Open PR #{p_num}] {pr_item.get('title')}"
                        target_author = pr_item.get("user", {}).get("login", "contributor")
                        target_sha = pr_item.get("head", {}).get("sha", "remote")
                        target_ref = f"{owner}/{repo}#{p_num}"
                        audit_number = p_num

            # 2. Try public GitHub API for commits if no PR diff found
            if not diff_text.strip() and pulls_resp.status_code == 200:
                commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=5"
                commits_resp = await client.get(commits_url, headers=headers)
                if commits_resp.status_code == 200:
                    commits = commits_resp.json()
                    if commits and isinstance(commits, list) and len(commits) > 0:
                        c_item = commits[0]
                        c_sha = c_item.get("sha")
                        commit_diff_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{c_sha}"
                        diff_resp = await client.get(commit_diff_url, headers={**headers, "Accept": "application/vnd.github.v3.diff"})
                        if diff_resp.status_code == 200 and diff_resp.text.strip():
                            diff_text = diff_resp.text
                            msg_first_line = c_item.get("commit", {}).get("message", "Latest commit").splitlines()[0]
                            target_title = f"[Latest Commit] {msg_first_line}"
                            target_author = c_item.get("commit", {}).get("author", {}).get("name", "developer")
                            target_sha = c_sha
                            target_ref = f"{owner}/{repo}@{c_sha[:8]}"
                            try:
                                audit_number = int(c_sha[:6], 16) % 900000 + 100000
                            except ValueError:
                                audit_number = 100002

            # 3. Seamless Atom Feed + Direct Patch Fallback (Bypasses GitHub API rate limits completely)
            if not diff_text.strip():
                atom_url = f"https://github.com/{owner}/{repo}/commits.atom"
                atom_resp = await client.get(atom_url, headers={"User-Agent": "Mozilla/5.0"})
                if atom_resp.status_code == 404:
                    raise HTTPException(status_code=404, detail=f"Repository '{owner}/{repo}' not found on GitHub. Verify the repo exists and is public.")
                if atom_resp.status_code == 200:
                    atom_content = atom_resp.text
                    shas = re.findall(r"Commit/([0-9a-fA-F]{40})", atom_content)
                    titles = re.findall(r"<title>\s*([^<]+?)\s*</title>", atom_content)
                    title_text = titles[1] if len(titles) > 1 else "Latest Repository Commit"
                    if shas:
                        c_sha = shas[0]
                        patch_url = f"https://github.com/{owner}/{repo}/commit/{c_sha}.patch"
                        patch_resp = await client.get(patch_url, headers={"User-Agent": "Mozilla/5.0"})
                        if patch_resp.status_code == 200 and patch_resp.text.strip():
                            diff_text = patch_resp.text
                            target_title = f"[Latest Commit] {title_text}"
                            target_author = owner
                            target_sha = c_sha
                            target_ref = f"{owner}/{repo}@{c_sha[:8]}"
                            try:
                                audit_number = int(c_sha[:6], 16) % 900000 + 100000
                            except ValueError:
                                audit_number = 100003

            # 4. If still empty, attempt fetching README.md or default file as baseline audit
            if not diff_text.strip():
                for test_branch in ("main", "master"):
                    for test_file in ("README.md", "main.py", "index.js", "package.json"):
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{test_branch}/{test_file}"
                        raw_resp = await client.get(raw_url, headers={"User-Agent": "Mozilla/5.0"})
                        if raw_resp.status_code == 200 and raw_resp.text.strip():
                            diff_lines = [
                                f"diff --git a/{test_file} b/{test_file}",
                                "--- /dev/null",
                                f"+++ b/{test_file}",
                                "@@ -0,0 +1 @@"
                            ]
                            for line in raw_resp.text.splitlines()[:250]:
                                diff_lines.append("+" + line)
                            diff_text = "\n".join(diff_lines)
                            target_title = f"[Repository Snapshot] {test_file}"
                            target_author = owner
                            target_sha = test_branch
                            target_ref = f"{owner}/{repo}/{test_file}"
                            audit_number = 100004
                            break
                    if diff_text.strip():
                        break

    if not diff_text.strip():
        raise HTTPException(
            status_code=400,
            detail=f"Could not retrieve a unified diff for {target_ref}. The repository or commit diff may be empty.",
        )

    # Execute multi-agent review
    review_req = ReviewRequest(
        diff=diff_text,
        language="unknown",
        repository=f"{owner}/{repo}",
        pull_request_number=audit_number,
    )
    rules = storage_repo.get_repo_patterns(f"{owner}/{repo}")
    review_res = engine.review(review_req, repo_rules=rules)

    # Save to persistent storage repository
    record = storage_repo.save_pr_review(
        repo=f"{owner}/{repo}",
        number=audit_number,
        title=target_title,
        author=target_author,
        head_sha=target_sha,
        review_res=review_res,
    )

    return {
        "status": "success",
        "pull_request": target_ref,
        "title": target_title,
        "author": target_author,
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


# --- User Authentication & Email Confirmation Endpoints ---


@router.post("/auth/signup", response_model=AuthResponse, tags=["auth"])
async def register_user(request: SignUpRequest, req: Request) -> AuthResponse:
    """Register a new user account, dispatch a confirmation email, and return session token."""
    # Check if username or email is already registered
    existing_user = storage_repo.get_user_auth(request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail=f"Username '{request.username}' is already taken. Please choose another.")

    existing_email = storage_repo.get_user_auth(request.email)
    if existing_email:
        raise HTTPException(status_code=400, detail=f"An account with email '{request.email}' already exists. Please sign in instead.")

    # Securely hash password using PBKDF2-HMAC-SHA256
    pwd_hash = hash_password(request.password)
    user = storage_repo.create_user(
        username=request.username,
        email=request.email,
        password_hash=pwd_hash,
        full_name=request.full_name,
    )

    # Dispatch confirmation email
    email_record = send_signup_confirmation_email(
        to_email=user.email,
        username=user.username,
        full_name=user.full_name,
        storage_repo=storage_repo,
    )

    token = create_access_token(user.id, user.username, user.email)
    return AuthResponse(
        status="success",
        message=f"Account created successfully for @{user.username}! A confirmation email was sent to {user.email}.",
        token=token,
        user=user,
        email_confirmation_sent=True,
        email_preview=email_record,
    )


@router.post("/auth/signin", response_model=AuthResponse, tags=["auth"])
@router.post("/auth/login", response_model=AuthResponse, tags=["auth"])
async def login_user(request: SignInRequest, req: Request) -> AuthResponse:
    """Sign in an existing user, verify credentials, dispatch a sign-in security notice, and return token."""
    user_record = storage_repo.get_user_auth(request.username_or_email)
    if not user_record:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    user, pwd_hash = user_record
    if not verify_password(request.password, pwd_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Update last login timestamp
    storage_repo.update_last_login(user.id)

    # Client metadata for security alert
    client_ip = req.client.host if req.client else "Unknown IP"
    user_agent = req.headers.get("User-Agent", "Web Browser")

    # Dispatch login notification email
    email_record = send_signin_notification_email(
        to_email=user.email,
        username=user.username,
        ip_address=client_ip,
        user_agent=user_agent,
        storage_repo=storage_repo,
    )

    token = create_access_token(user.id, user.username, user.email)
    return AuthResponse(
        status="success",
        message=f"Welcome back, @{user.username}! Sign-in notification sent to {user.email}.",
        token=token,
        user=user,
        email_confirmation_sent=True,
        email_preview=email_record,
    )


@router.get("/auth/me", response_model=UserProfile, tags=["auth"])
async def get_current_user(req: Request) -> UserProfile:
    """Retrieve current authenticated user profile from Bearer token."""
    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

    token = auth_header.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    user = storage_repo.get_user_by_id(payload.get("uid", ""))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    return user


@router.get("/auth/emails", response_model=list[SentEmailRecord], tags=["auth"])
async def list_sent_emails(recipient: str | None = None, limit: int = 15) -> list[SentEmailRecord]:
    """Inspect sent confirmation emails and security alerts for verification."""
    return storage_repo.get_sent_emails(recipient=recipient, limit=limit)

