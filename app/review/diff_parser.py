"""Robust unified diff parsing and changed-line mapping."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_lines>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_lines>\d+))? @@(?P<tail>.*)$"
)
FILE_DIFF_RE = re.compile(r"^diff --git a/(?P<old_path>.+) b/(?P<new_path>.+)$")
BINARY_DIFF_RE = re.compile(r"^Binary files (.+) and (.+) differ$")


class LineType(str, Enum):
    ADD = "ADD"
    DEL = "DEL"
    CTX = "CTX"


@dataclass
class DiffLine:
    line_type: LineType
    content: str
    old_line_no: int | None = None
    new_line_no: int | None = None


@dataclass
class DiffHunk:
    header: str
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    lines: list[DiffLine] = field(default_factory=list)


@dataclass
class DiffFile:
    old_path: str | None
    new_path: str | None
    is_binary: bool = False
    is_deleted: bool = False
    is_new: bool = False
    hunks: list[DiffHunk] = field(default_factory=list)

    @property
    def path(self) -> str:
        return self.new_path or self.old_path or "unknown"

    @property
    def added_lines(self) -> list[DiffLine]:
        return [line for hunk in self.hunks for line in hunk.lines if line.line_type == LineType.ADD]

    @property
    def deleted_lines(self) -> list[DiffLine]:
        return [line for hunk in self.hunks for line in hunk.lines if line.line_type == LineType.DEL]


@dataclass
class ParsedDiff:
    files: list[DiffFile] = field(default_factory=list)

    @property
    def total_added_lines(self) -> int:
        return sum(len(f.added_lines) for f in self.files)

    @property
    def total_deleted_lines(self) -> int:
        return sum(len(f.deleted_lines) for f in self.files)

    def get_valid_new_lines(self, file_path: str) -> set[int]:
        """Return the set of valid line numbers added in the given file for inline commenting."""
        for f in self.files:
            if f.path == file_path:
                return {
                    line.new_line_no
                    for line in f.added_lines
                    if line.new_line_no is not None
                }
        return set()


class DiffParser:
    """Parses standard multi-file git diffs or single patch snippets."""

    @classmethod
    def parse(cls, diff_text: str) -> ParsedDiff:
        parsed = ParsedDiff()
        if not diff_text or not diff_text.strip():
            return parsed

        current_file: DiffFile | None = None
        current_hunk: DiffHunk | None = None
        old_line_counter = 0
        new_line_counter = 0

        lines = diff_text.splitlines()
        i = 0
        while i < len(lines):
            raw = lines[i]

            # Check for file header (diff --git a/foo b/foo)
            git_match = FILE_DIFF_RE.match(raw)
            if git_match:
                current_file = DiffFile(
                    old_path=git_match.group("old_path"),
                    new_path=git_match.group("new_path"),
                )
                parsed.files.append(current_file)
                current_hunk = None
                i += 1
                continue

            # Check for binary file diff
            if BINARY_DIFF_RE.match(raw):
                if current_file:
                    current_file.is_binary = True
                i += 1
                continue

            # Check for deleted/new file metadata
            if raw.startswith("deleted file mode"):
                if current_file:
                    current_file.is_deleted = True
                i += 1
                continue
            if raw.startswith("new file mode"):
                if current_file:
                    current_file.is_new = True
                i += 1
                continue

            # Check for rename from / rename to
            if raw.startswith("rename from ") and current_file:
                current_file.old_path = raw[12:].strip()
                i += 1
                continue
            if raw.startswith("rename to ") and current_file:
                current_file.new_path = raw[10:].strip()
                i += 1
                continue

            # Check for --- and +++ lines if git diff header was absent
            if raw.startswith("--- "):
                old_p = raw[4:].strip()
                if old_p.startswith("a/"):
                    old_p = old_p[2:]
                if not current_file:
                    current_file = DiffFile(old_path=old_p, new_path=None)
                    parsed.files.append(current_file)
                else:
                    current_file.old_path = old_p
                i += 1
                continue

            if raw.startswith("+++ "):
                new_p = raw[4:].strip()
                if new_p.startswith("b/"):
                    new_p = new_p[2:]
                if not current_file:
                    current_file = DiffFile(old_path=None, new_path=new_p)
                    parsed.files.append(current_file)
                else:
                    current_file.new_path = new_p
                i += 1
                continue

            # Check for hunk header (@@ -1,5 +1,6 @@)
            hunk_match = HUNK_HEADER_RE.match(raw)
            if hunk_match:
                if not current_file:
                    current_file = DiffFile(old_path="unknown", new_path="unknown")
                    parsed.files.append(current_file)

                old_start = int(hunk_match.group("old_start"))
                old_len = int(hunk_match.group("old_lines") or "1")
                new_start = int(hunk_match.group("new_start"))
                new_len = int(hunk_match.group("new_lines") or "1")

                current_hunk = DiffHunk(
                    header=raw,
                    old_start=old_start,
                    old_lines=old_len,
                    new_start=new_start,
                    new_lines=new_len,
                )
                current_file.hunks.append(current_hunk)
                old_line_counter = old_start
                new_line_counter = new_start
                i += 1
                continue

            # Process diff line contents inside a hunk
            if current_hunk:
                if raw.startswith("+") and not raw.startswith("+++"):
                    current_hunk.lines.append(
                        DiffLine(
                            line_type=LineType.ADD,
                            content=raw[1:],
                            new_line_no=new_line_counter,
                        )
                    )
                    new_line_counter += 1
                elif raw.startswith("-") and not raw.startswith("---"):
                    current_hunk.lines.append(
                        DiffLine(
                            line_type=LineType.DEL,
                            content=raw[1:],
                            old_line_no=old_line_counter,
                        )
                    )
                    old_line_counter += 1
                elif raw.startswith(" ") or raw == "":
                    current_hunk.lines.append(
                        DiffLine(
                            line_type=LineType.CTX,
                            content=raw[1:] if raw.startswith(" ") else "",
                            old_line_no=old_line_counter,
                            new_line_no=new_line_counter,
                        )
                    )
                    old_line_counter += 1
                    new_line_counter += 1

            i += 1

        # Fallback for plain un-hunked snippets
        if not parsed.files and diff_text.strip():
            single_file = DiffFile(old_path="snippet", new_path="snippet")
            single_hunk = DiffHunk(header="@@ -1 +1 @@", old_start=1, old_lines=1, new_start=1, new_lines=1)
            line_no = 1
            for line in diff_text.splitlines():
                if line.startswith("-"):
                    continue
                code = line[1:] if line.startswith("+") else line
                single_hunk.lines.append(
                    DiffLine(line_type=LineType.ADD, content=code, new_line_no=line_no)
                )
                line_no += 1
            single_file.hunks.append(single_hunk)
            parsed.files.append(single_file)

        return parsed
