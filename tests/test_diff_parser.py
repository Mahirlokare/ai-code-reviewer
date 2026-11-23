"""Tests for robust diff parser."""
from app.review.diff_parser import DiffParser


def test_diff_parser_git_headers() -> None:
    diff_text = """diff --git a/app/main.py b/app/main.py
index abc..def 100644
--- a/app/main.py
+++ b/app/main.py
@@ -10,3 +10,4 @@ def run():
     print("existing")
+    print("new line")
"""
    parsed = DiffParser.parse(diff_text)
    assert len(parsed.files) == 1
    assert parsed.files[0].path == "app/main.py"
    assert parsed.total_added_lines == 1

    valid_lines = parsed.get_valid_new_lines("app/main.py")
    assert 11 in valid_lines


def test_diff_parser_unhunked_snippet() -> None:
    snippet = "def test():\n    return True"
    parsed = DiffParser.parse(snippet)
    assert len(parsed.files) == 1
    assert parsed.total_added_lines == 2


def test_diff_parser_binary_and_deletions() -> None:
    diff_text = """diff --git a/logo.png b/logo.png
Binary files a/logo.png and b/logo.png differ
diff --git a/old.py b/old.py
deleted file mode 100644
--- a/old.py
+++ /dev/null
@@ -1,2 +0,0 @@
-line1
-line2
"""
    parsed = DiffParser.parse(diff_text)
    assert len(parsed.files) == 2
    assert parsed.files[0].is_binary is True
    assert parsed.files[1].is_deleted is True
    assert parsed.total_deleted_lines == 2
    assert parsed.total_added_lines == 0
