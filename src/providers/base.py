"""Base provider class with common functionality."""

import logging
from collections.abc import Callable
from typing import TypeVar

from .protocol import PullRequestInfo

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseProvider:
    """Base class with common provider functionality.

    Provides shared caching and error handling patterns for all providers.
    """

    def __init__(self) -> None:
        """Initialize base provider with empty PR cache."""
        self._pr_cache: dict[int, PullRequestInfo] = {}

    def _get_cached_pr(self, pr_number: int) -> PullRequestInfo | None:
        """Get a cached pull request info if available.

        Args:
            pr_number: Pull request number

        Returns:
            Cached PullRequestInfo or None if not cached
        """
        return self._pr_cache.get(pr_number)

    def _cache_pr(self, pr_number: int, info: PullRequestInfo) -> None:
        """Cache pull request info.

        Args:
            pr_number: Pull request number
            info: Pull request info to cache
        """
        self._pr_cache[pr_number] = info

    def _safe_api_call(
        self,
        operation: Callable[[], T],
        fallback: T,
        error_msg: str = "",
    ) -> T:
        """Execute an API call with standardized error handling.

        Args:
            operation: Callable to execute
            fallback: Value to return on failure
            error_msg: Message prefix for logging

        Returns:
            Operation result or fallback on failure
        """
        try:
            return operation()
        except Exception as e:
            if error_msg:
                logger.warning(f"{error_msg}: {e}")
            else:
                logger.warning(f"API call failed: {e}")
            return fallback
