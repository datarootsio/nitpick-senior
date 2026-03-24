"""Bitbucket provider implementation."""

import logging

from atlassian.bitbucket import Cloud as BitbucketCloud

from .base import BaseProvider
from .protocol import IssueCommentInfo, PullRequestInfo, ReviewCommentInfo

logger = logging.getLogger(__name__)


class BitbucketProvider(BaseProvider):
    """Bitbucket Cloud implementation of the GitProvider protocol."""

    def __init__(
        self,
        username: str,
        app_password: str,
        workspace: str,
        repo_slug: str,
        bot_username: str | None = None,
    ):
        """Initialize the Bitbucket provider.

        Args:
            username: Bitbucket username
            app_password: Bitbucket app password
            workspace: Workspace ID
            repo_slug: Repository slug
            bot_username: Bot username (defaults to auth username)
        """
        super().__init__()
        self.username = username
        self.workspace = workspace
        self.repo_slug = repo_slug

        self.bitbucket = BitbucketCloud(username=username, password=app_password)
        self.bot_username = bot_username or username
        # Cache repository object to avoid repeated API calls
        self.repo = self.bitbucket.repositories.get(workspace, repo_slug)

    def get_pull_request(self, pr_number: int) -> PullRequestInfo:
        """Get pull request information."""
        cached = self._get_cached_pr(pr_number)
        if cached:
            return cached

        pr = self.repo.pullrequests.get(pr_number)

        data = pr.data

        info = PullRequestInfo(
            number=data["id"],
            title=data["title"],
            head_sha=data["source"]["commit"]["hash"],
            base_sha=data["destination"]["commit"]["hash"],
            author=data["author"]["nickname"],
        )
        self._cache_pr(pr_number, info)
        return info

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the unified diff for a pull request."""
        pr = self.repo.pullrequests.get(pr_number)

        # Get diff
        diff_response = pr.diff()
        if isinstance(diff_response, bytes):
            return diff_response.decode("utf-8")
        return str(diff_response) if diff_response else ""

    def get_changed_files(self, pr_number: int) -> list[str]:
        """Get list of changed file paths in a PR."""
        pr = self.repo.pullrequests.get(pr_number)

        # Get diffstat for file list
        diffstat = pr.diffstat()
        files = []
        for entry in diffstat.get("values", []):
            new_path = entry.get("new", {}).get("path")
            if new_path:
                files.append(new_path)
            else:
                old_path = entry.get("old", {}).get("path")
                if old_path:
                    files.append(old_path)

        return files

    def get_file_content(self, path: str, ref: str | None = None) -> str | None:
        """Get the content of a file from the repository."""
        try:
            # Use the main branch if no ref specified
            ref = ref or "main"
            content = self.repo.get(f"src/{ref}/{path}")
            if isinstance(content, bytes):
                return content.decode("utf-8")
            return str(content) if content else None
        except Exception as e:
            logger.warning(f"Failed to fetch file {path}: {e}")
            return None

    def get_bot_review_comments(self, pr_number: int) -> list[ReviewCommentInfo]:
        """Fetch all inline comments made by the bot."""
        pr = self.repo.pullrequests.get(pr_number)

        comments_data = pr.comments()
        comments = []

        for comment in comments_data.get("values", []):
            user = comment.get("user", {})
            username = user.get("nickname", "")

            if username != self.bot_username:
                continue

            # Check if it's an inline comment
            inline = comment.get("inline")
            if not inline:
                continue

            path = inline.get("path", "")
            line = inline.get("to")  # 'to' is the new line number

            comments.append(
                ReviewCommentInfo(
                    id=str(comment["id"]),
                    node_id=None,
                    path=path,
                    line=line,
                    body=comment.get("content", {}).get("raw", ""),
                    user=username,
                )
            )

        return comments

    def get_bot_issue_comments(self, pr_number: int) -> list[IssueCommentInfo]:
        """Fetch all general comments made by the bot."""
        pr = self.repo.pullrequests.get(pr_number)

        comments_data = pr.comments()
        comments = []

        for comment in comments_data.get("values", []):
            user = comment.get("user", {})
            username = user.get("nickname", "")

            if username != self.bot_username:
                continue

            # Skip inline comments
            if comment.get("inline"):
                continue

            comments.append(
                IssueCommentInfo(
                    id=str(comment["id"]),
                    body=comment.get("content", {}).get("raw", ""),
                    user=username,
                )
            )

        return comments

    def post_issue_comment(self, pr_number: int, body: str) -> None:
        """Post a comment on a pull request."""
        pr = self.repo.pullrequests.get(pr_number)

        pr.comment(body)

    def post_review_comment(
        self,
        pr_number: int,
        body: str,
        commit_sha: str,
        path: str,
        line: int,
    ) -> None:
        """Post an inline review comment on a specific line."""
        pr = self.repo.pullrequests.get(pr_number)

        # Bitbucket inline comments
        pr.comment(
            body,
            inline={
                "path": path,
                "to": line,
            },
        )

    def edit_review_comment(self, comment_id: str, body: str) -> bool:
        """Edit an existing review comment."""
        try:
            # Bitbucket API for editing comments is complex
            logger.warning("Edit review comment not fully implemented for Bitbucket")
            return False
        except Exception as e:
            logger.warning(f"Failed to edit comment {comment_id}: {e}")
            return False

    def edit_issue_comment(self, comment_id: str, body: str) -> bool:
        """Edit an existing issue comment."""
        try:
            logger.warning("Edit issue comment not fully implemented for Bitbucket")
            return False
        except Exception as e:
            logger.warning(f"Failed to edit issue comment {comment_id}: {e}")
            return False

    def delete_review_comment(self, comment_id: str) -> bool:
        """Delete a review comment."""
        try:
            # Would need PR number context
            logger.warning("Delete review comment requires PR context in Bitbucket")
            return False
        except Exception as e:
            logger.warning(f"Failed to delete comment {comment_id}: {e}")
            return False

    def minimize_comment(self, comment_id: str) -> bool:
        """Minimize a comment. Bitbucket doesn't support this."""
        return False
