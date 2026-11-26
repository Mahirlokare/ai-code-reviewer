"""High-end security middleware, rate limiting, brute-force protection, and SSRF guards."""
from __future__ import annotations

import ipaddress
import re
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

GITHUB_IDENT_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9._-]{0,98}[a-zA-Z0-9])?$")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects OWASP-recommended security headers on every HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "img-src 'self' data: https://api.dicebear.com; "
            "connect-src 'self' https://ai-code-reviewer-api-z7hr.onrender.com https://*.supabase.co; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        if request.url.path.startswith("/api/v1/auth"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response


class SlidingWindowRateLimiter:
    """Thread-safe per-IP sliding-window rate limiter to mitigate DoS and brute-force attacks."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._buckets[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - q[0])))
                return False, retry_after
            q.append(now)
            return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies tiered rate limits: strict on /auth/* and moderate on general /api/v1/*."""

    def __init__(self, app, auth_limit: int = 12, api_limit: int = 60, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.auth_limiter = SlidingWindowRateLimiter(auth_limit, window_seconds)
        self.api_limiter = SlidingWindowRateLimiter(api_limit, window_seconds)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if request.method == "OPTIONS" or path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if path.startswith("/api/v1/auth/signin") or path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/signup"):
            allowed, retry = self.auth_limiter.check(f"auth:{client_ip}")
        elif path.startswith("/api/"):
            allowed, retry = self.api_limiter.check(f"api:{client_ip}")
        else:
            allowed, retry = True, 0

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again shortly."},
                headers={"Retry-After": str(retry)},
            )
        return await call_next(request)


class LoginBruteForceGuard:
    """Locks out repeated failed login attempts per account/IP."""

    def __init__(self, max_failures: int = 5, lockout_seconds: int = 300) -> None:
        self.max_failures = max_failures
        self.lockout_seconds = lockout_seconds
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_locked(self, identifier: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.lockout_seconds
        key = identifier.strip().lower()
        with self._lock:
            attempts = [ts for ts in self._failures.get(key, []) if ts >= cutoff]
            self._failures[key] = attempts
            if len(attempts) >= self.max_failures:
                retry = max(1, int(self.lockout_seconds - (now - attempts[0])))
                return True, retry
            return False, 0

    def record_failure(self, identifier: str) -> None:
        now = time.monotonic()
        key = identifier.strip().lower()
        with self._lock:
            self._failures[key].append(now)

    def clear(self, identifier: str) -> None:
        key = identifier.strip().lower()
        with self._lock:
            self._failures.pop(key, None)


login_guard = LoginBruteForceGuard()


def validate_github_identifier(value: str, field_name: str = "identifier") -> str:
    """Strictly validate GitHub owner/repo names to prevent SSRF and path traversal."""
    cleaned = value.strip()
    if ".." in cleaned or "/" in cleaned or "\\" in cleaned or not GITHUB_IDENT_RE.match(cleaned):
        raise HTTPException(status_code=400, detail=f"Invalid GitHub {field_name}.")
    try:
        ipaddress.ip_address(cleaned)
        raise HTTPException(status_code=400, detail=f"IP addresses are not permitted for {field_name}.")
    except ValueError:
        pass
    return cleaned
