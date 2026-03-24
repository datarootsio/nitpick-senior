"""Tests for the Azure DevOps provider."""

from unittest.mock import MagicMock, patch

import pytest

from src.providers import GitProvider


class TestAzureDevOpsProviderInit:
    """Tests for AzureDevOpsProvider initialization."""

    @patch("src.providers.azure_devops.Connection")
    @patch("src.providers.azure_devops.BasicAuthentication")
    def test_init_creates_client(self, mock_auth, mock_connection):
        """Test that initialization creates an Azure DevOps client."""
        mock_git_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.id = "repo-id"
        mock_git_client.get_repository.return_value = mock_repo
        mock_connection.return_value.clients.get_git_client.return_value = mock_git_client

        from src.providers.azure_devops import AzureDevOpsProvider

        provider = AzureDevOpsProvider(
            token="test-token",
            org_url="https://dev.azure.com/myorg",
            project="MyProject",
            repository="MyRepo",
        )

        mock_auth.assert_called_once_with("", "test-token")
        assert provider.repository_id == "repo-id"

    @patch("src.providers.azure_devops.Connection")
    @patch("src.providers.azure_devops.BasicAuthentication")
    def test_implements_protocol(self, mock_auth, mock_connection):
        """Test that AzureDevOpsProvider implements GitProvider protocol."""
        mock_git_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.id = "repo-id"
        mock_git_client.get_repository.return_value = mock_repo
        mock_connection.return_value.clients.get_git_client.return_value = mock_git_client

        from src.providers.azure_devops import AzureDevOpsProvider

        provider = AzureDevOpsProvider(
            token="test-token",
            org_url="https://dev.azure.com/myorg",
            project="MyProject",
            repository="MyRepo",
        )

        assert isinstance(provider, GitProvider)


class TestAzureDevOpsProviderMethods:
    """Tests for AzureDevOpsProvider methods."""

    @pytest.fixture
    def provider(self):
        """Create a mocked AzureDevOpsProvider."""
        with patch("src.providers.azure_devops.Connection") as mock_conn:
            with patch("src.providers.azure_devops.BasicAuthentication"):
                mock_git_client = MagicMock()
                mock_repo = MagicMock()
                mock_repo.id = "repo-id"
                mock_git_client.get_repository.return_value = mock_repo
                mock_conn.return_value.clients.get_git_client.return_value = mock_git_client

                from src.providers.azure_devops import AzureDevOpsProvider

                provider = AzureDevOpsProvider(
                    token="test-token",
                    org_url="https://dev.azure.com/myorg",
                    project="MyProject",
                    repository="MyRepo",
                )
                provider._mock_git_client = mock_git_client
                yield provider

    def test_get_pull_request(self, provider):
        """Test get_pull_request returns PullRequestInfo."""
        mock_pr = MagicMock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        mock_pr.last_merge_source_commit.commit_id = "abc123"
        mock_pr.last_merge_target_commit.commit_id = "def456"
        mock_pr.created_by.display_name = "Test User"
        provider._mock_git_client.get_pull_request.return_value = mock_pr

        pr_info = provider.get_pull_request(123)

        assert pr_info.number == 123
        assert pr_info.title == "Test PR"
        assert pr_info.head_sha == "abc123"
        assert pr_info.base_sha == "def456"
        assert pr_info.author == "Test User"

    def test_get_changed_files(self, provider):
        """Test get_changed_files returns file paths."""
        mock_iteration = MagicMock()
        mock_iteration.id = 1
        provider._mock_git_client.get_pull_request_iterations.return_value = [mock_iteration]

        mock_change1 = MagicMock()
        mock_change1.item.path = "/src/main.py"
        mock_change2 = MagicMock()
        mock_change2.item.path = "/tests/test_main.py"

        mock_changes = MagicMock()
        mock_changes.change_entries = [mock_change1, mock_change2]
        provider._mock_git_client.get_pull_request_iteration_changes.return_value = mock_changes

        files = provider.get_changed_files(123)

        assert files == ["src/main.py", "tests/test_main.py"]

    def test_minimize_comment_returns_false(self, provider):
        """Test that minimize_comment returns False (unsupported)."""
        assert provider.minimize_comment("123") is False
