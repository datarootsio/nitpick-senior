"""Comment posting utilities."""

import logging

from github.PullRequestComment import PullRequestComment

from src.github.client import GitHubClient
from src.llm.response import ReviewComment

logger = logging.getLogger(__name__)

BOT_NAME = "Nitpick Senior"
BOT_REPO = "https://github.com/datarootsio/github-reviewer"
BOT_SIGNATURE = f"\n\n---\n:nerd_face: *Um, actually... reviewed by [{BOT_NAME}]({BOT_REPO})*"

SEVERITY_LEVELS = {"error": 3, "warning": 2, "info": 1}


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


def format_suggestion_block(suggestion: str) -> str:
    """Format a code suggestion as a GitHub suggestion block."""
    return f"\n\n```suggestion\n{suggestion}\n```"


def format_comment_body(comment: ReviewComment) -> str:
    """Format a review comment body with optional suggestion."""
    severity_emoji = {
        "error": ":x:",
        "warning": ":warning:",
        "info": ":information_source:",
    }

    emoji = severity_emoji.get(comment.severity, ":warning:")
    body = f"{emoji} **{comment.severity.upper()}**: {comment.body}"

    if comment.suggestion:
        body += format_suggestion_block(comment.suggestion)

    return body


def post_summary_comment(
    client: GitHubClient,
    pr_number: int,
    summary: str,
    comment_count: int,
) -> None:
    """Post or update the summary comment on the PR.

    Args:
        client: GitHub client
        pr_number: Pull request number
        summary: Review summary text
        comment_count: Number of inline comments posted
    """
    header = f"## :nerd_face: {BOT_NAME} Review"
    body = f"{header}\n\n{summary}\n\n"

    if comment_count > 0:
        body += f"Posted **{comment_count}** inline comment(s) on the code changes."
    else:
        body += "No issues found in the code changes."

    body += BOT_SIGNATURE

    try:
        # Check for existing summary comment to edit
        existing_comments = client.get_bot_issue_comments(pr_number)
        for comment in existing_comments:
            if comment.body.startswith(header):
                if comment.body != body:
                    comment.edit(body)
                    logger.info("Updated existing summary comment")
                else:
                    logger.info("Summary comment unchanged, skipping update")
                return

        # No existing summary, create new
        client.post_comment(pr_number, body)
        logger.info("Posted summary comment")
    except Exception as e:
        logger.error(f"Failed to post summary comment: {e}")
        raise


def post_inline_comment(
    client: GitHubClient,
    pr_number: int,
    commit_sha: str,
    comment: ReviewComment,
) -> bool:
    """Post a single inline comment.

    Returns True if successful, False otherwise.
    """
    body = format_comment_body(comment)

    try:
        client.post_review_comment(
            pr_number=pr_number,
            body=body,
            commit_sha=commit_sha,
            path=comment.file,
            line=comment.line,
        )
        logger.info(f"Posted comment on {comment.file}:{comment.line}")
        return True
    except Exception as e:
        logger.warning(f"Failed to post comment on {comment.file}:{comment.line}: {e}")
        return False


def sync_comments(
    client: GitHubClient,
    pr_number: int,
    summary: str,
    new_comments: list[ReviewComment],
    max_comments: int = 20,
) -> tuple[int, int, int]:
    """Sync new comments with existing bot comments.

    Edits existing comments at same location, creates new ones, minimizes outdated.

    Returns (edited, created, minimized) counts.
    """
    pr = client.get_pull_request(pr_number)
    commit_sha = pr.head.sha

    existing = client.get_bot_comments(pr_number)
    # Index existing comments by (path, line), skip those with line=None (outdated)
    existing_by_location: dict[tuple[str, int], PullRequestComment] = {
        (c.path, c.line): c for c in existing if c.line is not None
    }

    # Index new comments by (file, line)
    new_by_location = {(c.file, c.line): c for c in new_comments[:max_comments]}

    edited = created = minimized = 0

    # Edit existing or create new
    for location, new_comment in new_by_location.items():
        new_body = format_comment_body(new_comment)
        if location in existing_by_location:
            old = existing_by_location[location]
            if old.body != new_body:
                try:
                    old.edit(new_body)
                    edited += 1
                    logger.info(f"Edited comment on {new_comment.file}:{new_comment.line}")
                except Exception as e:
                    logger.warning(f"Failed to edit comment: {e}")
        else:
            # Post new comment
            try:
                client.post_review_comment(
                    pr_number=pr_number,
                    body=new_body,
                    commit_sha=commit_sha,
                    path=new_comment.file,
                    line=new_comment.line,
                )
                created += 1
                logger.info(f"Created comment on {new_comment.file}:{new_comment.line}")
            except Exception as e:
                logger.warning(f"Failed to create comment: {e}")

    # Minimize old comments not in new set
    for location, old_comment in existing_by_location.items():
        if location not in new_by_location:
            try:
                if client._minimize_comment(old_comment.node_id):
                    minimized += 1
                    logger.info(f"Minimized comment on {old_comment.path}:{old_comment.line}")
            except Exception as e:
                logger.warning(f"Failed to minimize comment: {e}")

    # Post summary comment
    total_posted = edited + created
    post_summary_comment(client, pr_number, summary, total_posted)

    return edited, created, minimized


def post_review_with_comments(
    client: GitHubClient,
    pr_number: int,
    summary: str,
    comments: list[ReviewComment],
    max_comments: int = 20,
) -> int:
    """Post a review with multiple inline comments.

    Uses GitHub's review API to post all comments atomically.

    Returns the number of comments posted.
    """
    # Limit comments to max
    comments_to_post = comments[:max_comments]

    if not comments_to_post:
        # Just post the summary
        post_summary_comment(client, pr_number, summary, 0)
        return 0

    # Format comments for the review API
    review_comments = []
    for comment in comments_to_post:
        review_comments.append(
            {
                "path": comment.file,
                "line": comment.line,
                "body": format_comment_body(comment),
            }
        )

    # Build review body
    header = f"## :nerd_face: {BOT_NAME} Review"
    review_body = f"{header}\n\n{summary}"
    review_body += BOT_SIGNATURE

    try:
        client.create_review(
            pr_number=pr_number,
            body=review_body,
            comments=review_comments,
            event="COMMENT",
        )
        logger.info(f"Posted review with {len(review_comments)} comments")
        return len(review_comments)
    except Exception as e:
        logger.error(f"Failed to post review: {e}")
        # Fall back to posting summary only
        post_summary_comment(client, pr_number, summary, 0)
        return 0
