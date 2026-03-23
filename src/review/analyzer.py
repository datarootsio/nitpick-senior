"""Core PR analysis logic."""

import logging

from src.constants import CHARS_PER_TOKEN
from src.context import ContextCollector, RepoContext
from src.github.client import GitHubClient
from src.github.diff import get_changed_line_numbers
from src.llm.client import LLMClient
from src.llm.response import ReviewComment, ReviewResponse

logger = logging.getLogger(__name__)

MAX_DIFF_TOKENS = 30000  # Leave room for response
DEFAULT_CONTEXT_TOKENS = 5000


def estimate_tokens(text: str) -> int:
    """Estimate token count for text."""
    return len(text) // CHARS_PER_TOKEN


def truncate_diff(diff_content: str, max_tokens: int = MAX_DIFF_TOKENS) -> str:
    """Truncate diff to fit within token limit."""
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(diff_content) <= max_chars:
        return diff_content

    # Truncate and add notice
    truncated = diff_content[:max_chars]
    # Try to end at a newline
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars * 0.8:
        truncated = truncated[:last_newline]

    return truncated + "\n\n[... diff truncated due to size ...]"


def filter_valid_comments(
    comments: list[ReviewComment],
    diff_content: str,
) -> list[ReviewComment]:
    """Filter comments to only include those targeting valid changed lines."""
    valid_comments = []

    for comment in comments:
        # Get the valid line numbers for this file
        valid_lines = get_changed_line_numbers(diff_content, comment.file)

        if comment.line in valid_lines:
            valid_comments.append(comment)
        else:
            logger.warning(
                f"Skipping comment on {comment.file}:{comment.line} - line not in changed lines"
            )

    return valid_comments


async def analyze_pr(
    github_client: GitHubClient,
    llm_client: LLMClient,
    pr_number: int,
    system_prompt: str,
    context_enabled: bool = True,
    context_max_tokens: int = DEFAULT_CONTEXT_TOKENS,
) -> ReviewResponse:
    """Analyze a pull request and generate review feedback.

    Args:
        github_client: GitHub API client
        llm_client: LLM client for review generation
        pr_number: Pull request number to analyze
        system_prompt: Agent specification / system prompt
        context_enabled: Whether to collect repository context
        context_max_tokens: Maximum tokens for context

    Returns:
        ReviewResponse with summary and comments
    """
    # Fetch the PR diff
    logger.info(f"Fetching diff for PR #{pr_number}")
    diff_content = github_client.get_pr_diff(pr_number)

    if not diff_content.strip():
        logger.info("PR has no diff content")
        return ReviewResponse(
            summary="No code changes to review.",
            comments=[],
        )

    # Collect repository context
    context: RepoContext | None = None
    if context_enabled:
        logger.info("Collecting repository context...")
        changed_files = github_client.get_changed_files(pr_number)
        collector = ContextCollector(
            github_client=github_client,
            max_context_tokens=context_max_tokens,
        )
        context = await collector.collect(pr_number, changed_files, diff_content)
        if context.is_empty():
            logger.info("No context collected")
            context = None
        else:
            logger.info(
                f"Context collected: {context.total_tokens} tokens, "
                f"{len(context.related_files)} related files"
            )

    # Calculate available tokens for diff (reduce if context was collected)
    max_diff_tokens = MAX_DIFF_TOKENS
    if context:
        max_diff_tokens = MAX_DIFF_TOKENS - context.total_tokens

    # Log diff size
    token_estimate = estimate_tokens(diff_content)
    logger.info(f"Diff size: ~{token_estimate} tokens (max: {max_diff_tokens})")

    # Truncate if needed
    diff_content = truncate_diff(diff_content, max_diff_tokens)

    # Generate review
    logger.info("Generating review...")
    response = await llm_client.review(system_prompt, diff_content, context)

    # Filter comments to only valid lines
    if response.comments:
        original_count = len(response.comments)
        response.comments = filter_valid_comments(response.comments, diff_content)
        if len(response.comments) < original_count:
            logger.info(
                f"Filtered {original_count - len(response.comments)} comments "
                "targeting invalid lines"
            )

    logger.info(f"Review complete: {len(response.comments)} comments")

    return response
