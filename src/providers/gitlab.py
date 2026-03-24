"""GitLab provider implementation."""

import logging

import gitlab
from gitlab.v4.objects import Project, ProjectMergeRequest

from .base import BaseProvider
from .protocol import IssueCommentInfo, PullRequestInfo, ReviewCommentInfo

logger = logging.getLogger(__name__)

DEFAULT_GITLAB_URL = "https://gitlab.com"


class GitLabProvider(BaseProvider):
    """GitLab implementation of the GitProvider protocol."""

    def __init__(
        self,
        token: str,
        project_path: str,
        gitlab_url: str = DEFAULT_GITLAB_URL,
        bot_username: str | None = None,
    ):
        """Initialize the GitLab provider.

        Args:
            token: GitLab personal access token
            project_path: Project path (e.g., "group/project")
            gitlab_url: GitLab instance URL
            bot_username: Bot username (defaults to token owner)
        """
        super().__init__()
        self.token = token
        self.gitlab_url = gitlab_url

        self.gl = gitlab.Gitlab(gitlab_url, private_token=token)
        self.gl.auth()

        self.project: Project = self.gl.projects.get(project_path)
        self.bot_username = bot_username or self.gl.user.username

    def get_pull_request(self, pr_number: int) -> PullRequestInfo:
        """Get merge request information."""
        cached = self._get_cached_pr(pr_number)
        if cached:
            return cached

        mr: ProjectMergeRequest = self.project.mergerequests.get(pr_number)

        info = PullRequestInfo(
            number=mr.iid,
            title=mr.title,
            head_sha=mr.sha,
            base_sha=mr.diff_refs["base_sha"],
            author=mr.author["username"],
        )
        self._cache_pr(pr_number, info)
        return info

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the unified diff for a merge request."""
        mr = self.project.mergerequests.get(pr_number)
        changes = mr.changes()

        diff_parts = []
        for change in changes.get("changes", []):
            old_path = change.get("old_path", "")
            new_path = change.get("new_path", "")
            diff = change.get("diff", "")

            diff_parts.append(f"diff --git a/{old_path} b/{new_path}")
            diff_parts.append(f"--- a/{old_path}")
            diff_parts.append(f"+++ b/{new_path}")
            diff_parts.append(diff)
            diff_parts.append("")

        return "\n".join(diff_parts)

    def get_changed_files(self, pr_number: int) -> list[str]:
        """Get list of changed file paths in a MR."""
        mr = self.project.mergerequests.get(pr_number)
        changes = mr.changes()

        files = []
        for change in changes.get("changes", []):
            new_path = change.get("new_path")
            if new_path:
                files.append(new_path)

        return files

    def get_file_content(self, path: str, ref: str | None = None) -> str | None:
        """Get the content of a file from the repository."""
        try:
            ref = ref or self.project.default_branch
            file = self.project.files.get(file_path=path, ref=ref)
            return file.decode().decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to fetch file {path}: {e}")
            return None

    def get_bot_review_comments(self, pr_number: int) -> list[ReviewCommentInfo]:
        """Fetch all review comments (discussions) made by the bot."""
        mr = self.project.mergerequests.get(pr_number)
        discussions = mr.discussions.list(all=True)

        comments = []
        for discussion in discussions:
            notes = discussion.attributes.get("notes", [])
            if not notes:
                continue

            first_note = notes[0]
            author = first_note.get("author", {})
            username = author.get("username", "")

            if username != self.bot_username:
                continue

            # Check if it's a diff note (has position)
            position = first_note.get("position")
            if not position:
                continue

            path = position.get("new_path", "")
            line = position.get("new_line")

            comments.append(
                ReviewCommentInfo(
                    id=str(discussion.id),
                    node_id=str(first_note.get("id")),
                    path=path,
                    line=line,
                    body=first_note.get("body", ""),
                    user=username,
                )
            )

        return comments

    def get_bot_issue_comments(self, pr_number: int) -> list[IssueCommentInfo]:
        """Fetch all general comments (notes) made by the bot."""
        mr = self.project.mergerequests.get(pr_number)
        notes = mr.notes.list(all=True)

        comments = []
        for note in notes:
            author = note.author
            username = author.get("username", "") if isinstance(author, dict) else ""

            if username != self.bot_username:
                continue

            # Skip system notes and diff notes
            if note.system or hasattr(note, "position"):
                continue

            comments.append(
                IssueCommentInfo(
                    id=str(note.id),
                    body=note.body,
                    user=username,
                )
            )

        return comments

    def post_issue_comment(self, pr_number: int, body: str) -> None:
        """Post a comment on a merge request."""
        mr = self.project.mergerequests.get(pr_number)
        mr.notes.create({"body": body})

    def post_review_comment(
        self,
        pr_number: int,
        body: str,
        commit_sha: str,
        path: str,
        line: int,
    ) -> None:
        """Post an inline review comment (diff note) on a specific line."""
        mr = self.project.mergerequests.get(pr_number)
        diff_refs = mr.diff_refs

        mr.discussions.create(
            {
                "body": body,
                "position": {
                    "base_sha": diff_refs["base_sha"],
                    "start_sha": diff_refs["start_sha"],
                    "head_sha": diff_refs["head_sha"],
                    "position_type": "text",
                    "new_path": path,
                    "new_line": line,
                },
            }
        )

    def edit_review_comment(self, comment_id: str, body: str) -> bool:
        """Edit an existing review comment (discussion note)."""
        try:
            # comment_id here is the discussion ID
            # We need to get the first note and edit it
            # This requires the MR context which we don't have here
            logger.warning("Edit review comment requires MR context in GitLab")
            return False
        except Exception as e:
            logger.warning(f"Failed to edit comment {comment_id}: {e}")
            return False

    def edit_issue_comment(self, pr_number: int, comment_id: str, body: str) -> bool:
        """Edit an existing issue comment (note)."""
        try:
            mr = self.project.mergerequests.get(pr_number)
            note = mr.notes.get(int(comment_id))
            note.body = body
            note.save()
            return True
        except Exception as e:
            logger.warning(f"Failed to edit issue comment {comment_id}: {e}")
            return False

    def delete_review_comment(self, comment_id: str) -> bool:
        """Delete a review comment."""
        try:
            # Need MR context
            logger.warning("Delete review comment requires MR context in GitLab")
            return False
        except Exception as e:
            logger.warning(f"Failed to delete comment {comment_id}: {e}")
            return False

    def minimize_comment(self, comment_id: str) -> bool:
        """Minimize a comment. GitLab doesn't support this."""
        return False
