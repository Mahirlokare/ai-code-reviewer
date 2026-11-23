"""Tests for SQLite persistent storage repository."""
import os
import tempfile
from app.schemas.review import Finding, ReviewResponse
from app.storage.repository import StorageRepository


def test_storage_sqlite_crud() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        repo = StorageRepository(db_path=db_path)
        assert len(repo.pull_requests) >= 2  # Seeded initial PRs

        # Test deduplication
        assert not repo.is_sha_processed("newsha123")
        repo.mark_sha_processed("newsha123")
        assert repo.is_sha_processed("newsha123")

        # Test saving PR review
        review_res = ReviewResponse(
            summary="Test review summary",
            findings=[
                Finding(
                    severity="high",
                    category="security",
                    title="Test finding",
                    description="Test description",
                    line=10,
                    file_path="main.py",
                    suggestion="fix",
                )
            ],
            analyzed_lines=25,
            engine="test-engine",
        )
        record = repo.save_pr_review(
            repo="test/repo",
            number=99,
            title="Feature PR",
            author="tester",
            head_sha="sha999",
            review_res=review_res,
        )
        assert record.id == "#99"
        assert record.status == "Reviewed" or "Review" in record.status

        # Test reload from disk
        repo_reloaded = StorageRepository(db_path=db_path)
        assert "#99" in repo_reloaded.pull_requests
        assert repo_reloaded.is_sha_processed("sha999")

        # Test metrics
        metrics = repo_reloaded.get_metrics()
        assert metrics["total_pull_requests"] >= 3
        assert metrics["pipeline_status"] == "Healthy"

        # Test learned patterns
        repo_reloaded.add_learned_pattern("test/repo", "convention", "Always use typed variables")
        patterns = repo_reloaded.get_repo_patterns("test/repo")
        assert "Always use typed variables" in patterns
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
