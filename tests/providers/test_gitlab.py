"""Tests for the GitLab provider."""

from unittest.mock import MagicMock, patch

import pytest

from src.providers import GitProvider


class TestGitLabProviderInit:
    """Tests for GitLabProvider initialization."""

    @patch("src.providers.gitlab.gitlab.Gitlab")
    def test_init_creates_client(self, mock_gitlab):
        """Test that initialization creates a GitLab client."""
        mock_gl = MagicMock()
        mock_gl.user.username = "testbot"
        mock_project = MagicMock()
        mock_gl.projects.get.return_value = mock_project
        mock_gitlab.return_value = mock_gl

        from src.providers.gitlab import GitLabProvider

        provider = GitLabProvider(
            token="test-token",
            project_path="group/project",
        )

        mock_gitlab.assert_called_once_with("https://gitlab.com", private_token="test-token")
        assert provider.bot_username == "testbot"

    @patch("src.providers.gitlab.gitlab.Gitlab")
    def test_implements_protocol(self, mock_gitlab):
        """Test that GitLabProvider implements GitProvider protocol."""
        mock_gl = MagicMock()
        mock_gl.user.username = "testbot"
        mock_gitlab.return_value = mock_gl

        from src.providers.gitlab import GitLabProvider

        provider = GitLabProvider(
            token="test-token",
            project_path="group/project",
        )

        assert isinstance(provider, GitProvider)


class TestGitLabProviderMethods:
    """Tests for GitLabProvider methods."""

    @pytest.fixture
    def provider(self):
        """Create a mocked GitLabProvider."""
        with patch("src.providers.gitlab.gitlab.Gitlab") as mock_gitlab:
            mock_gl = MagicMock()
            mock_gl.user.username = "testbot"
            mock_project = MagicMock()
            mock_gl.projects.get.return_value = mock_project
            mock_gitlab.return_value = mock_gl

            from src.providers.gitlab import GitLabProvider

            provider = GitLabProvider(
                token="test-token",
                project_path="group/project",
            )
            provider._mock_project = mock_project
            provider._mock_gl = mock_gl
            yield provider

    def test_get_pull_request(self, provider):
        """Test get_pull_request returns PullRequestInfo."""
        mock_mr = MagicMock()
        mock_mr.iid = 123
        mock_mr.title = "Test MR"
        mock_mr.sha = "abc123"
        mock_mr.diff_refs = {"base_sha": "def456"}
        mock_mr.author = {"username": "testuser"}
        provider._mock_project.mergerequests.get.return_value = mock_mr

        pr_info = provider.get_pull_request(123)

        assert pr_info.number == 123
        assert pr_info.title == "Test MR"
        assert pr_info.head_sha == "abc123"
        assert pr_info.base_sha == "def456"
        assert pr_info.author == "testuser"

    def test_get_changed_files(self, provider):
        """Test get_changed_files returns file paths."""
        mock_mr = MagicMock()
        mock_mr.changes.return_value = {
            "changes": [
                {"new_path": "src/main.py"},
                {"new_path": "tests/test_main.py"},
            ]
        }
        provider._mock_project.mergerequests.get.return_value = mock_mr

        files = provider.get_changed_files(123)

        assert files == ["src/main.py", "tests/test_main.py"]

    def test_get_file_content_success(self, provider):
        """Test get_file_content returns content."""
        mock_file = MagicMock()
        mock_file.decode.return_value = b"print('hello')"
        provider._mock_project.files.get.return_value = mock_file
        provider._mock_project.default_branch = "main"

        content = provider.get_file_content("src/main.py")

        assert content == "print('hello')"

    def test_post_issue_comment(self, provider):
        """Test post_issue_comment creates note."""
        mock_mr = MagicMock()
        provider._mock_project.mergerequests.get.return_value = mock_mr

        provider.post_issue_comment(123, "Test comment")

        mock_mr.notes.create.assert_called_once_with({"body": "Test comment"})

    def test_minimize_comment_returns_false(self, provider):
        """Test that minimize_comment returns False (unsupported)."""
        assert provider.minimize_comment("123") is False
