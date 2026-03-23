"""Comment posting utilities."""

import logging

from github.PullRequestComment import PullRequestComment

from src.github.client import GitHubClient
from src.llm.response import ReviewComment, ReviewResponse

logger = logging.getLogger(__name__)

BOT_NAME = "Nitpick Senior"
BOT_REPO = "https://github.com/datarootsio/github-reviewer"
BOT_SIGNATURE = f"\n\n---\n:nerd_face: *Um, actually... reviewed by [{BOT_NAME}]({BOT_REPO})*"

SEVERITY_LEVELS = {"error": 3, "warning": 2, "info": 1}

CATEGORY_EMOJI = {
    "Security": ":lock:",
    "Bug": ":bug:",
    "Reliability": ":zap:",
    "Performance": ":chart_with_upwards_trend:",
    "Correctness": ":white_check_mark:",
}

CONFIDENCE_LABELS = {
    5: ":white_check_mark: **Safe to merge** - no issues found",
    4: ":white_check_mark: **Safe to merge** - minor issues only",
    3: ":warning: **Review recommended** - some concerns",
    2: ":warning: **Changes needed** - significant issues",
    1: ":x: **Do not merge** - critical issues",
}


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


def format_why_block(why: str) -> str:
    """Format the root cause explanation."""
    return f"\n\n**Why this matters:** {why}"


def format_comment_body(comment: ReviewComment) -> str:
    """Format a review comment body with category badge and root cause explanation."""
    severity_emoji = {
        "error": ":x:",
        "warning": ":warning:",
        "info": ":information_source:",
    }

    emoji = severity_emoji.get(comment.severity, ":warning:")

    # Add category badge if present
    if comment.category:
        category_icon = CATEGORY_EMOJI.get(comment.category, "")
        body = (
            f"{category_icon} **{comment.category}** | "
            f"{emoji} **{comment.severity.upper()}**\n\n{comment.body}"
        )
    else:
        body = f"{emoji} **{comment.severity.upper()}**: {comment.body}"

    # Add root cause explanation if present
    if comment.why:
        body += format_why_block(comment.why)

    return body


def format_enhanced_summary(response: ReviewResponse, comment_count: int) -> str:
    """Format the enhanced review summary with confidence and file overviews.

    Args:
        response: The structured review response from the LLM
        comment_count: Number of inline comments posted

    Returns:
        Formatted markdown summary
    """
    header = f"## :nerd_face: {BOT_NAME} Review"
    lines = [header, "", response.summary, ""]

    # Confidence score
    confidence_label = CONFIDENCE_LABELS.get(response.confidence, "")
    lines.append(f"### Confidence: {response.confidence}/5")
    lines.append(confidence_label)
    lines.append("")

    # Important files table
    if response.important_files:
        lines.append("### Files Changed")
        lines.append("")
        lines.append("| File | Type | Overview |")
        lines.append("|------|------|----------|")
        for f in response.important_files:
            lines.append(f"| `{f.file}` | {f.change_type} | {f.overview} |")
        lines.append("")

    # Issues summary grouped by category
    if comment_count > 0:
        lines.append(f"### Issues Found ({comment_count})")
        lines.append("")
    else:
        lines.append(":white_check_mark: No issues found in the code changes.")
        lines.append("")

    lines.append(BOT_SIGNATURE)
    return "\n".join(lines)


def post_summary_comment(
    client: GitHubClient,
    pr_number: int,
    summary: str,
    comment_count: int,
    response: ReviewResponse | None = None,
) -> None:
    """Post or update the summary comment on the PR.

    Args:
        client: GitHub client
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


def sync_comments(
    client: GitHubClient,
    pr_number: int,
    summary: str,
    new_comments: list[ReviewComment],
    max_comments: int = 20,
    response: ReviewResponse | None = None,
) -> tuple[int, int, int]:
    """Sync new comments with existing bot comments.

    Edits existing comments at same location, creates new ones, deletes outdated.

    Args:
        client: GitHub client
        pr_number: Pull request number
        summary: Review summary text
        new_comments: List of review comments to post
        max_comments: Maximum number of inline comments
        response: Optional structured review response for enhanced summary

    Returns (edited, created, deleted) counts.
    """
    pr = client.get_pull_request(pr_number)
    commit_sha = pr.head.sha

    existing = client.get_bot_comments(pr_number)
    # Index existing comments by (path, line), skip those with line=None (outdated)
    existing_by_location: dict[tuple[str, int], PullRequestComment] = {
        (c.path, c.line): c for c in existing if c.line is not None
    }
    # Track outdated comments (line=None) separately to minimize them
    outdated_comments = [c for c in existing if c.line is None]

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

    # Delete old comments not in new set
    for location, old_comment in existing_by_location.items():
        if location not in new_by_location:
            try:
                if client.delete_review_comment(old_comment):
                    minimized += 1
                    logger.info(f"Deleted comment on {old_comment.path}:{old_comment.line}")
            except Exception as e:
                logger.warning(f"Failed to delete comment: {e}")

    # Delete outdated comments (line=None means code changed and comment is stale)
    for old_comment in outdated_comments:
        try:
            if client.delete_review_comment(old_comment):
                minimized += 1
                logger.info(f"Deleted outdated comment on {old_comment.path}")
        except Exception as e:
            logger.warning(f"Failed to delete outdated comment: {e}")

    # Post summary comment
    total_posted = edited + created
    post_summary_comment(client, pr_number, summary, total_posted, response)

    return edited, created, minimized
