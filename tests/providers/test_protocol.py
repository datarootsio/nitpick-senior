"""Tests for the GitProvider protocol and data classes."""

import pytest

from src.providers import (
    GitProvider,
    IssueCommentInfo,
    PullRequestInfo,
    ReviewCommentInfo,
)


class TestDataClasses:
    """Tests for protocol data classes."""

    def test_pull_request_info_creation(self):
        """Test PullRequestInfo creation."""
        pr = PullRequestInfo(
            number=123,
            title="Test PR",
            head_sha="abc123",
            base_sha="def456",
            author="testuser",
        )

        assert pr.number == 123
        assert pr.title == "Test PR"
        assert pr.head_sha == "abc123"
        assert pr.base_sha == "def456"
        assert pr.author == "testuser"

    def test_review_comment_info_creation(self):
        """Test ReviewCommentInfo creation."""
        comment = ReviewCommentInfo(
            id="1",
            node_id="MDI0OlB1bGxSZXF1ZXN0UmV2aWV3Q29tbWVudDE=",
            path="src/main.py",
            line=42,
            body="This is a test comment",
            user="testbot",
        )

        assert comment.id == "1"
        assert comment.node_id is not None
        assert comment.path == "src/main.py"
        assert comment.line == 42
        assert comment.body == "This is a test comment"
        assert comment.user == "testbot"

    def test_review_comment_info_none_line(self):
        """Test ReviewCommentInfo with None line (outdated comment)."""
        comment = ReviewCommentInfo(
            id="2",
            node_id=None,
            path="src/main.py",
            line=None,
            body="Outdated comment",
            user="testbot",
        )

        assert comment.line is None
        assert comment.node_id is None

    def test_issue_comment_info_creation(self):
        """Test IssueCommentInfo creation."""
        comment = IssueCommentInfo(
            id="100",
            body="Summary comment",
            user="testbot",
        )

        assert comment.id == "100"
        assert comment.body == "Summary comment"
        assert comment.user == "testbot"


class TestGitProviderProtocol:
    """Tests for the GitProvider protocol."""

    def test_protocol_is_runtime_checkable(self):
        """Test that GitProvider is runtime checkable."""

        class MockProvider:
            bot_username: str = "mockbot"

            def get_pull_request(self, pr_number: int) -> PullRequestInfo:
                return PullRequestInfo(
                    number=pr_number,
                    title="Mock PR",
                    head_sha="abc",
                    base_sha="def",
                    author="mock",
                )

            def get_pr_diff(self, pr_number: int) -> str:
                return ""

            def get_changed_files(self, pr_number: int) -> list[str]:
                return []

            def get_file_content(self, path: str, ref: str | None = None) -> str | None:
                return None

            def get_bot_review_comments(self, pr_number: int) -> list[ReviewCommentInfo]:
                return []

            def get_bot_issue_comments(self, pr_number: int) -> list[IssueCommentInfo]:
                return []

            def post_issue_comment(self, pr_number: int, body: str) -> None:
                pass

            def post_review_comment(
                self, pr_number: int, body: str, commit_sha: str, path: str, line: int
            ) -> None:
                pass

            def edit_review_comment(self, comment_id: str, body: str) -> bool:
                return True

            def edit_issue_comment(self, comment_id: str, body: str) -> bool:
                return True

            def delete_review_comment(self, comment_id: str) -> bool:
                return True

            def minimize_comment(self, comment_id: str) -> bool:
                return False

        provider = MockProvider()
        assert isinstance(provider, GitProvider)
