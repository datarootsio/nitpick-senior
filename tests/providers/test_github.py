"""Tests for the GitHub provider."""

from unittest.mock import MagicMock, patch

import pytest

from src.providers import GitProvider
from src.providers.github import GitHubProvider


class TestGitHubProviderInit:
    """Tests for GitHubProvider initialization."""

    @patch("src.providers.github.Github")
    def test_init_creates_client(self, mock_github):
        """Test that initialization creates a GitHub client."""
        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo

        provider = GitHubProvider(
            token="test-token",
            repo_owner="owner",
            repo_name="repo",
        )

        mock_github.assert_called_once_with("test-token")
        mock_github.return_value.get_repo.assert_called_once_with("owner/repo")
        assert provider.bot_username == "github-actions[bot]"

    @patch("src.providers.github.Github")
    def test_implements_protocol(self, mock_github):
        """Test that GitHubProvider implements GitProvider protocol."""
        mock_github.return_value.get_repo.return_value = MagicMock()

        provider = GitHubProvider(
            token="test-token",
            repo_owner="owner",
            repo_name="repo",
        )

        assert isinstance(provider, GitProvider)


class TestGitHubProviderMethods:
    """Tests for GitHubProvider methods."""

    @pytest.fixture
    def provider(self):
        """Create a mocked GitHubProvider."""
        with patch("src.providers.github.Github") as mock_github:
            mock_repo = MagicMock()
            mock_github.return_value.get_repo.return_value = mock_repo
            provider = GitHubProvider(
                token="test-token",
                repo_owner="owner",
                repo_name="repo",
            )
            provider._mock_repo = mock_repo
            yield provider

    def test_get_pull_request(self, provider):
        """Test get_pull_request returns PullRequestInfo."""
        mock_pr = MagicMock()
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.head.sha = "abc123"
        mock_pr.base.sha = "def456"
        mock_pr.user.login = "testuser"
        provider._mock_repo.get_pull.return_value = mock_pr

        pr_info = provider.get_pull_request(123)

        assert pr_info.number == 123
        assert pr_info.title == "Test PR"
        assert pr_info.head_sha == "abc123"
        assert pr_info.base_sha == "def456"
        assert pr_info.author == "testuser"

    def test_get_pull_request_caches(self, provider):
        """Test that get_pull_request caches results."""
        mock_pr = MagicMock()
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.head.sha = "abc123"
        mock_pr.base.sha = "def456"
        mock_pr.user.login = "testuser"
        provider._mock_repo.get_pull.return_value = mock_pr

        # First call
        provider.get_pull_request(123)
        # Second call should use cache
        provider.get_pull_request(123)

        # Should only call get_pull once due to caching
        assert provider._mock_repo.get_pull.call_count == 1

    def test_get_changed_files(self, provider):
        """Test get_changed_files returns file paths."""
        mock_pr = MagicMock()
        mock_file1 = MagicMock()
        mock_file1.filename = "src/main.py"
        mock_file2 = MagicMock()
        mock_file2.filename = "tests/test_main.py"
        mock_pr.get_files.return_value = [mock_file1, mock_file2]
        provider._mock_repo.get_pull.return_value = mock_pr

        files = provider.get_changed_files(123)

        assert files == ["src/main.py", "tests/test_main.py"]

    def test_get_file_content_success(self, provider):
        """Test get_file_content returns content."""
        mock_content = MagicMock()
        mock_content.decoded_content = b"print('hello')"
        provider._mock_repo.get_contents.return_value = mock_content

        content = provider.get_file_content("src/main.py", "abc123")

        assert content == "print('hello')"

    def test_get_file_content_not_found(self, provider):
        """Test get_file_content returns None for missing files."""
        provider._mock_repo.get_contents.side_effect = Exception("Not found")

        content = provider.get_file_content("missing.py")

        assert content is None

    def test_get_bot_review_comments(self, provider):
        """Test get_bot_review_comments filters by bot username."""
        mock_pr = MagicMock()
        mock_comment1 = MagicMock()
        mock_comment1.id = 1
        mock_comment1.node_id = "node1"
        mock_comment1.path = "src/main.py"
        mock_comment1.line = 10
        mock_comment1.body = "Bot comment"
        mock_comment1.user.login = "github-actions[bot]"

        mock_comment2 = MagicMock()
        mock_comment2.id = 2
        mock_comment2.user.login = "human-user"

        mock_pr.get_review_comments.return_value = [mock_comment1, mock_comment2]
        provider._mock_repo.get_pull.return_value = mock_pr

        comments = provider.get_bot_review_comments(123)

        assert len(comments) == 1
        assert comments[0].id == "1"
        assert comments[0].user == "github-actions[bot]"

    def test_post_issue_comment(self, provider):
        """Test post_issue_comment creates comment."""
        mock_pr = MagicMock()
        provider._mock_repo.get_pull.return_value = mock_pr

        provider.post_issue_comment(123, "Test comment")

        mock_pr.create_issue_comment.assert_called_once_with("Test comment")

    def test_post_review_comment(self, provider):
        """Test post_review_comment creates inline comment."""
        mock_pr = MagicMock()
        mock_commit = MagicMock()
        provider._mock_repo.get_pull.return_value = mock_pr
        provider._mock_repo.get_commit.return_value = mock_commit

        provider.post_review_comment(
            pr_number=123,
            body="Review comment",
            commit_sha="abc123",
            path="src/main.py",
            line=42,
        )

        mock_pr.create_review_comment.assert_called_once_with(
            body="Review comment",
            commit=mock_commit,
            path="src/main.py",
            line=42,
        )
