"""Load agent specification from repository."""

import logging
import os

from .defaults import DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def load_agent_spec(spec_path: str) -> str:
    """Load the agent specification from the repository.

    Args:
        spec_path: Path to the agent spec file (relative to repo root)

    Returns:
        The agent specification content, or default prompt if not found
    """
    # In GitHub Actions, GITHUB_WORKSPACE is the repo root
    workspace = os.environ.get("GITHUB_WORKSPACE", ".")
    full_path = os.path.join(workspace, spec_path)

    if os.path.exists(full_path):
        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    logger.info(f"Loaded agent spec from {spec_path}")
                    return content
        except Exception as e:
            logger.warning(f"Failed to read agent spec from {spec_path}: {e}")

    logger.info("Using default system prompt (no agent spec found)")
    return DEFAULT_SYSTEM_PROMPT
