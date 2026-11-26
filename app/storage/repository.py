"""Thread-safe SQLite persistent storage for PR audit history and learned patterns."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.schemas.auth import SentEmailRecord, UserProfile
from app.schemas.review import Finding, ReviewResponse
from app.services.crypto_service import decrypt_sensitive, encrypt_sensitive


@dataclass
class PullRequestRecord:
    id: str
    repo: str
    number: int
    title: str
    author: str
    head_sha: str
    status: str
    score: int
    summary: str
    findings: list[Finding] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    analyzed_lines: int = 0


@dataclass
class RepoPatternRecord:
    id: str
    repo: str
    pattern_type: str
    rule_description: str
    confidence: float
    occurrences: int = 1


class StorageRepository:
    """Persistent storage using SQLite with in-memory caching."""

    def __init__(self, db_path: str = "reviews.db") -> None:
        self.db_path = db_path
        self.pull_requests: dict[str, PullRequestRecord] = {}
        self.repo_patterns: dict[str, list[RepoPatternRecord]] = {}
        self.processed_shas: set[str] = set()

        self._init_db()
        self._load_from_db()
        if not self.pull_requests:
            self._seed_initial_records()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pull_requests (
                    id TEXT PRIMARY KEY,
                    repo TEXT NOT NULL,
                    number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    head_sha TEXT NOT NULL,
                    status TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    findings_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    analyzed_lines INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repo_patterns (
                    id TEXT PRIMARY KEY,
                    repo TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    rule_description TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    occurrences INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_shas (
                    sha TEXT PRIMARY KEY
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    created_at REAL NOT NULL,
                    last_login REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sent_emails (
                    id TEXT PRIMARY KEY,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body_html TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    email_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def _load_from_db(self) -> None:
        with self._get_connection() as conn:
            # Load processed SHAs
            cur = conn.execute("SELECT sha FROM processed_shas")
            for row in cur.fetchall():
                self.processed_shas.add(row["sha"])

            # Load PRs (decrypt sensitive summary and findings at rest)
            cur = conn.execute("SELECT * FROM pull_requests ORDER BY created_at DESC")
            for row in cur.fetchall():
                findings_raw = decrypt_sensitive(row["findings_json"]) or "[]"
                findings_data = json.loads(findings_raw)
                findings = [Finding(**f) for f in findings_data]
                pr = PullRequestRecord(
                    id=row["id"],
                    repo=row["repo"],
                    number=row["number"],
                    title=row["title"],
                    author=row["author"],
                    head_sha=row["head_sha"],
                    status=row["status"],
                    score=row["score"],
                    summary=decrypt_sensitive(row["summary"]) or "",
                    findings=findings,
                    created_at=row["created_at"],
                    analyzed_lines=row["analyzed_lines"],
                )
                self.pull_requests[pr.id] = pr

            # Load patterns
            cur = conn.execute("SELECT * FROM repo_patterns")
            for row in cur.fetchall():
                repo = row["repo"]
                if repo not in self.repo_patterns:
                    self.repo_patterns[repo] = []
                self.repo_patterns[repo].append(
                    RepoPatternRecord(
                        id=row["id"],
                        repo=repo,
                        pattern_type=row["pattern_type"],
                        rule_description=row["rule_description"],
                        confidence=row["confidence"],
                        occurrences=row["occurrences"],
                    )
                )

    def _seed_initial_records(self) -> None:
        self.save_pr_review(
            repo="acme/platform-api",
            number=284,
            title="Refactor authentication middleware",
            author="sarahchen",
            head_sha="a1b2c3d4e5f67890",
            review_res=ReviewResponse(
                summary="🚨 Critical security vulnerability detected in auth handler.",
                findings=[
                    Finding(
                        severity="critical",
                        category="security",
                        title="Potential hard-coded credential",
                        description="Detected API token assignment in auth config.",
                        line=42,
                        file_path="config/auth.py",
                        suggestion="Move secret to os.environ.get('AUTH_SECRET')",
                    ),
                    Finding(
                        severity="medium",
                        category="correctness",
                        title="Broad exception handler",
                        description="Bare except clause catches all exceptions.",
                        line=108,
                        file_path="services/session.py",
                        suggestion="except AuthenticationError as err:\n    logger.warning(err)",
                    ),
                ],
                analyzed_lines=146,
                engine="heuristic-v1",
            ),
        )

        self.save_pr_review(
            repo="acme/platform-api",
            number=283,
            title="Add caching to user endpoints",
            author="marcus-dev",
            head_sha="f6e5d4c3b2a10987",
            review_res=ReviewResponse(
                summary="✅ Clean review. Minor maintainability suggestions.",
                findings=[
                    Finding(
                        severity="low",
                        category="debugging",
                        title="Leftover debug statement",
                        description="Found print statement in cache worker.",
                        line=16,
                        file_path="handlers/login.py",
                        suggestion="logger.debug('Cache populated')",
                    ),
                ],
                analyzed_lines=89,
                engine="heuristic-v1",
            ),
        )

    def is_sha_processed(self, sha: str) -> bool:
        return sha in self.processed_shas

    def mark_sha_processed(self, sha: str) -> None:
        self.processed_shas.add(sha)
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO processed_shas (sha) VALUES (?)", (sha,))
            conn.commit()

    def save_pr_review(
        self,
        repo: str,
        number: int,
        title: str,
        author: str,
        head_sha: str,
        review_res: ReviewResponse,
    ) -> PullRequestRecord:
        crit_count = sum(1 for f in review_res.findings if f.severity == "critical")
        high_count = sum(1 for f in review_res.findings if f.severity == "high")

        score = max(0, 100 - (crit_count * 25) - (high_count * 10) - (len(review_res.findings) * 3))
        status = "Action Required" if crit_count > 0 else ("Reviewed" if score >= 80 else "Review Needed")

        pr_id = f"#{number}"
        findings_json = json.dumps([f.model_dump() for f in review_res.findings])
        created_at = time.time()

        record = PullRequestRecord(
            id=pr_id,
            repo=repo,
            number=number,
            title=title,
            author=author,
            head_sha=head_sha,
            status=status,
            score=score,
            summary=review_res.summary,
            findings=review_res.findings,
            created_at=created_at,
            analyzed_lines=review_res.analyzed_lines,
        )
        self.pull_requests[pr_id] = record
        self.mark_sha_processed(head_sha)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pull_requests
                (id, repo, number, title, author, head_sha, status, score, summary, findings_json, created_at, analyzed_lines)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pr_id, repo, number, title, author, head_sha, status, score,
                encrypt_sensitive(review_res.summary), encrypt_sensitive(findings_json), created_at, review_res.analyzed_lines
            ))
            conn.commit()

        return record

    def list_pull_requests(self) -> list[dict[str, Any]]:
        records = sorted(self.pull_requests.values(), key=lambda r: r.created_at, reverse=True)
        return [
            {
                "id": r.id,
                "title": r.title,
                "repo": r.repo,
                "author": r.author,
                "time": "Just now" if time.time() - r.created_at < 120 else f"{int((time.time() - r.created_at) // 60)} min ago",
                "status": r.status,
                "score": r.score,
                "files": len({f.file_path for f in r.findings if f.file_path}) or 1,
                "additions": r.analyzed_lines,
                "deletions": 0,
                "avatar": (r.author[:2] if r.author else "GH").upper(),
                "findings": [f.model_dump() for f in r.findings],
                "summary": r.summary,
            }
            for r in records
        ]

    def get_metrics(self) -> dict[str, Any]:
        total_prs = len(self.pull_requests)
        total_findings = sum(len(r.findings) for r in self.pull_requests.values())
        critical_issues = sum(
            sum(1 for f in r.findings if f.severity in ("critical", "high"))
            for r in self.pull_requests.values()
        )
        avg_score = (
            int(sum(r.score for r in self.pull_requests.values()) / total_prs)
            if total_prs > 0
            else 100
        )
        return {
            "total_pull_requests": total_prs,
            "total_findings": total_findings,
            "critical_issues_blocked": critical_issues,
            "average_quality_score": avg_score,
            "pipeline_status": "Healthy",
        }

    def add_learned_pattern(self, repo: str, pattern_type: str, description: str, confidence: float = 0.8) -> None:
        if repo not in self.repo_patterns:
            self.repo_patterns[repo] = []
        pattern_id = f"pat_{int(time.time() * 1000)}"
        record = RepoPatternRecord(
            id=pattern_id,
            repo=repo,
            pattern_type=pattern_type,
            rule_description=description,
            confidence=confidence,
        )
        self.repo_patterns[repo].append(record)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO repo_patterns
                (id, repo, pattern_type, rule_description, confidence, occurrences)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pattern_id, repo, pattern_type, description, confidence, 1))
            conn.commit()

    def get_repo_patterns(self, repo: str) -> list[str]:
        patterns = self.repo_patterns.get(repo, [])
        return [p.rule_description for p in patterns]

    # --- User Authentication & Management ---

    def create_user(
        self, username: str, email: str, password_hash: str, full_name: str | None = None
    ) -> UserProfile:
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, username, password_hash, full_name, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, email.lower().strip(), username.strip(), password_hash, encrypt_sensitive(full_name), now, now),
            )
            conn.commit()

        return UserProfile(
            id=user_id,
            username=username.strip(),
            email=email.lower().strip(),
            full_name=full_name,
            created_at=now,
            last_login=now,
            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
        )

    def upsert_user(
        self, user_id: str, email: str, username: str, full_name: str | None = None
    ) -> UserProfile:
        now = time.time()
        clean_email = email.lower().strip()
        clean_user = username.strip() or clean_email.split("@")[0]
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM users WHERE id = ? OR email = ?", (user_id, clean_email))
            row = cur.fetchone()
            if row:
                conn.execute(
                    "UPDATE users SET last_login = ?, full_name = coalesce(?, full_name) WHERE id = ?",
                    (now, encrypt_sensitive(full_name), row["id"]),
                )
                conn.commit()
                return self.get_user_by_id(row["id"])
            else:
                conn.execute(
                    """
                    INSERT INTO users (id, email, username, password_hash, full_name, created_at, last_login)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, clean_email, clean_user, "oauth_provider_supabase", encrypt_sensitive(full_name), now, now),
                )
                conn.commit()
                return self.get_user_by_id(user_id)

    def get_user_by_id(self, user_id: str) -> UserProfile | None:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            return UserProfile(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                full_name=decrypt_sensitive(row["full_name"]),
                created_at=row["created_at"],
                last_login=row["last_login"],
                avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={row['username']}",
            )

    def get_user_auth(self, username_or_email: str) -> tuple[UserProfile, str] | None:
        term = username_or_email.lower().strip()
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
                (term, term),
            )
            row = cur.fetchone()
            if not row:
                return None
            profile = UserProfile(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                full_name=decrypt_sensitive(row["full_name"]),
                created_at=row["created_at"],
                last_login=row["last_login"],
                avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={row['username']}",
            )
            return profile, row["password_hash"]

    def update_last_login(self, user_id: str) -> None:
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user_id))
            conn.commit()

    # --- Email Records & Confirmation Logs ---

    def save_sent_email(
        self,
        recipient: str,
        subject: str,
        body_html: str,
        body_text: str,
        email_type: str,
        status: str = "sent",
    ) -> SentEmailRecord:
        email_id = f"eml_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sent_emails (id, recipient, subject, body_html, body_text, email_type, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email_id,
                    recipient.lower().strip(),
                    subject,
                    encrypt_sensitive(body_html),
                    encrypt_sensitive(body_text),
                    email_type,
                    status,
                    now,
                ),
            )
            conn.commit()

        return SentEmailRecord(
            id=email_id,
            recipient=recipient.lower().strip(),
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            email_type=email_type,
            status=status,
            created_at=now,
        )

    def get_sent_emails(self, recipient: str | None = None, limit: int = 20) -> list[SentEmailRecord]:
        with self._get_connection() as conn:
            if recipient:
                cur = conn.execute(
                    "SELECT * FROM sent_emails WHERE LOWER(recipient) = ? ORDER BY created_at DESC LIMIT ?",
                    (recipient.lower().strip(), limit),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM sent_emails ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            rows = cur.fetchall()
            return [
                SentEmailRecord(
                    id=r["id"],
                    recipient=r["recipient"],
                    subject=r["subject"],
                    body_html=decrypt_sensitive(r["body_html"]) or "",
                    body_text=decrypt_sensitive(r["body_text"]) or "",
                    email_type=r["email_type"],
                    status=r["status"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]



# Singleton instance across application
storage_repo = StorageRepository()
