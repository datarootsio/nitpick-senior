# GitHub Setup

Nitpick Senior works natively with GitHub Actions. This is the default provider and requires minimal configuration.

## Prerequisites

- A GitHub repository with Actions enabled
- A GitHub token with PR read/write permissions
- An LLM API key (OpenAI, Anthropic, Azure OpenAI, or AWS Bedrock)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub token for PR access (automatically provided in Actions) |
| `INPUT_MODEL` | Yes | LiteLLM model string (e.g., `gpt-4o`, `anthropic/claude-sonnet-4-5-20250929`) |
| `OPENAI_API_KEY` | Conditional | Required for OpenAI models |
| `ANTHROPIC_API_KEY` | Conditional | Required for Anthropic models |

## Configuration

### Step 1: Create the Workflow File

Create `.github/workflows/ai-review.yml` in your repository:

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: AI Code Review
        uses: datarootsio/nitpick-senior@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          model: gpt-4o
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Step 2: Add Secrets

1. Go to your repository **Settings** > **Secrets and variables** > **Actions**
2. Add your LLM API key:
   - For OpenAI: Add `OPENAI_API_KEY`
   - For Anthropic: Add `ANTHROPIC_API_KEY`

### Step 3 (Optional): Customize Review Behavior

Create `.github/ai-reviewer.md` to customize the review agent:

```markdown
You are a senior code reviewer focusing on:
- Security vulnerabilities
- Performance issues
- Code maintainability

Be constructive and provide actionable suggestions.
```

## Full Configuration Example

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: AI Code Review
        uses: datarootsio/nitpick-senior@v1
        with:
          # Authentication
          github_token: ${{ secrets.GITHUB_TOKEN }}

          # Model configuration
          model: anthropic/claude-sonnet-4-5-20250929

          # Review behavior
          agent_spec_path: .github/ai-reviewer.md
          post_summary: true
          post_inline_comments: true
          max_comments: 15
          min_severity: warning

          # Context settings
          context_enabled: true
          context_max_tokens: 5000
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Using with GitHub Enterprise

For GitHub Enterprise Server, the action works the same way. Ensure your self-hosted runner has network access to your LLM provider.

## Inputs Reference

| Input | Default | Description |
|-------|---------|-------------|
| `github_token` | - | GitHub token for PR access |
| `model` | - | LiteLLM model string |
| `agent_spec_path` | `.github/ai-reviewer.md` | Path to agent spec file |
| `post_summary` | `true` | Post PR summary comment |
| `post_inline_comments` | `true` | Post inline code comments |
| `max_comments` | `10` | Maximum inline comments |
| `min_severity` | `warning` | Minimum severity (error, warning, info) |
| `context_enabled` | `true` | Include repo context in review |
| `context_max_tokens` | `5000` | Max tokens for context |

## Outputs

| Output | Description |
|--------|-------------|
| `comment_count` | Number of comments posted |
| `summary` | Brief review summary |
| `total_tokens` | Total tokens used |
| `cost_usd` | Estimated cost in USD |

## Troubleshooting

### "Resource not accessible by integration"

Ensure your workflow has the correct permissions:

```yaml
permissions:
  contents: read
  pull-requests: write
```

### Comments not appearing

1. Check that `post_inline_comments` is `true`
2. Verify the token has write access to pull requests
3. Check the action logs for errors

### Rate limiting

If you hit API rate limits, consider:
- Reducing `max_comments`
- Using a model with higher rate limits
- Adding delays between PR reviews
