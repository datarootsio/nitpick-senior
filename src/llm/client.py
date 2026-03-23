"""LLM client using Pydantic AI for provider-agnostic access with structured output."""

import logging
import os
from dataclasses import dataclass

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from .response import ReviewResponse

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
            - "azure/gpt-4o" (Azure OpenAI)
            - "openrouter/provider/model" (OpenRouter)

    Returns:
        Configured Pydantic AI model
    """
    if model_string.startswith("anthropic/"):
        return AnthropicModel(model_string.replace("anthropic/", ""))
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

    async def review(self, system_prompt: str, diff_content: str) -> ReviewResponse:
        """Generate a code review for the given diff.

        Args:
            system_prompt: The agent specification / system prompt
            diff_content: The PR diff content to review

        Returns:
            ReviewResponse with summary and comments
        """
        user_prompt = self._build_user_prompt(diff_content)

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

    def _build_user_prompt(self, diff_content: str) -> str:
        """Build the user prompt with diff content."""
        return f"""Review the following code changes and provide feedback.

## Code Changes (Unified Diff Format)

```diff
{diff_content}
```

Guidelines for comments:
- MAXIMUM 5 comments total - be extremely selective
- Only comment on bugs, security issues, or serious problems
- Use "error" for critical issues, "warning" for significant problems
- NEVER comment on the same issue twice, even on different lines
- If an issue appears multiple times, mention it ONCE with "appears in multiple places"
- The "line" must be a line number from the NEW version of the file (lines with + prefix)
- Include a "suggestion" when you have a concrete code fix
- ALWAYS check: can user/environment input cause division by zero, index errors, or crashes?
- Do NOT comment on:
  - Style, formatting, naming preferences
  - Unused variables or imports (linters catch these)
  - Missing features or enhancements
  - Hypothetical issues unrelated to actual input paths

If there are no significant issues to report, return an empty comments array."""

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
