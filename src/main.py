"""Main entry point for the AI PR Reviewer action."""

import logging
import sys

from src.config import Config
from src.github.client import GitHubClient
from src.github.comments import post_review_with_comments, post_summary_comment
from src.llm.client import LLMClient
from src.prompts.loader import load_agent_spec
from src.review.analyzer import analyze_pr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
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
        response = analyze_pr(
            github_client=github_client,
            llm_client=llm_client,
            pr_number=config.pr_number,
            system_prompt=system_prompt,
        )

        # Post results
        if config.post_inline_comments and response.comments:
            logger.info(f"Posting review with {len(response.comments)} comments...")
            comment_count = post_review_with_comments(
                client=github_client,
                pr_number=config.pr_number,
                summary=response.summary,
                comments=response.comments,
                max_comments=config.max_comments,
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

        # Output results
        logger.info(f"Review complete: {comment_count} comments posted")
        print(f"::set-output name=comment_count::{comment_count}")
        print(f"::set-output name=summary::{response.summary[:200]}")

        return 0

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
