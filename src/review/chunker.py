"""Diff chunking for large PRs."""

from dataclasses import dataclass

from src.constants import CHARS_PER_TOKEN
from src.github.diff import FileChange, parse_diff

DEFAULT_CHUNK_SIZE = 20000  # tokens


@dataclass
class DiffChunk:
    """A chunk of diff content for review."""

    files: list[str]
    content: str
    token_estimate: int


def estimate_tokens(text: str) -> int:
    """Estimate token count."""
    return len(text) // CHARS_PER_TOKEN


def chunk_diff(
    diff_content: str,
    max_chunk_tokens: int = DEFAULT_CHUNK_SIZE,
) -> list[DiffChunk]:
    """Split a large diff into reviewable chunks.

    Groups files together up to the token limit.

    Args:
        diff_content: Full unified diff
        max_chunk_tokens: Maximum tokens per chunk

    Returns:
        List of DiffChunk objects
    """
    changes = parse_diff(diff_content)

    if not changes:
        return []

    chunks = []
    current_files: list[str] = []
    current_content: list[str] = []
    current_tokens = 0
    max_chars = max_chunk_tokens * CHARS_PER_TOKEN

    for change in changes:
        file_diff = _build_file_diff(change)
        file_tokens = estimate_tokens(file_diff)

        # If single file exceeds limit, it gets its own chunk
        if file_tokens > max_chunk_tokens:
            # Flush current chunk if any
            if current_content:
                chunks.append(
                    DiffChunk(
                        files=current_files.copy(),
                        content="\n".join(current_content),
                        token_estimate=current_tokens,
                    )
                )
                current_files = []
                current_content = []
                current_tokens = 0

            # Add oversized file as its own chunk (will be truncated later)
            chunks.append(
                DiffChunk(
                    files=[change.path],
                    content=file_diff[:max_chars],
                    token_estimate=min(file_tokens, max_chunk_tokens),
                )
            )
            continue

        # Check if adding this file would exceed limit
        if current_tokens + file_tokens > max_chunk_tokens:
            # Flush current chunk
            chunks.append(
                DiffChunk(
                    files=current_files.copy(),
                    content="\n".join(current_content),
                    token_estimate=current_tokens,
                )
            )
            current_files = []
            current_content = []
            current_tokens = 0

        # Add file to current chunk
        current_files.append(change.path)
        current_content.append(file_diff)
        current_tokens += file_tokens

    # Flush remaining content
    if current_content:
        chunks.append(
            DiffChunk(
                files=current_files,
                content="\n".join(current_content),
                token_estimate=current_tokens,
            )
        )

    return chunks


def _build_file_diff(change: FileChange) -> str:
    """Build a diff string for a single file."""
    lines = [
        f"diff --git a/{change.path} b/{change.path}",
        f"--- a/{change.path}",
        f"+++ b/{change.path}",
        change.patch,
    ]
    return "\n".join(lines)
