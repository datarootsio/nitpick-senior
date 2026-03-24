"""Tests for the provider factory."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.providers import ProviderType, create_provider, detect_provider


class TestDetectProvider:
    """Tests for detect_provider function."""

    def test_detects_azure_devops_from_org(self):
        """Test detection of Azure DevOps from AZURE_DEVOPS_ORG."""
        with patch.dict(os.environ, {"AZURE_DEVOPS_ORG": "https://dev.azure.com/myorg"}):
            provider = detect_provider()
            assert provider == ProviderType.AZURE_DEVOPS

    def test_detects_azure_devops_from_system_project(self):
        """Test detection of Azure DevOps from SYSTEM_TEAMPROJECT."""
        with patch.dict(os.environ, {"SYSTEM_TEAMPROJECT": "MyProject"}, clear=True):
            provider = detect_provider()
            assert provider == ProviderType.AZURE_DEVOPS

    def test_detects_gitlab_from_ci_server(self):
        """Test detection of GitLab from CI_SERVER_URL."""
        with patch.dict(os.environ, {"CI_SERVER_URL": "https://gitlab.com"}, clear=True):
            provider = detect_provider()
            assert provider == ProviderType.GITLAB

    def test_detects_gitlab_from_gitlab_url(self):
        """Test detection of GitLab from GITLAB_URL."""
        with patch.dict(os.environ, {"GITLAB_URL": "https://gitlab.mycompany.com"}, clear=True):
            provider = detect_provider()
            assert provider == ProviderType.GITLAB

    def test_detects_bitbucket_from_workspace(self):
        """Test detection of Bitbucket from BITBUCKET_WORKSPACE."""
        with patch.dict(os.environ, {"BITBUCKET_WORKSPACE": "myworkspace"}, clear=True):
            provider = detect_provider()
            assert provider == ProviderType.BITBUCKET

    def test_defaults_to_github(self):
        """Test default to GitHub when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            provider = detect_provider()
            assert provider == ProviderType.GITHUB


class TestCreateProvider:
    """Tests for create_provider function."""

    @patch("src.providers.github.Github")
    def test_creates_github_provider(self, mock_github):
        """Test creating a GitHub provider."""
        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo

        with patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "test-token", "GITHUB_REPOSITORY": "owner/repo"},
        ):
            provider = create_provider(provider_type=ProviderType.GITHUB)

            mock_github.assert_called_once_with("test-token")
            mock_github.return_value.get_repo.assert_called_once_with("owner/repo")

    @patch("src.providers.github.Github")
    def test_creates_github_with_explicit_params(self, mock_github):
        """Test creating GitHub provider with explicit parameters."""
        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo

        provider = create_provider(
            provider_type=ProviderType.GITHUB,
            token="explicit-token",
            repo_owner="explicit-owner",
            repo_name="explicit-repo",
        )

        mock_github.assert_called_once_with("explicit-token")

    def test_raises_without_token(self):
        """Test that ValueError is raised without a token."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Authentication token is required"):
                create_provider(provider_type=ProviderType.GITHUB)

    def test_raises_github_without_repo(self):
        """Test that ValueError is raised without repo info for GitHub."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=True):
            with pytest.raises(ValueError, match="GitHub requires repo_owner"):
                create_provider(provider_type=ProviderType.GITHUB)

    @patch("src.providers.azure_devops.Connection")
    @patch("src.providers.azure_devops.BasicAuthentication")
    def test_creates_azure_devops_provider(self, mock_auth, mock_connection):
        """Test creating an Azure DevOps provider."""
        mock_git_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.id = "repo-id"
        mock_git_client.get_repository.return_value = mock_repo
        mock_connection.return_value.clients.get_git_client.return_value = mock_git_client

        provider = create_provider(
            provider_type=ProviderType.AZURE_DEVOPS,
            token="test-token",
            azure_org_url="https://dev.azure.com/myorg",
            azure_project="MyProject",
            azure_repository="MyRepo",
        )

        mock_auth.assert_called_once_with("", "test-token")

    @patch("src.providers.gitlab.gitlab.Gitlab")
    def test_creates_gitlab_provider(self, mock_gitlab):
        """Test creating a GitLab provider."""
        mock_gl = MagicMock()
        mock_gl.user.username = "testbot"
        mock_project = MagicMock()
        mock_gl.projects.get.return_value = mock_project
        mock_gitlab.return_value = mock_gl

        provider = create_provider(
            provider_type=ProviderType.GITLAB,
            token="test-token",
            gitlab_project="group/project",
        )

        mock_gitlab.assert_called_once_with("https://gitlab.com", private_token="test-token")

    @patch("src.providers.bitbucket.BitbucketCloud")
    def test_creates_bitbucket_provider(self, mock_bitbucket):
        """Test creating a Bitbucket provider."""
        provider = create_provider(
            provider_type=ProviderType.BITBUCKET,
            token="app-password",
            bitbucket_workspace="myworkspace",
            bitbucket_repo_slug="myrepo",
            bitbucket_username="myuser",
        )

        mock_bitbucket.assert_called_once_with(username="myuser", password="app-password")

    @patch("src.providers.github.Github")
    def test_accepts_string_provider_type(self, mock_github):
        """Test that string provider type is accepted."""
        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo

        provider = create_provider(
            provider_type="github",
            token="test-token",
            repo_owner="owner",
            repo_name="repo",
        )

        mock_github.assert_called_once()

    @patch("src.providers.github.Github")
    def test_auto_detects_provider(self, mock_github):
        """Test auto-detection when provider_type is None."""
        mock_repo = MagicMock()
        mock_github.return_value.get_repo.return_value = mock_repo

        with patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "test-token", "GITHUB_REPOSITORY": "owner/repo"},
            clear=True,
        ):
            provider = create_provider(
                provider_type=None,
                token="test-token",
                repo_owner="owner",
                repo_name="repo",
            )

            mock_github.assert_called_once()
