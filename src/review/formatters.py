"""Comment formatting utilities."""

from src.llm.response import ReviewComment, ReviewResponse

BOT_NAME = "Nitpick Senior"
BOT_REPO = "https://github.com/datarootsio/nitpick-senior"
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
