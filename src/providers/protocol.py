"""Git provider protocol and data classes."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class PullRequestInfo:
    """Information about a pull request."""

    number: int
    title: str
    head_sha: str
    base_sha: str
    author: str


@dataclass
class ReviewCommentInfo:
    """Information about a review comment."""

    id: str
    node_id: str | None
    path: str
    line: int | None
    body: str
    user: str


@dataclass
class IssueCommentInfo:
    """Information about an issue comment."""

    id: str
    body: str
    user: str


@runtime_checkable
class GitProvider(Protocol):
    """Protocol defining the interface for Git providers."""

    bot_username: str

    def get_pull_request(self, pr_number: int) -> PullRequestInfo:
        """Get pull request information."""
        ...

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the unified diff for a pull request."""
        ...

    def get_changed_files(self, pr_number: int) -> list[str]:
        """Get list of changed file paths in a PR."""
        ...

    def get_file_content(self, path: str, ref: str | None = None) -> str | None:
        """Get the content of a file from the repository."""
        ...

    def get_bot_review_comments(self, pr_number: int) -> list[ReviewCommentInfo]:
        """Fetch all review comments made by the bot."""
        ...

    def get_bot_issue_comments(self, pr_number: int) -> list[IssueCommentInfo]:
        """Fetch all issue comments made by the bot."""
        ...

    def post_issue_comment(self, pr_number: int, body: str) -> None:
        """Post a comment on a pull request."""
        ...

    def post_review_comment(
        self,
        pr_number: int,
        body: str,
        commit_sha: str,
        path: str,
        line: int,
    ) -> None:
        """Post an inline review comment on a specific line."""
        ...

    def edit_review_comment(self, comment_id: str, body: str) -> bool:
        """Edit an existing review comment."""
        ...

    def edit_issue_comment(self, comment_id: str, body: str) -> bool:
        """Edit an existing issue comment."""
        ...

    def delete_review_comment(self, comment_id: str) -> bool:
        """Delete a review comment."""
        ...

    def minimize_comment(self, comment_id: str) -> bool:
        """Minimize a comment. Returns False if unsupported."""
        ...
