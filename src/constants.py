"""Shared constants."""

# Approximate characters per token for token estimation.
# Based on OpenAI's observation that ~4 characters = 1 token for English text.
# This is a rough estimate used for budget calculations before actual tokenization.
CHARS_PER_TOKEN = 4
