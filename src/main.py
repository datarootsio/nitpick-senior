"""Main entry point for the AI PR Reviewer action."""

import asyncio
import logging
import os
import sys

from src.config import Config
from src.github.client import GitHubClient
from src.github.comments import (
    deduplicate_comments,
    filter_by_severity,
    post_summary_comment,
    sync_comments,
)
from src.llm.client import LLMClient
from src.prompts.loader import load_agent_spec
from src.review.analyzer import analyze_pr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> int:
    """Main entry point."""
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config.from_env()

        # Initialize clients
        logger.info(f"Initializing clients for {config.repo_owner}/{config.repo_name}")
        github_client = GitHubClient(
            token=config.github_token,
            repo_owner=config.repo_owner,
            repo_name=config.repo_name,
        )

        llm_client = LLMClient(model=config.model)
        logger.info(f"Using model: {config.model}")

        # Load agent specification
        system_prompt = load_agent_spec(config.agent_spec_path)

        # Analyze the PR
        logger.info(f"Analyzing PR #{config.pr_number}...")
        response = await analyze_pr(
            github_client=github_client,
            llm_client=llm_client,
            pr_number=config.pr_number,
            system_prompt=system_prompt,
        )

        # Deduplicate comments first
        deduped_comments = deduplicate_comments(response.comments)
        if len(deduped_comments) < len(response.comments):
            logger.info(
                f"Removed {len(response.comments) - len(deduped_comments)} duplicate comments"
            )

        # Filter comments by severity
        filtered_comments = filter_by_severity(deduped_comments, config.min_severity)
        if len(filtered_comments) < len(deduped_comments):
            logger.info(
                f"Filtered {len(deduped_comments) - len(filtered_comments)} "
                f"comments below {config.min_severity} severity"
            )

        # Post results
        if config.post_inline_comments and filtered_comments:
            logger.info(f"Syncing {len(filtered_comments)} comments...")
            edited, created, minimized = sync_comments(
                client=github_client,
                pr_number=config.pr_number,
                summary=response.summary,
                new_comments=filtered_comments,
                max_comments=config.max_comments,
            )
            comment_count = edited + created
            logger.info(
                f"Synced comments: {edited} edited, {created} created, {minimized} minimized"
            )
        elif config.post_summary:
            logger.info("Posting summary comment...")
            post_summary_comment(
                client=github_client,
                pr_number=config.pr_number,
                summary=response.summary,
                comment_count=0,
            )
            comment_count = 0
        else:
            logger.info("Review complete (posting disabled)")
            comment_count = 0

        # Output results using GITHUB_OUTPUT file
        logger.info(f"Review complete: {comment_count} comments posted")

        # Log cost summary
        usage = llm_client.usage
        logger.info("=" * 50)
        logger.info("USAGE SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Model: {usage.model}")
        logger.info(f"Prompt tokens: {usage.prompt_tokens:,}")
        logger.info(f"Completion tokens: {usage.completion_tokens:,}")
        logger.info(f"Total tokens: {usage.total_tokens:,}")
        if usage.cost_usd > 0:
            logger.info(f"Estimated cost: ${usage.cost_usd:.4f} USD")
        else:
            logger.info("Estimated cost: Unable to calculate (model pricing not available)")
        logger.info("=" * 50)

        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"comment_count={comment_count}\n")
                # Escape newlines for multiline summary
                safe_summary = response.summary[:200].replace("\n", " ")
                f.write(f"summary={safe_summary}\n")
                f.write(f"total_tokens={usage.total_tokens}\n")
                f.write(f"cost_usd={usage.cost_usd:.4f}\n")

        return 0

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
