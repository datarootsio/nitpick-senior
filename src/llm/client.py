"""LLM client using Pydantic AI for provider-agnostic access with structured output."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from .response import ReviewResponse

if TYPE_CHECKING:
    from src.context import RepoContext

logger = logging.getLogger(__name__)

# Pricing per million tokens (input, output)
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
}


@dataclass
class UsageStats:
    """Token usage and cost statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


def create_model(model_string: str):
    """Create a Pydantic AI model from a model string.

    Args:
        model_string: Model identifier. Supported formats:
            - "gpt-4o" (OpenAI)
            - "anthropic/claude-..." (Anthropic)
            - "google/gemini-..." (Google AI Studio)
            - "azure/gpt-4o" (Azure OpenAI)
            - "openrouter/provider/model" (OpenRouter)

    Returns:
        Configured Pydantic AI model
    """
    if model_string.startswith("anthropic/"):
        return AnthropicModel(model_string.replace("anthropic/", ""))
    elif model_string.startswith("google/"):
        return GoogleModel(model_string.replace("google/", ""))
    elif model_string.startswith("azure/"):
        provider = OpenAIProvider(
            base_url=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        )
        return OpenAIModel(model_string.replace("azure/", ""), provider=provider)
    elif model_string.startswith("openrouter/"):
        provider = OpenAIProvider(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )
        return OpenAIModel(model_string.replace("openrouter/", ""), provider=provider)
    else:
        return OpenAIModel(model_string)


class LLMClient:
    """Client for interacting with LLMs via Pydantic AI."""

    def __init__(self, model: str):
        """Initialize the LLM client.

        Args:
            model: Model string (e.g., "gpt-4o", "anthropic/claude-sonnet-4-5-20250929")
        """
        self.model_string = model
        self.model = create_model(model)
        self.usage = UsageStats(model=model)

    async def review(
        self,
        system_prompt: str,
        diff_content: str,
        context: RepoContext | None = None,
    ) -> ReviewResponse:
        """Generate a code review for the given diff.

        Args:
            system_prompt: The agent specification / system prompt
            diff_content: The PR diff content to review
            context: Optional repository context

        Returns:
            ReviewResponse with summary and comments
        """
        user_prompt = self._build_user_prompt(diff_content, context)

        agent = Agent(
            self.model,
            output_type=ReviewResponse,
            system_prompt=system_prompt,
            retries=2,
        )

        try:
            result = await agent.run(user_prompt, model_settings={"temperature": 0.3})

            # Track usage statistics
            if result.usage():
                usage = result.usage()
                self.usage.prompt_tokens += usage.request_tokens or 0
                self.usage.completion_tokens += usage.response_tokens or 0
                self.usage.total_tokens += usage.total_tokens or 0
                self.usage.cost_usd += self._calculate_cost(
                    usage.request_tokens or 0,
                    usage.response_tokens or 0,
                )

            return result.output

        except UnexpectedModelBehavior as e:
            logger.error(f"Model returned unexpected format: {e}")
            return ReviewResponse(summary="Failed to parse review response", comments=[])
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise

    def _build_user_prompt(
        self,
        diff_content: str,
        context: RepoContext | None = None,
    ) -> str:
        """Build the user prompt with diff content and optional context."""
        sections = []

        # Add context section if available
        if context and not context.is_empty():
            sections.append(self._build_context_section(context))

        # Add diff section
        sections.append(f"""## Code Changes (Unified Diff Format)

```diff
{diff_content}
```""")

        # Add guidelines
        sections.append("""## Guidelines for comments:
- MAXIMUM 5 comments total - be extremely selective
- Only comment on bugs, security issues, or serious problems
- Use "error" for critical issues, "warning" for significant problems
- NEVER comment on the same issue twice, even on different lines
- If an issue appears multiple times, mention it ONCE with "appears in multiple places"
- The "line" must be a line number from the NEW version of the file (lines with + prefix)
- ALWAYS check: can user/environment input cause division by zero, index errors, or crashes?
- Do NOT comment on:
  - Style, formatting, naming preferences
  - Unused variables or imports (linters catch these)
  - Missing features or enhancements
  - Hypothetical issues unrelated to actual input paths

## CRITICAL: Do NOT suggest fixes
- Identify WHAT is wrong and WHY (root cause)
- Do NOT tell the developer HOW to fix it
- Use the "why" field to explain the underlying architectural or logical flaw
- Force the developer to understand the problem deeply enough to fix it completely

If there are no significant issues to report, return an empty comments array.""")

        return "Review the following code changes and provide feedback.\n\n" + "\n\n".join(
            sections
        )

    def _build_context_section(self, context: RepoContext) -> str:
        """Build the context section of the prompt."""
        parts = ["## Repository Context"]

        if context.readme:
            parts.append(f"""### README
```
{context.readme}
```""")

        if context.related_files:
            parts.append("### Related Files")
            for file in context.related_files:
                parts.append(f"""#### {file.path} (reason: {file.reason})
```
{file.content}
```""")

        if context.static_analysis:
            parts.append("### Static Analysis Findings")
            parts.append(
                "The following issues were detected by static analysis tools. "
                "Consider these when reviewing the code changes:"
            )
            for f in context.static_analysis:
                parts.append(
                    f"- **{f.file}:{f.line}** [{f.severity}] `{f.rule_id}`: {f.message}"
                )

        return "\n\n".join(parts)

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost based on token usage."""
        # Extract the base model name (strip provider prefix)
        model_name = self.model_string.split("/")[-1]
        pricing = MODEL_PRICING.get(model_name)

        if not pricing:
            return 0.0

        return (input_tokens / 1_000_000) * pricing["input"] + (
            output_tokens / 1_000_000
        ) * pricing["output"]
