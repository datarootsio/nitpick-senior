"""Main context collector orchestrator."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from src.utils.tokens import estimate_tokens, truncate_to_tokens

from .extractors.files import fetch_file_content, fetch_readme
from .extractors.imports import detect_language, extract_imports, resolve_import_paths
from .models import RelatedFile, RepoContext

if TYPE_CHECKING:
    from src.providers import GitProvider

logger = logging.getLogger(__name__)

# Default token limits
DEFAULT_MAX_CONTEXT_TOKENS = 5000
DEFAULT_MAX_README_TOKENS = 2000
DEFAULT_MAX_FILE_TOKENS = 1000

# Patterns for sensitive files that should never be included in context
SENSITIVE_PATTERNS = [
    ".env",
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    "secret",
    "credential",
    "password",
    "token",
    ".htpasswd",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
]

# Allowed source code extensions
ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".java",
    ".kt",
    ".rs",
    ".rb",
    ".php",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".swift",
    ".scala",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
}


class ContextCollector:
    """Collects repository context for PR reviews."""

    def __init__(
        self,
        provider: GitProvider,
        max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
        max_readme_tokens: int = DEFAULT_MAX_README_TOKENS,
        max_file_tokens: int = DEFAULT_MAX_FILE_TOKENS,
    ):
        """Initialize the context collector.

        Args:
            provider: Git provider (GitHub, GitLab, etc.)
            max_context_tokens: Maximum total tokens for context
            max_readme_tokens: Maximum tokens for README
            max_file_tokens: Maximum tokens per related file
        """
        self.provider = provider
        self.max_context_tokens = max_context_tokens
        self.max_readme_tokens = max_readme_tokens
        self.max_file_tokens = max_file_tokens

    async def collect(
        self,
        pr_number: int,
        changed_files: list[str],
        diff_content: str,
    ) -> RepoContext:
        """Collect repository context for a PR.

        Args:
            pr_number: Pull request number
            changed_files: List of changed file paths
            diff_content: The PR diff content

        Returns:
            RepoContext with collected context
        """
        context = RepoContext()
        tokens_used = 0

        # Get the PR head ref for fetching files
        pr_info = self.provider.get_pull_request(pr_number)
        ref = pr_info.head_sha

        # 1. Fetch README
        readme = fetch_readme(self.provider, ref)
        if readme:
            readme = truncate_to_tokens(readme, self.max_readme_tokens)
            readme_tokens = estimate_tokens(readme)
            if tokens_used + readme_tokens <= self.max_context_tokens:
                context.readme = readme
                tokens_used += readme_tokens
                logger.info(f"Added README ({readme_tokens} tokens)")

        # 2. Extract and fetch imported files
        imported_paths = self._extract_imported_files(changed_files, diff_content, ref)

        for path in imported_paths:
            if tokens_used >= self.max_context_tokens:
                logger.info("Context token limit reached, stopping file collection")
                break

            # Skip if already a changed file
            if path in changed_files:
                continue

            # Skip sensitive files
            if self._is_sensitive_file(path):
                logger.debug(f"Skipping sensitive file: {path}")
                continue

            content = fetch_file_content(self.provider, path, ref)
            if content is None:
                continue

            content = truncate_to_tokens(content, self.max_file_tokens)
            file_tokens = estimate_tokens(content)

            if tokens_used + file_tokens <= self.max_context_tokens:
                context.related_files.append(
                    RelatedFile(
                        path=path,
                        content=content,
                        reason="import",
                    )
                )
                tokens_used += file_tokens
                logger.info(f"Added imported file: {path} ({file_tokens} tokens)")

        context.total_tokens = tokens_used
        logger.info(f"Context collection complete: {tokens_used} tokens total")

        return context

    def _extract_imported_files(
        self,
        changed_files: list[str],
        diff_content: str,
        ref: str,
    ) -> list[str]:
        """Extract imported file paths from changed files.

        Args:
            changed_files: List of changed file paths
            diff_content: The diff content (for extracting new code)
            ref: Git ref for fetching full file content

        Returns:
            List of unique imported file paths
        """
        imported_paths: set[str] = set()

        for file_path in changed_files:
            language = detect_language(file_path)
            if not language:
                continue

            # Fetch the full file content to extract all imports
            content = fetch_file_content(self.provider, file_path, ref)
            if not content:
                continue

            imports = extract_imports(content, language)

            for import_name in imports:
                candidates = resolve_import_paths(import_name, file_path, language)
                for resolved in candidates:
                    # Normalize the path
                    resolved = os.path.normpath(resolved)
                    if not resolved.startswith(".."):
                        imported_paths.add(resolved)

        return list(imported_paths)

    def _is_sensitive_file(self, path: str) -> bool:
        """Check if a file path matches sensitive patterns.

        Args:
            path: File path to check

        Returns:
            True if the file should be excluded from context
        """
        path_lower = path.lower()

        # Check for sensitive patterns in path
        for pattern in SENSITIVE_PATTERNS:
            if pattern in path_lower:
                return True

        # Check if extension is allowed
        ext = os.path.splitext(path)[1].lower()
        return bool(ext and ext not in ALLOWED_EXTENSIONS)
