"""LLM client using LiteLLM for provider-agnostic access."""

import json
import logging

import litellm
from pydantic import ValidationError

from .response import ReviewResponse

logger = logging.getLogger(__name__)

# Disable LiteLLM's verbose logging
litellm.suppress_debug_info = True


class LLMClient:
    """Client for interacting with LLMs via LiteLLM."""

    def __init__(self, model: str):
        """Initialize the LLM client.

        Args:
            model: LiteLLM model string (e.g., "gpt-4o", "anthropic/claude-sonnet-4-5-20250929")
        """
        self.model = model

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
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
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
- Use "error" severity for critical issues (security vulnerabilities, bugs)
- Use "warning" for code quality issues and best practice violations
- Use "info" for suggestions and improvements
- The "line" must be a line number from the NEW version of the file (lines with + prefix)
- Include a "suggestion" when you have a concrete code fix
- Be concise but specific in your explanations

If there are no issues to report, return an empty comments array."""

    def _parse_response(self, content: str) -> ReviewResponse:
        """Parse the LLM response into a ReviewResponse."""
        try:
            data = json.loads(content)
            return ReviewResponse.model_validate(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response content: {content}")
            # Return empty response on parse failure
            return ReviewResponse(
                summary="Failed to parse review response", comments=[]
            )
        except ValidationError as e:
            logger.error(f"Response validation failed: {e}")
            # Try to extract what we can
            try:
                data = json.loads(content)
                return ReviewResponse(
                    summary=data.get("summary", "Review completed"),
                    comments=[],
                )
            except Exception:
                return ReviewResponse(
                    summary="Failed to validate review response", comments=[]
                )
