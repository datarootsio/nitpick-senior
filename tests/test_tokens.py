"""Tests for token utilities."""

from src.utils.tokens import estimate_tokens, truncate_to_tokens


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_text(self):
        # 4 chars per token
        assert estimate_tokens("abcd") == 1
        assert estimate_tokens("abcdefgh") == 2

    def test_longer_text(self):
        text = "a" * 100
        assert estimate_tokens(text) == 25

    def test_real_text(self):
        text = "This is a sample sentence for testing token estimation."
        # 55 chars = 13 tokens (55 // 4)
        assert estimate_tokens(text) == 13


class TestTruncateToTokens:
    def test_no_truncation_needed(self):
        text = "Short text"
        result = truncate_to_tokens(text, max_tokens=100)
        assert result == text

    def test_truncation_at_limit(self):
        text = "a" * 100  # 25 tokens
        result = truncate_to_tokens(text, max_tokens=10)  # 40 chars
        assert len(result) < 100
        assert "[... truncated ...]" in result

    def test_truncation_at_newline(self):
        # Create text with newlines where truncation should happen
        text = "line1\n" + "a" * 50 + "\nline3"
        result = truncate_to_tokens(text, max_tokens=10)  # 40 chars
        # Should truncate at a newline boundary when possible
        assert "[... truncated ...]" in result

    def test_custom_marker(self):
        text = "a" * 100
        result = truncate_to_tokens(text, max_tokens=10, marker="[CUT]")
        assert "[CUT]" in result
        assert "[... truncated ...]" not in result

    def test_empty_text(self):
        result = truncate_to_tokens("", max_tokens=10)
        assert result == ""

    def test_exact_limit(self):
        # 40 chars = 10 tokens exactly
        text = "a" * 40
        result = truncate_to_tokens(text, max_tokens=10)
        assert result == text
