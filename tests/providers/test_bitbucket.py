"""Tests for the Bitbucket provider."""

from unittest.mock import MagicMock, patch

import pytest

from src.providers import GitProvider


class TestBitbucketProviderInit:
    """Tests for BitbucketProvider initialization."""

    @patch("src.providers.bitbucket.BitbucketCloud")
    def test_init_creates_client(self, mock_bitbucket):
        """Test that initialization creates a Bitbucket client."""
        from src.providers.bitbucket import BitbucketProvider

        provider = BitbucketProvider(
            username="testuser",
            app_password="test-password",
            workspace="myworkspace",
            repo_slug="myrepo",
        )

        mock_bitbucket.assert_called_once_with(username="testuser", password="test-password")
        assert provider.bot_username == "testuser"

    @patch("src.providers.bitbucket.BitbucketCloud")
    def test_implements_protocol(self, mock_bitbucket):
        """Test that BitbucketProvider implements GitProvider protocol."""
        from src.providers.bitbucket import BitbucketProvider

        provider = BitbucketProvider(
            username="testuser",
            app_password="test-password",
            workspace="myworkspace",
            repo_slug="myrepo",
        )

        assert isinstance(provider, GitProvider)


class TestBitbucketProviderMethods:
    """Tests for BitbucketProvider methods."""

    @pytest.fixture
    def provider(self):
        """Create a mocked BitbucketProvider."""
        with patch("src.providers.bitbucket.BitbucketCloud") as mock_bitbucket:
            mock_client = MagicMock()
            mock_bitbucket.return_value = mock_client

            from src.providers.bitbucket import BitbucketProvider

            provider = BitbucketProvider(
                username="testuser",
                app_password="test-password",
                workspace="myworkspace",
                repo_slug="myrepo",
            )
            provider._mock_client = mock_client
            yield provider

    def test_get_pull_request(self, provider):
        """Test get_pull_request returns PullRequestInfo."""
        mock_pr = MagicMock()
        mock_pr.data = {
            "id": 123,
            "title": "Test PR",
            "source": {"commit": {"hash": "abc123"}},
            "destination": {"commit": {"hash": "def456"}},
            "author": {"nickname": "testuser"},
        }
        provider._mock_client.repositories.get.return_value.pullrequests.get.return_value = (
            mock_pr
        )

        pr_info = provider.get_pull_request(123)

        assert pr_info.number == 123
        assert pr_info.title == "Test PR"
        assert pr_info.head_sha == "abc123"
        assert pr_info.base_sha == "def456"
        assert pr_info.author == "testuser"

    def test_get_changed_files(self, provider):
        """Test get_changed_files returns file paths."""
        mock_pr = MagicMock()
        mock_pr.diffstat.return_value = {
            "values": [
                {"new": {"path": "src/main.py"}},
                {"new": {"path": "tests/test_main.py"}},
            ]
        }
        provider._mock_client.repositories.get.return_value.pullrequests.get.return_value = (
            mock_pr
        )

        files = provider.get_changed_files(123)

        assert files == ["src/main.py", "tests/test_main.py"]

    def test_post_issue_comment(self, provider):
        """Test post_issue_comment creates comment."""
        mock_pr = MagicMock()
        provider._mock_client.repositories.get.return_value.pullrequests.get.return_value = (
            mock_pr
        )

        provider.post_issue_comment(123, "Test comment")

        mock_pr.comment.assert_called_once_with("Test comment")

    def test_post_review_comment(self, provider):
        """Test post_review_comment creates inline comment."""
        mock_pr = MagicMock()
        provider._mock_client.repositories.get.return_value.pullrequests.get.return_value = (
            mock_pr
        )

        provider.post_review_comment(
            pr_number=123,
            body="Review comment",
            commit_sha="abc123",
            path="src/main.py",
            line=42,
        )

        mock_pr.comment.assert_called_once_with(
            "Review comment",
            inline={"path": "src/main.py", "to": 42},
        )

    def test_minimize_comment_returns_false(self, provider):
        """Test that minimize_comment returns False (unsupported)."""
        assert provider.minimize_comment("123") is False
