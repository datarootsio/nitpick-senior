"""GitHub API client wrapper - backward compatibility layer.

This module provides backward compatibility with code that imports GitHubClient
from src.github.client. New code should use src.providers.GitHubProvider instead.
"""

import logging
import warnings

from src.providers.github import GitHubProvider
from src.providers.protocol import IssueCommentInfo, PullRequestInfo, ReviewCommentInfo

logger = logging.getLogger(__name__)

# Re-export constants for backward compatibility
BOT_USERNAME = "github-actions[bot]"
GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubClient(GitHubProvider):
    """Backward compatible wrapper around GitHubProvider.

    Deprecated: Use src.providers.GitHubProvider instead.
    """

    def __init__(self, token: str, repo_owner: str, repo_name: str):
        """Initialize the GitHub client.

        Args:
            token: GitHub token for authentication
            repo_owner: Repository owner (user or org)
            repo_name: Repository name
        """
        warnings.warn(
            "GitHubClient is deprecated. Use src.providers.GitHubProvider instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(token=token, repo_owner=repo_owner, repo_name=repo_name)

    # Backward compatible method names

    def get_bot_comments(self, pr_number: int) -> list[ReviewCommentInfo]:
        """Backward compatible alias for get_bot_review_comments."""
        return self.get_bot_review_comments(pr_number)

    def post_comment(self, pr_number: int, body: str) -> None:
        """Backward compatible alias for post_issue_comment."""
        self.post_issue_comment(pr_number, body)


__all__ = [
    "GitHubClient",
    "BOT_USERNAME",
    "GRAPHQL_URL",
    "PullRequestInfo",
    "ReviewCommentInfo",
    "IssueCommentInfo",
]
