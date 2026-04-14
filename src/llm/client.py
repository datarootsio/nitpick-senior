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

# Pricing per million tokens (input, output) - Updated March 2026
MODEL_PRICING = {
    # OpenAI
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "o3": {"input": 2.00, "output": 8.00},
    "o4-mini": {"input": 1.10, "output": 4.40},
    "o1": {"input": 15.00, "output": 60.00},
    # Anthropic Claude
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    # Google Gemini
    "gemini-3.1-pro": {"input": 2.00, "output": 12.00},
    "gemini-3-flash": {"input": 0.50, "output": 3.00},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
}


@dataclass
class UsageStats:
    """Token usage and cost statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""


def create_model(llm_provider: str, model_name: str):
    """Create a Pydantic AI model from a provider and model name.

    Args:
        llm_provider: LLM provider (openai, anthropic, google, azure, azure_foundry_anthropic,
            azure_foundry_openai, openrouter)
        model_name: Model name (e.g., gpt-4o, claude-sonnet-4-6, gemini-2.5-flash)

    Returns:
        Configured Pydantic AI model
    """
    if llm_provider == "anthropic":
        return AnthropicModel(model_name)
    elif llm_provider == "google":
        return GoogleModel(model_name)
    elif llm_provider == "azure":
        provider = OpenAIProvider(
            base_url=os.environ.get("AZURE_OPENAI_ENDPOINT"),
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        )
        return OpenAIModel(model_name, provider=provider)
    elif llm_provider == "azure_foundry_anthropic":
        from anthropic import AsyncAnthropicFoundry
        from pydantic_ai.providers.anthropic import AnthropicProvider

        foundry_client = AsyncAnthropicFoundry(
            api_key=os.environ.get("AZURE_FOUNDRY_API_KEY"),
            base_url=os.environ.get("AZURE_FOUNDRY_BASE_URL"),
            resource=os.environ.get("AZURE_FOUNDRY_RESOURCE"),
        )
        provider = AnthropicProvider(anthropic_client=foundry_client)
        return AnthropicModel(model_name, provider=provider)
    elif llm_provider == "azure_foundry_openai":
        resource = os.environ.get("AZURE_FOUNDRY_RESOURCE")
        base_url = os.environ.get("AZURE_FOUNDRY_BASE_URL")
        if not base_url and resource:
            base_url = f"https://{resource}.services.ai.azure.com/openai/v1"
        provider = OpenAIProvider(
            base_url=base_url,
            api_key=os.environ.get("AZURE_FOUNDRY_API_KEY"),
        )
        return OpenAIModel(model_name, provider=provider)
    elif llm_provider == "openrouter":
        provider = OpenAIProvider(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )
        return OpenAIModel(model_name, provider=provider)
    elif llm_provider == "openai":
        return OpenAIModel(model_name)
    else:
        raise ValueError(
            f"Unknown LLM provider: '{llm_provider}'. "
            "Supported: openai, anthropic, google, azure, azure_foundry_anthropic, "
            "azure_foundry_openai, openrouter"
        )


class LLMClient:
    """Client for interacting with LLMs via Pydantic AI."""

    def __init__(self, llm_provider: str, model: str, max_comments: int = 10):
        """Initialize the LLM client.

        Args:
            llm_provider: LLM provider (openai, anthropic, google, azure, foundry, openrouter)
            model: Model name (e.g., "gpt-4o", "claude-sonnet-4-6")
            max_comments: Maximum number of review comments to generate
        """
        self.model_string = model
        self.model = create_model(llm_provider, model)
        self.usage = UsageStats(model=model)
        self.max_comments = max_comments

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
        sections.append(f"""## Guidelines for comments:
- MAXIMUM {self.max_comments} comments total - be extremely selective
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
            parts.append("### Static Analysis Findings (Posted Separately)")
            parts.append(
                "The following issues were detected by static analysis tools and will be "
                "reported in a separate comment. **Do NOT duplicate these findings** in your "
                "review comments. Instead, focus on issues that require human judgment: "
                "logic errors, edge cases, architectural concerns, API misuse, missing "
                "validation, and other issues that static analysis cannot detect."
            )
            parts.append("")
            parts.append("Findings for reference (already reported separately):")
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
