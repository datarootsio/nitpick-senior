"""Token estimation and text truncation utilities."""

from src.constants import CHARS_PER_TOKEN


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses a simple character-based heuristic (~4 chars per token).

    Args:
        text: Input text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // CHARS_PER_TOKEN


def truncate_to_tokens(text: str, max_tokens: int, marker: str = "[... truncated ...]") -> str:
    """Truncate text to fit within a token limit.

    Attempts to end at a newline boundary when possible.

    Args:
        text: Input text to truncate
        max_tokens: Maximum tokens allowed
        marker: Text to append when truncation occurs

    Returns:
        Truncated text with marker appended if truncation occurred
    """
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    # Try to end at a newline for cleaner output
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars * 0.8:
        truncated = truncated[:last_newline]

    return truncated + "\n\n" + marker
