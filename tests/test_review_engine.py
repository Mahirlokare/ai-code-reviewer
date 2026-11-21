"""Tests for baseline heuristic review."""
from app.review.engine import ReviewEngine
from app.schemas.review import ReviewRequest


def test_empty_findings_for_clean_added_line() -> None:
    result = ReviewEngine().review(ReviewRequest(diff="@@ -0,0 +1 @@\n+return value", language="python"))
    assert result.findings == []
    assert result.analyzed_lines == 1


def test_todo_and_debug_print_detected() -> None:
    diff = "@@ -1,0 +1,2 @@\n+# TODO: revisit\n+print('debug')"
    result = ReviewEngine().review(ReviewRequest(diff=diff, language="python"))
    assert any(f.category == "maintainability" for f in result.findings)
    assert any(f.category == "debugging" for f in result.findings)


def test_possible_credential_pattern_detected() -> None:
    diff = "@@ -1,0 +1 @@\n+api_key = 'example-not-a-real-key'"
    result = ReviewEngine().review(ReviewRequest(diff=diff, language="python"))
    assert any(f.category == "security" for f in result.findings)


def test_deleted_lines_not_analyzed_as_added() -> None:
    diff = "@@ -1 +0,0 @@\n-print('debug')"
    result = ReviewEngine().review(ReviewRequest(diff=diff, language="python"))
    assert result.findings == []
    assert result.analyzed_lines == 0
