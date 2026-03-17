"""LLM client using LiteLLM for provider-agnostic access."""

import json
import logging
import re
from dataclasses import dataclass

import litellm
from pydantic import ValidationError

from .response import ReviewResponse

logger = logging.getLogger(__name__)

# Disable LiteLLM's verbose logging
litellm.suppress_debug_info = True


@dataclass
class UsageStats:
    """Token usage and cost statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


class LLMClient:
    """Client for interacting with LLMs via LiteLLM."""

    def __init__(self, model: str):
        """Initialize the LLM client.

        Args:
            model: LiteLLM model string (e.g., "gpt-4o", "anthropic/claude-sonnet-4-5-20250929")
        """
        self.model = model
        self.usage = UsageStats(model=model)

    def review(self, system_prompt: str, diff_content: str) -> ReviewResponse:
        """Generate a code review for the given diff.

        Args:
            system_prompt: The agent specification / system prompt
            diff_content: The PR diff content to review

        Returns:
            ReviewResponse with summary and comments
        """
        user_prompt = self._build_user_prompt(diff_content)

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )

            if not response.choices:
                raise ValueError("LLM returned empty response")

            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLM returned empty message content")

            # Track usage statistics
            if hasattr(response, "usage") and response.usage:
                self.usage.prompt_tokens += response.usage.prompt_tokens or 0
                self.usage.completion_tokens += response.usage.completion_tokens or 0
                self.usage.total_tokens += response.usage.total_tokens or 0

            # Calculate cost using LiteLLM
            try:
                cost = litellm.completion_cost(completion_response=response)
                self.usage.cost_usd += cost
            except Exception:
                pass  # Cost calculation not available for all models

            return self._parse_response(content)

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise

    def _build_user_prompt(self, diff_content: str) -> str:
        """Build the user prompt with diff and response format instructions."""
        return f"""Review the following code changes and provide feedback.

## Code Changes (Unified Diff Format)

```diff
{diff_content}
```

## Response Format

Respond with a JSON object in this exact format:
{{
    "summary": "Brief summary of what this PR does (2-3 sentences)",
    "comments": [
        {{
            "file": "path/to/file.py",
            "line": 42,
            "body": "Clear explanation of the issue",
            "suggestion": "// Optional: suggested fix code",
            "severity": "warning"
        }}
    ]
}}

Guidelines for comments:
- Only comment on actual issues (bugs, security, performance, bad practices)
- Use "error" severity for critical issues (security vulnerabilities, bugs that will cause failures)
- Use "warning" for code quality issues and best practice violations
- Do NOT use "info" severity - only comment if it's at least a warning
- The "line" must be a line number from the NEW version of the file (lines with + prefix)
- Include a "suggestion" when you have a concrete code fix
- Be concise but specific in your explanations
- Do NOT comment on:
  - Stylistic preferences or formatting (assume linters/formatters handle this)
  - Missing features that weren't part of the change
  - Theoretical issues that are unlikely in practice
  - The same issue multiple times - consolidate into one comment
- Aim for 5-10 high-quality comments maximum, not comprehensive coverage

If there are no significant issues to report, return an empty comments array."""

    def _extract_json(self, content: str) -> str:
        """Extract JSON from response that may contain markdown or other text."""
        # Try to find JSON in code blocks first
        json_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_block:
            return json_block.group(1)

        # Try to find raw JSON object
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            return json_match.group(0)

        return content

    def _parse_response(self, content: str) -> ReviewResponse:
        """Parse the LLM response into a ReviewResponse."""
        # Extract JSON from possibly markdown-wrapped response
        json_str = self._extract_json(content)

        try:
            data = json.loads(json_str)
            return ReviewResponse.model_validate(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response content: {content[:500]}")
            return ReviewResponse(
                summary="Failed to parse review response", comments=[]
            )
        except ValidationError as e:
            logger.error(f"Response validation failed: {e}")
            try:
                data = json.loads(json_str)
                return ReviewResponse(
                    summary=data.get("summary", "Review completed"),
                    comments=[],
                )
            except Exception:
                return ReviewResponse(
                    summary="Failed to validate review response", comments=[]
                )
