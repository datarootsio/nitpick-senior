"""GitHub API client wrapper."""

import logging

import requests
from github.PullRequest import PullRequest
from github.PullRequestComment import PullRequestComment
from github.Repository import Repository

from github import Github

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubClient:
    """Wrapper around PyGithub for PR operations."""

    def __init__(self, token: str, repo_owner: str, repo_name: str):
        """Initialize the GitHub client.

        Args:
            token: GitHub token for authentication
            repo_owner: Repository owner (user or org)
            repo_name: Repository name
        """
        self.token = token
        self.gh = Github(token)
        self.repo: Repository = self.gh.get_repo(f"{repo_owner}/{repo_name}")

    def get_pull_request(self, pr_number: int) -> PullRequest:
        """Get a pull request by number."""
        return self.repo.get_pull(pr_number)

    def get_bot_comments(self, pr_number: int) -> list[PullRequestComment]:
        """Fetch all review comments made by github-actions[bot]."""
        pr = self.get_pull_request(pr_number)
        return [c for c in pr.get_review_comments() if c.user.login == "github-actions[bot]"]

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the unified diff for a pull request."""
        pr = self.get_pull_request(pr_number)
        # Get diff via the compare API
        comparison = self.repo.compare(pr.base.sha, pr.head.sha)

        # Build unified diff from files
        diff_parts = []
        for file in comparison.files:
            if file.patch:
                diff_parts.append(f"diff --git a/{file.filename} b/{file.filename}")
                diff_parts.append(f"--- a/{file.filename}")
                diff_parts.append(f"+++ b/{file.filename}")
                diff_parts.append(file.patch)
                diff_parts.append("")

        return "\n".join(diff_parts)

    def post_comment(self, pr_number: int, body: str) -> None:
        """Post a comment on a pull request."""
        pr = self.get_pull_request(pr_number)
        pr.create_issue_comment(body)

    def post_review_comment(
        self,
        pr_number: int,
        body: str,
        commit_sha: str,
        path: str,
        line: int,
    ) -> None:
        """Post an inline review comment on a specific line.

        Args:
            pr_number: Pull request number
            body: Comment body
            commit_sha: The commit SHA to comment on
            path: File path relative to repo root
            line: Line number in the file
        """
        pr = self.get_pull_request(pr_number)
        pr.create_review_comment(
            body=body,
            commit=self.repo.get_commit(commit_sha),
            path=path,
            line=line,
        )

    def create_review(
        self,
        pr_number: int,
        body: str,
        comments: list[dict],
        event: str = "COMMENT",
    ) -> None:
        """Create a pull request review with multiple comments.

        Args:
            pr_number: Pull request number
            body: Review summary body
            comments: List of comment dicts with path, line, body
            event: Review event type (COMMENT, APPROVE, REQUEST_CHANGES)
        """
        pr = self.get_pull_request(pr_number)
        pr.create_review(
            body=body,
            event=event,
            comments=comments,
        )

    def _minimize_comment(self, node_id: str) -> bool:
        """Minimize a comment using GitHub's GraphQL API.

        Args:
            node_id: The GraphQL node ID of the comment

        Returns:
            True if successful, False otherwise
        """
        query = """
        mutation MinimizeComment($id: ID!) {
            minimizeComment(input: {subjectId: $id, classifier: OUTDATED}) {
                minimizedComment {
                    isMinimized
                }
            }
        }
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                GRAPHQL_URL,
                json={"query": query, "variables": {"id": node_id}},
                headers=headers,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            logger.warning(f"GraphQL request failed: {e}")
            return False

        if response.status_code != 200:
            logger.warning(f"GraphQL request failed: {response.status_code}")
            return False

        data = response.json()
        if "errors" in data:
            logger.warning(f"GraphQL errors: {data['errors']}")
            return False

        return True

    def resolve_outdated_comments(self, pr_number: int) -> int:
        """Minimize outdated review comments from previous bot runs.

        Uses GitHub's GraphQL API to collapse outdated comments.

        Returns the number of comments resolved.
        """
        pr = self.get_pull_request(pr_number)
        resolved_count = 0

        for comment in pr.get_review_comments():
            # Check if this is our bot's comment and on outdated diff
            # Comments are made by github-actions[bot], outdated when line is None
            is_bot_comment = comment.user.login == "github-actions[bot]"
            is_outdated = comment.line is None
            if is_bot_comment and is_outdated and self._minimize_comment(comment.node_id):
                resolved_count += 1
                logger.info(f"Minimized outdated comment on {comment.path}")

        return resolved_count
