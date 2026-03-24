"""Fetch file contents from repository."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.providers import GitProvider

logger = logging.getLogger(__name__)

# Common README file names in order of preference
README_NAMES = [
    "README.md",
    "README.rst",
    "README.txt",
    "README",
    "readme.md",
]


def fetch_readme(provider: GitProvider, ref: str | None = None) -> str | None:
    """Fetch README content from the repository.

    Args:
        provider: Git provider (GitHub, GitLab, etc.)
        ref: Git ref (branch, tag, commit SHA) to fetch from

    Returns:
        README content or None if not found
    """
    for readme_name in README_NAMES:
        content = fetch_file_content(provider, readme_name, ref)
        if content is not None:
            logger.debug(f"Found README: {readme_name}")
            return content

    logger.debug("No README found in repository")
    return None


def fetch_file_content(
    provider: GitProvider,
    path: str,
    ref: str | None = None,
) -> str | None:
    """Fetch file content from the repository.

    Args:
        provider: Git provider (GitHub, GitLab, etc.)
        path: File path relative to repo root
        ref: Git ref (branch, tag, commit SHA) to fetch from

    Returns:
        File content or None if not found
    """
    try:
        content = provider.get_file_content(path, ref)
        return content
    except Exception as e:
        logger.warning(f"Could not fetch {path} at ref {ref}: {type(e).__name__}: {e}")
        return None


def fetch_files_with_fallback(
    provider: GitProvider,
    base_path: str,
    extensions: list[str],
    ref: str | None = None,
) -> tuple[str | None, str | None]:
    """Try fetching a file with different extensions.

    Args:
        provider: Git provider (GitHub, GitLab, etc.)
        base_path: Base file path without extension
        extensions: List of extensions to try (e.g., [".ts", ".tsx", ".js"])
        ref: Git ref to fetch from

    Returns:
        Tuple of (content, actual_path) or (None, None) if not found
    """
    for ext in extensions:
        path = f"{base_path}{ext}"
        content = fetch_file_content(provider, path, ref)
        if content is not None:
            return content, path

    return None, None
