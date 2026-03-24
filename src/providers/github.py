"""GitHub provider implementation."""

import logging

import requests
from github.Repository import Repository

from github import Github
from src.providers.base import BaseProvider
from src.providers.protocol import IssueCommentInfo, PullRequestInfo, ReviewCommentInfo

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.github.com"
BOT_USERNAME = "github-actions[bot]"


def _graphql_url(api_url: str) -> str:
    """Get the GraphQL endpoint for a GitHub API URL."""
    return f"{api_url}/graphql"


class GitHubProvider(BaseProvider):
    """GitHub implementation of the GitProvider protocol."""

    bot_username: str = BOT_USERNAME

    def __init__(self, token: str, repo_owner: str, repo_name: str, base_url: str | None = None):
        """Initialize the GitHub provider.

        Args:
            token: GitHub token for authentication
            repo_owner: Repository owner (user or org)
            repo_name: Repository name
            base_url: GitHub API base URL (for GitHub Enterprise)
        """
        super().__init__()
        self.token = token
        self.api_url = base_url or DEFAULT_API_URL
        self.gh = Github(token, base_url=self.api_url) if base_url else Github(token)
        self.repo: Repository = self.gh.get_repo(f"{repo_owner}/{repo_name}")

    def get_pull_request(self, pr_number: int) -> PullRequestInfo:
        """Get pull request information."""
        cached = self._get_cached_pr(pr_number)
        if cached:
            return cached

        pr = self.repo.get_pull(pr_number)
        info = PullRequestInfo(
            number=pr.number,
            title=pr.title,
            head_sha=pr.head.sha,
            base_sha=pr.base.sha,
            author=pr.user.login,
        )
        self._cache_pr(pr_number, info)
        return info

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the unified diff for a pull request."""
        pr = self.repo.get_pull(pr_number)
        comparison = self.repo.compare(pr.base.sha, pr.head.sha)

        diff_parts = []
        for file in comparison.files:
            if file.patch:
                diff_parts.append(f"diff --git a/{file.filename} b/{file.filename}")
                diff_parts.append(f"--- a/{file.filename}")
                diff_parts.append(f"+++ b/{file.filename}")
                diff_parts.append(file.patch)
                diff_parts.append("")

        return "\n".join(diff_parts)

    def get_changed_files(self, pr_number: int) -> list[str]:
        """Get list of changed file paths in a PR."""
        pr = self.repo.get_pull(pr_number)
        return [f.filename for f in pr.get_files()]

    def get_file_content(self, path: str, ref: str | None = None) -> str | None:
        """Get the content of a file from the repository."""
        try:
            if ref:
                contents = self.repo.get_contents(path, ref=ref)
            else:
                contents = self.repo.get_contents(path)

            if isinstance(contents, list):
                return None

            return contents.decoded_content.decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to fetch file {path}: {e}")
            return None

    def get_bot_review_comments(self, pr_number: int) -> list[ReviewCommentInfo]:
        """Fetch all review comments made by the bot."""
        pr = self.repo.get_pull(pr_number)
        comments = []
        for c in pr.get_review_comments():
            if c.user.login == self.bot_username:
                comments.append(
                    ReviewCommentInfo(
                        id=str(c.id),
                        node_id=c.node_id,
                        path=c.path,
                        line=c.line,
                        body=c.body,
                        user=c.user.login,
                    )
                )
        return comments

    def get_bot_issue_comments(self, pr_number: int) -> list[IssueCommentInfo]:
        """Fetch all issue comments made by the bot."""
        pr = self.repo.get_pull(pr_number)
        comments = []
        for c in pr.get_issue_comments():
            if c.user.login == self.bot_username:
                comments.append(
                    IssueCommentInfo(
                        id=str(c.id),
                        body=c.body,
                        user=c.user.login,
                    )
                )
        return comments

    def post_issue_comment(self, pr_number: int, body: str) -> None:
        """Post a comment on a pull request."""
        pr = self.repo.get_pull(pr_number)
        pr.create_issue_comment(body)

    def post_review_comment(
        self,
        pr_number: int,
        body: str,
        commit_sha: str,
        path: str,
        line: int,
    ) -> None:
        """Post an inline review comment on a specific line."""
        pr = self.repo.get_pull(pr_number)
        pr.create_review_comment(
            body=body,
            commit=self.repo.get_commit(commit_sha),
            path=path,
            line=line,
        )

    def edit_review_comment(self, comment_id: str, body: str) -> bool:
        """Edit an existing review comment using direct REST API."""
        url = f"{self.api_url}/repos/{self.repo.full_name}/pulls/comments/{comment_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            response = requests.patch(
                url,
                json={"body": body},
                headers=headers,
                timeout=30,
            )
            if response.status_code == 200:
                return True
            logger.warning(
                f"Failed to edit review comment {comment_id}: {response.status_code}"
            )
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to edit review comment {comment_id}: {e}")
            return False

    def edit_issue_comment(self, pr_number: int, comment_id: str, body: str) -> bool:
        """Edit an existing issue comment using direct REST API.

        Uses PATCH /repos/{owner}/{repo}/issues/comments/{comment_id} directly
        to avoid permission issues with the Issues API that PyGithub uses.
        """
        url = f"{self.api_url}/repos/{self.repo.full_name}/issues/comments/{comment_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            response = requests.patch(
                url,
                json={"body": body},
                headers=headers,
                timeout=30,
            )
            if response.status_code == 200:
                return True
            logger.warning(
                f"Failed to edit issue comment {comment_id}: {response.status_code}"
            )
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to edit issue comment {comment_id}: {e}")
            return False

    def delete_review_comment(self, comment_id: str) -> bool:
        """Delete a review comment using direct REST API."""
        url = f"{self.api_url}/repos/{self.repo.full_name}/pulls/comments/{comment_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            response = requests.delete(url, headers=headers, timeout=30)
            if response.status_code == 204:
                return True
            logger.warning(
                f"Failed to delete comment {comment_id}: {response.status_code}"
            )
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to delete comment {comment_id}: {e}")
            return False

    def minimize_comment(self, comment_id: str) -> bool:
        """Minimize a comment using GitHub's GraphQL API."""
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
                _graphql_url(self.api_url),
                json={"query": query, "variables": {"id": comment_id}},
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
