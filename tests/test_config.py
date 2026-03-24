"""Tests for configuration loading."""

import pytest

from src.config import Config


class TestConfigFromEnv:
    def test_valid_config(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "123")

        config = Config.from_env()

        assert config.github_token == "test-token"
        assert config.model == "gpt-4o"
        assert config.repo_owner == "owner"
        assert config.repo_name == "repo"
        assert config.pr_number == 123

    def test_defaults(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "1")

        config = Config.from_env()

        assert config.agent_spec_path == ".github/ai-reviewer.md"
        assert config.post_summary is True
        assert config.post_inline_comments is True
        assert config.max_comments == 10
        assert config.min_severity == "warning"
        assert config.context_enabled is True
        assert config.context_max_tokens == 5000

    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.delenv("INPUT_GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("INPUT_TOKEN", raising=False)
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "1")

        with pytest.raises(ValueError, match="Authentication token is required"):
            Config.from_env()

    def test_missing_model_raises(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.delenv("INPUT_MODEL", raising=False)
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "1")

        with pytest.raises(ValueError, match="Model is required"):
            Config.from_env()

    def test_invalid_repository_format_raises(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "invalid-format")
        monkeypatch.setenv("PR_NUMBER", "1")

        with pytest.raises(ValueError, match="GITHUB_REPOSITORY must be in format"):
            Config.from_env()

    def test_pr_number_from_github_ref(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.delenv("PR_NUMBER", raising=False)
        monkeypatch.setenv("GITHUB_REF", "refs/pull/456/merge")

        config = Config.from_env()
        assert config.pr_number == 456

    def test_invalid_pr_number_raises(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "not-a-number")

        with pytest.raises(ValueError, match="Invalid PR number format"):
            Config.from_env()

    def test_invalid_severity_defaults_to_warning(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "1")
        monkeypatch.setenv("INPUT_MIN_SEVERITY", "invalid")

        config = Config.from_env()
        assert config.min_severity == "warning"

    def test_bool_parsing(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "1")
        monkeypatch.setenv("INPUT_POST_SUMMARY", "false")
        monkeypatch.setenv("INPUT_POST_INLINE_COMMENTS", "FALSE")
        monkeypatch.setenv("INPUT_CONTEXT_ENABLED", "False")

        config = Config.from_env()
        assert config.post_summary is False
        assert config.post_inline_comments is False
        assert config.context_enabled is False

    def test_context_max_tokens_invalid_defaults(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "1")
        monkeypatch.setenv("INPUT_CONTEXT_MAX_TOKENS", "not-a-number")

        config = Config.from_env()
        assert config.context_max_tokens == 5000

    def test_max_comments_invalid_defaults(self, monkeypatch):
        monkeypatch.setenv("INPUT_GITHUB_TOKEN", "test-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "1")
        monkeypatch.setenv("INPUT_MAX_COMMENTS", "not-a-number")

        config = Config.from_env()
        assert config.max_comments == 10

    def test_fallback_to_github_token(self, monkeypatch):
        monkeypatch.delenv("INPUT_GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "fallback-token")
        monkeypatch.setenv("INPUT_MODEL", "gpt-4o")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "1")

        config = Config.from_env()
        assert config.github_token == "fallback-token"
