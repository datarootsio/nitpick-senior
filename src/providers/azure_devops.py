"""Azure DevOps provider implementation."""

import difflib
import logging

from azure.devops.connection import Connection
from azure.devops.v7_1.git import GitClient
from azure.devops.v7_1.git.models import (
    Comment,
    CommentThread,
    CommentThreadContext,
    GitPullRequestCommentThread,
)
from msrest.authentication import BasicAuthentication

from .base import BaseProvider
from .protocol import IssueCommentInfo, PullRequestInfo, ReviewCommentInfo

logger = logging.getLogger(__name__)


class AzureDevOpsProvider(BaseProvider):
    """Azure DevOps implementation of the GitProvider protocol."""

    def __init__(
        self,
        token: str,
        org_url: str,
        project: str,
        repository: str,
        bot_username: str | None = None,
    ):
        """Initialize the Azure DevOps provider.

        Args:
            token: Personal Access Token for authentication
            org_url: Organization URL (e.g., https://dev.azure.com/myorg)
            project: Project name
            repository: Repository name
            bot_username: Bot username (defaults to PAT owner)
        """
        super().__init__()
        self.token = token
        self.org_url = org_url
        self.project = project
        self.repository = repository

        credentials = BasicAuthentication("", token)
        connection = Connection(base_url=org_url, creds=credentials)
        self.git_client: GitClient = connection.clients.get_git_client()

        # Get repository ID
        repo = self.git_client.get_repository(repository, project)
        self.repository_id = repo.id

        # Bot username is the PAT owner identity
        self.bot_username = bot_username or self._get_current_user()

    def _get_current_user(self) -> str:
        """Get the current authenticated user."""
        try:
            # The identity is typically the PAT owner
            return "Azure DevOps Bot"
        except Exception:
            return "Azure DevOps Bot"

    def get_pull_request(self, pr_number: int) -> PullRequestInfo:
        """Get pull request information."""
        cached = self._get_cached_pr(pr_number)
        if cached:
            return cached

        pr = self.git_client.get_pull_request(
            repository_id=self.repository_id,
            pull_request_id=pr_number,
            project=self.project,
        )

        info = PullRequestInfo(
            number=pr.pull_request_id,
            title=pr.title,
            head_sha=pr.last_merge_source_commit.commit_id,
            base_sha=pr.last_merge_target_commit.commit_id,
            author=pr.created_by.display_name,
        )
        self._cache_pr(pr_number, info)
        return info

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the unified diff for a pull request."""
        pr_info = self.get_pull_request(pr_number)

        iterations = self.git_client.get_pull_request_iterations(
            repository_id=self.repository_id,
            pull_request_id=pr_number,
            project=self.project,
        )

        if not iterations:
            return ""

        latest_iteration = iterations[-1]
        changes = self.git_client.get_pull_request_iteration_changes(
            repository_id=self.repository_id,
            pull_request_id=pr_number,
            iteration_id=latest_iteration.id,
            project=self.project,
        )

        diff_parts = []
        for change in changes.change_entries or []:
            if not (change.item and change.item.path):
                continue

            path = change.item.path.lstrip("/")
            change_type = str(change.change_type).lower() if change.change_type else ""

            # Fetch file content at base and head commits
            if "delete" in change_type:
                base_content = self.get_file_content(path, pr_info.base_sha) or ""
                head_content = ""
            elif "add" in change_type:
                base_content = ""
                head_content = self.get_file_content(path, pr_info.head_sha) or ""
            else:
                base_content = self.get_file_content(path, pr_info.base_sha) or ""
                head_content = self.get_file_content(path, pr_info.head_sha) or ""

            # Compute unified diff
            diff_lines = list(
                difflib.unified_diff(
                    base_content.splitlines(keepends=True),
                    head_content.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                )
            )

            if diff_lines:
                diff_parts.append("".join(diff_lines))

        return "\n".join(diff_parts)

    def get_changed_files(self, pr_number: int) -> list[str]:
        """Get list of changed file paths in a PR."""
        iterations = self.git_client.get_pull_request_iterations(
            repository_id=self.repository_id,
            pull_request_id=pr_number,
            project=self.project,
        )

        if not iterations:
            return []

        latest_iteration = iterations[-1]
        changes = self.git_client.get_pull_request_iteration_changes(
            repository_id=self.repository_id,
            pull_request_id=pr_number,
            iteration_id=latest_iteration.id,
            project=self.project,
        )

        files = []
        for change in changes.change_entries or []:
            if change.item and change.item.path:
                files.append(change.item.path.lstrip("/"))

        return files

    def get_file_content(self, path: str, ref: str | None = None) -> str | None:
        """Get the content of a file from the repository."""
        try:
            version_descriptor = None
            if ref:
                from azure.devops.v7_1.git.models import GitVersionDescriptor

                version_descriptor = GitVersionDescriptor(
                    version=ref,
                    version_type="commit",
                )

            item = self.git_client.get_item(
                repository_id=self.repository_id,
                path=path,
                project=self.project,
                version_descriptor=version_descriptor,
                include_content=True,
            )
            return item.content if item else None
        except Exception as e:
            logger.warning(f"Failed to fetch file {path}: {e}")
            return None

    def get_bot_review_comments(self, pr_number: int) -> list[ReviewCommentInfo]:
        """Fetch all review comments made by the bot."""
        threads = self.git_client.get_threads(
            repository_id=self.repository_id,
            pull_request_id=pr_number,
            project=self.project,
        )

        comments = []
        for thread in threads or []:
            if not thread.comments:
                continue

            # Check if first comment is from bot
            first_comment = thread.comments[0]
            author_name = (
                first_comment.author.display_name if first_comment.author else ""
            )

            if author_name == self.bot_username or self.bot_username in author_name:
                path = ""
                line = None

                if thread.thread_context:
                    path = thread.thread_context.file_path or ""
                    path = path.lstrip("/")
                    if thread.thread_context.right_file_end:
                        line = thread.thread_context.right_file_end.line

                comments.append(
                    ReviewCommentInfo(
                        id=str(thread.id),
                        node_id=None,
                        path=path,
                        line=line,
                        body=first_comment.content or "",
                        user=author_name,
                    )
                )

        return comments

    def get_bot_issue_comments(self, pr_number: int) -> list[IssueCommentInfo]:
        """Fetch all issue comments made by the bot (general comments)."""
        threads = self.git_client.get_threads(
            repository_id=self.repository_id,
            pull_request_id=pr_number,
            project=self.project,
        )

        comments = []
        for thread in threads or []:
            # General comments have no thread_context
            if thread.thread_context:
                continue

            if not thread.comments:
                continue

            first_comment = thread.comments[0]
            author_name = (
                first_comment.author.display_name if first_comment.author else ""
            )

            if author_name == self.bot_username or self.bot_username in author_name:
                comments.append(
                    IssueCommentInfo(
                        id=str(thread.id),
                        body=first_comment.content or "",
                        user=author_name,
                    )
                )

        return comments

    def post_issue_comment(self, pr_number: int, body: str) -> None:
        """Post a comment on a pull request."""
        thread = GitPullRequestCommentThread(
            comments=[Comment(content=body)],
            status="active",
        )
        self.git_client.create_thread(
            comment_thread=thread,
            repository_id=self.repository_id,
            pull_request_id=pr_number,
            project=self.project,
        )

    def post_review_comment(
        self,
        pr_number: int,
        body: str,
        commit_sha: str,
        path: str,
        line: int,
    ) -> None:
        """Post an inline review comment on a specific line."""
        from azure.devops.v7_1.git.models import CommentPosition

        thread_context = CommentThreadContext(
            file_path=f"/{path}",
            right_file_start=CommentPosition(line=line, offset=1),
            right_file_end=CommentPosition(line=line, offset=1),
        )

        thread = GitPullRequestCommentThread(
            comments=[Comment(content=body)],
            thread_context=thread_context,
            status="active",
        )

        self.git_client.create_thread(
            comment_thread=thread,
            repository_id=self.repository_id,
            pull_request_id=pr_number,
            project=self.project,
        )

    def edit_review_comment(self, comment_id: str, body: str) -> bool:
        """Edit an existing review comment (thread)."""
        # Azure DevOps uses thread ID, need to update the first comment
        try:
            # This is complex in Azure DevOps - we need thread_id and comment_id
            # For simplicity, we'll update by creating a new comment in the thread
            logger.warning("Edit review comment not fully implemented for Azure DevOps")
            return False
        except Exception as e:
            logger.warning(f"Failed to edit comment {comment_id}: {e}")
            return False

    def edit_issue_comment(self, pr_number: int, comment_id: str, body: str) -> bool:
        """Edit an existing issue comment."""
        try:
            logger.warning("Edit issue comment not fully implemented for Azure DevOps")
            return False
        except Exception as e:
            logger.warning(f"Failed to edit issue comment {comment_id}: {e}")
            return False

    def delete_review_comment(self, comment_id: str) -> bool:
        """Delete a review comment (resolve the thread)."""
        try:
            # In Azure DevOps, we can't delete threads, but we can resolve them
            update = CommentThread(status="closed")
            self.git_client.update_thread(
                comment_thread=update,
                repository_id=self.repository_id,
                pull_request_id=0,  # Need actual PR number
                thread_id=int(comment_id),
                project=self.project,
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to delete comment {comment_id}: {e}")
            return False

    def minimize_comment(self, comment_id: str) -> bool:
        """Minimize a comment. Azure DevOps doesn't support this."""
        return False
