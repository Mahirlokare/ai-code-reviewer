"""Tests for baseline heuristic review."""
from app.review.engine import ReviewEngine
from app.schemas.review import ReviewRequest


def run(diff: str):
    return ReviewEngine().review(ReviewRequest(diff=diff, language="python"))


def test_clean_added_line() -> None:
    result = run("@@ -0,0 +1 @@\n+return value")
    assert result.findings == []
    assert result.analyzed_lines == 1


def test_todo_and_print_detected() -> None:
    result = run("@@ -1,0 +1,2 @@\n+# TODO: revisit\n+print('debug')")
    assert any(f.category == "maintainability" for f in result.findings)
    assert any(f.category == "debugging" for f in result.findings)


def test_possible_credential_detected() -> None:
    result = run("@@ -1,0 +1 @@\n+api_key = 'example-not-a-real-key'")
    assert any(f.category == "security" for f in result.findings)


def test_removed_lines_not_analyzed() -> None:
    result = run("@@ -1 +0,0 @@\n-print('debug')")
    assert result.findings == []
    assert result.analyzed_lines == 0


def test_bare_except_warned() -> None:
    result = run("@@ -1,0 +1 @@\n+except: pass")
    assert any(f.category == "correctness" for f in result.findings)
