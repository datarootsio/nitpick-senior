"""Tests for comment formatting and filtering utilities."""

from src.github.comments import (
    deduplicate_comments,
    filter_by_severity,
    format_comment_body,
)
from src.llm.response import ReviewComment


class TestDeduplicateComments:
    def test_removes_exact_duplicates(self):
        comments = [
            ReviewComment(file="a.py", line=1, body="Issue A"),
            ReviewComment(file="b.py", line=2, body="Issue B"),
            ReviewComment(file="c.py", line=3, body="Issue A"),  # Duplicate body
        ]
        result = deduplicate_comments(comments)
        assert len(result) == 2
        assert result[0].body == "Issue A"
        assert result[1].body == "Issue B"

    def test_keeps_unique_comments(self):
        comments = [
            ReviewComment(file="a.py", line=1, body="Issue A"),
            ReviewComment(file="b.py", line=2, body="Issue B"),
            ReviewComment(file="c.py", line=3, body="Issue C"),
        ]
        result = deduplicate_comments(comments)
        assert len(result) == 3

    def test_empty_list(self):
        result = deduplicate_comments([])
        assert result == []

    def test_preserves_order(self):
        comments = [
            ReviewComment(file="a.py", line=1, body="First"),
            ReviewComment(file="b.py", line=2, body="Second"),
            ReviewComment(file="c.py", line=3, body="Third"),
        ]
        result = deduplicate_comments(comments)
        assert [c.body for c in result] == ["First", "Second", "Third"]


class TestFilterBySeverity:
    def test_filter_to_error_only(self):
        comments = [
            ReviewComment(file="a.py", line=1, body="Error", severity="error"),
            ReviewComment(file="b.py", line=2, body="Warning", severity="warning"),
            ReviewComment(file="c.py", line=3, body="Info", severity="info"),
        ]
        result = filter_by_severity(comments, "error")
        assert len(result) == 1
        assert result[0].severity == "error"

    def test_filter_to_warning_and_above(self):
        comments = [
            ReviewComment(file="a.py", line=1, body="Error", severity="error"),
            ReviewComment(file="b.py", line=2, body="Warning", severity="warning"),
            ReviewComment(file="c.py", line=3, body="Info", severity="info"),
        ]
        result = filter_by_severity(comments, "warning")
        assert len(result) == 2
        assert all(c.severity in ("error", "warning") for c in result)

    def test_filter_to_info_includes_all(self):
        comments = [
            ReviewComment(file="a.py", line=1, body="Error", severity="error"),
            ReviewComment(file="b.py", line=2, body="Warning", severity="warning"),
            ReviewComment(file="c.py", line=3, body="Info", severity="info"),
        ]
        result = filter_by_severity(comments, "info")
        assert len(result) == 3

    def test_empty_list(self):
        result = filter_by_severity([], "warning")
        assert result == []


class TestFormatCommentBody:
    def test_basic_warning(self):
        comment = ReviewComment(
            file="a.py",
            line=1,
            body="This is a problem",
            severity="warning",
        )
        result = format_comment_body(comment)
        assert ":warning:" in result
        assert "WARNING" in result
        assert "This is a problem" in result

    def test_error_with_category(self):
        comment = ReviewComment(
            file="a.py",
            line=1,
            body="Security issue",
            severity="error",
            category="Security",
        )
        result = format_comment_body(comment)
        assert ":lock:" in result
        assert "Security" in result
        assert ":x:" in result
        assert "ERROR" in result

    def test_includes_why_block(self):
        comment = ReviewComment(
            file="a.py",
            line=1,
            body="Problem description",
            why="Because it violates invariant X",
            severity="warning",
        )
        result = format_comment_body(comment)
        assert "Why this matters:" in result
        assert "violates invariant X" in result

    def test_info_severity(self):
        comment = ReviewComment(
            file="a.py",
            line=1,
            body="Just FYI",
            severity="info",
        )
        result = format_comment_body(comment)
        assert ":information_source:" in result
        assert "INFO" in result
