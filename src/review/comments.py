"""Comment posting utilities."""

import logging
from typing import TYPE_CHECKING

from src.context.models import StaticAnalysisFinding
from src.llm.response import ReviewComment, ReviewResponse
from src.providers import ReviewCommentInfo
from src.review.formatters import (
    BOT_NAME,
    BOT_SIGNATURE,
    SEVERITY_LEVELS,
    format_comment_body,
    format_enhanced_summary,
)

if TYPE_CHECKING:
    from src.providers import GitProvider

logger = logging.getLogger(__name__)

STATIC_ANALYSIS_HEADER = f"## :mag: {BOT_NAME} - Static Analysis"


def deduplicate_comments(comments: list[ReviewComment]) -> list[ReviewComment]:
    """Remove duplicate comments with identical content."""
    seen_bodies: set[str] = set()
    unique = []

    for comment in comments:
        if comment.body in seen_bodies:
            continue
        seen_bodies.add(comment.body)
        unique.append(comment)

    return unique


def filter_by_severity(comments: list[ReviewComment], min_severity: str) -> list[ReviewComment]:
    """Filter comments to only include those at or above the minimum severity."""
    min_level = SEVERITY_LEVELS.get(min_severity, 2)
    return [c for c in comments if SEVERITY_LEVELS.get(c.severity, 1) >= min_level]


def post_static_analysis_comment(
    provider: "GitProvider",
    pr_number: int,
    findings: list[StaticAnalysisFinding],
) -> bool:
    """Post or update a separate comment for static analysis findings.

    This keeps semgrep/static analysis findings separate from LLM review comments,
    ensuring they are always visible regardless of the LLM comment limit.

    Args:
        provider: Git provider (GitHub, GitLab, etc.)
        pr_number: Pull request number
        findings: List of static analysis findings

    Returns:
        True if comment was posted/updated, False if no findings
    """
    if not findings:
        return False

    severity_emoji = {
        "ERROR": ":x:",
        "WARNING": ":warning:",
        "INFO": ":information_source:",
    }

    lines = [
        STATIC_ANALYSIS_HEADER,
        "",
        f"Found **{len(findings)}** issue(s) via static analysis (semgrep):",
        "",
        "| Severity | File | Line | Rule | Message |",
        "|----------|------|------|------|---------|",
    ]

    for f in findings:
        emoji = severity_emoji.get(f.severity, ":warning:")
        # Escape pipe characters in message
        safe_message = f.message.replace("|", "\\|")[:100]
        if len(f.message) > 100:
            safe_message += "..."
        lines.append(
            f"| {emoji} {f.severity} | `{f.file}` | {f.line} | `{f.rule_id}` | {safe_message} |"
        )

    lines.append("")
    lines.append(
        "> :bulb: These findings are from automated static analysis. "
        "The AI review below focuses on issues requiring human judgment."
    )
    lines.append(BOT_SIGNATURE)

    body = "\n".join(lines)

    try:
        # Check for existing static analysis comment to edit
        existing_comments = provider.get_bot_issue_comments(pr_number)
        for comment in existing_comments:
            if comment.body.startswith(STATIC_ANALYSIS_HEADER):
                if comment.body != body:
                    if provider.edit_issue_comment(pr_number, comment.id, body):
                        logger.info("Updated existing static analysis comment")
                        return True
                    logger.warning("Failed to edit static analysis comment, creating new one")
                else:
                    logger.info("Static analysis comment unchanged, skipping update")
                    return True

        # No existing comment or edit failed, create new
        provider.post_issue_comment(pr_number, body)
        logger.info(f"Posted static analysis comment with {len(findings)} findings")
        return True
    except Exception as e:
        logger.error(f"Failed to post static analysis comment: {e}")
        return False


def post_summary_comment(
    provider: "GitProvider",
    pr_number: int,
    summary: str,
    comment_count: int,
    response: ReviewResponse | None = None,
) -> None:
    """Post or update the summary comment on the PR.

    Args:
        provider: Git provider (GitHub, GitLab, etc.)
        pr_number: Pull request number
        summary: Review summary text (fallback if response not provided)
        comment_count: Number of inline comments posted
        response: Optional structured review response for enhanced formatting
    """
    header = f"## :nerd_face: {BOT_NAME} Review"

    if response:
        body = format_enhanced_summary(response, comment_count)
    else:
        # Fallback to simple format
        body = f"{header}\n\n{summary}\n\n"
        if comment_count > 0:
            body += f"Posted **{comment_count}** inline comment(s) on the code changes."
        else:
            body += "No issues found in the code changes."
        body += BOT_SIGNATURE

    try:
        # Check for existing summary comment to edit
        existing_comments = provider.get_bot_issue_comments(pr_number)
        for comment in existing_comments:
            if comment.body.startswith(header):
                if comment.body != body:
                    if provider.edit_issue_comment(pr_number, comment.id, body):
                        logger.info("Updated existing summary comment")
                        return
                    # Edit failed, fall through to create new comment
                    logger.warning("Failed to edit summary comment, creating new one")
                else:
                    logger.info("Summary comment unchanged, skipping update")
                    return

        # No existing summary or edit failed, create new
        provider.post_issue_comment(pr_number, body)
        logger.info("Posted summary comment")
    except Exception as e:
        logger.error(f"Failed to post summary comment: {e}")
        raise


def sync_comments(
    provider: "GitProvider",
    pr_number: int,
    summary: str,
    new_comments: list[ReviewComment],
    max_comments: int = 20,
    response: ReviewResponse | None = None,
    resolve_outdated: bool = True,
) -> tuple[int, int, int]:
    """Sync new comments with existing bot comments.

    Edits existing comments at same location, creates new ones, optionally deletes outdated.

    Args:
        provider: Git provider (GitHub, GitLab, etc.)
        pr_number: Pull request number
        summary: Review summary text
        new_comments: List of review comments to post
        max_comments: Maximum number of inline comments
        response: Optional structured review response for enhanced summary
        resolve_outdated: Whether to delete outdated comments from previous runs

    Returns (edited, created, deleted) counts.
    """
    pr_info = provider.get_pull_request(pr_number)
    head_commit_sha = pr_info.head_sha

    existing = provider.get_bot_review_comments(pr_number)
    # Index existing comments by (path, line), skip those with line=None (outdated)
    existing_by_location: dict[tuple[str, int], ReviewCommentInfo] = {
        (c.path, c.line): c for c in existing if c.line is not None
    }
    # Track stale comments (line=None) separately to delete them
    stale_comments = [c for c in existing if c.line is None]

    # Index new comments by (file, line)
    new_by_location = {(c.file, c.line): c for c in new_comments[:max_comments]}

    edited = created = deleted = 0

    # Edit existing or create new
    for location, new_comment in new_by_location.items():
        new_body = format_comment_body(new_comment)
        if location in existing_by_location:
            old = existing_by_location[location]
            if old.body != new_body:
                try:
                    if provider.edit_review_comment(old.id, new_body):
                        edited += 1
                        logger.info(f"Edited comment on {new_comment.file}:{new_comment.line}")
                except Exception as e:
                    logger.warning(f"Failed to edit comment: {e}")
        else:
            # Post new comment
            try:
                provider.post_review_comment(
                    pr_number=pr_number,
                    body=new_body,
                    commit_sha=head_commit_sha,
                    path=new_comment.file,
                    line=new_comment.line,
                )
                created += 1
                logger.info(f"Created comment on {new_comment.file}:{new_comment.line}")
            except Exception as e:
                logger.warning(f"Failed to create comment: {e}")

    # Delete old comments not in new set (if resolve_outdated is enabled)
    if resolve_outdated:
        for location, old_comment in existing_by_location.items():
            if location not in new_by_location:
                try:
                    if provider.delete_review_comment(old_comment.id):
                        deleted += 1
                        logger.info(f"Deleted comment on {old_comment.path}:{old_comment.line}")
                except Exception as e:
                    logger.warning(f"Failed to delete comment: {e}")

        # Delete stale comments (line=None means code changed and comment is stale)
        for old_comment in stale_comments:
            try:
                if provider.delete_review_comment(old_comment.id):
                    deleted += 1
                    logger.info(f"Deleted stale comment on {old_comment.path}")
            except Exception as e:
                logger.warning(f"Failed to delete stale comment: {e}")

    # Post summary comment
    total_synced = edited + created
    post_summary_comment(provider, pr_number, summary, total_synced, response)

    return edited, created, deleted
