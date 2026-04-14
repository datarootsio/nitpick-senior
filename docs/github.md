# GitHub Setup

Nitpick Senior works natively with GitHub Actions. This is the default provider and requires minimal configuration.

## Prerequisites

- A GitHub repository with Actions enabled
- A GitHub token with PR read/write permissions
- An LLM API key (OpenAI, Anthropic, Azure OpenAI, Azure Foundry, or OpenRouter)

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
          llm_provider: openai
          model: gpt-4o
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Step 2: Add Secrets

1. Go to your repository **Settings** > **Secrets and variables** > **Actions**
2. Add your LLM API key (depends on your chosen provider)

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
          github_token: ${{ secrets.GITHUB_TOKEN }}
          llm_provider: anthropic
          model: claude-sonnet-4-6
          agent_spec_path: .github/ai-reviewer.md
          post_summary: true
          post_inline_comments: true
          max_comments: 15
          min_severity: warning
          context_enabled: true
          context_max_tokens: 5000
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## LLM Provider Examples

### OpenAI

```yaml
- uses: datarootsio/nitpick-senior@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    llm_provider: openai
    model: gpt-4o
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Anthropic

```yaml
- uses: datarootsio/nitpick-senior@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    llm_provider: anthropic
    model: claude-sonnet-4-6
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Azure OpenAI

```yaml
- uses: datarootsio/nitpick-senior@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    llm_provider: azure
    model: gpt-4o
  env:
    AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
    AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
```

### Azure Foundry — Claude

```yaml
- uses: datarootsio/nitpick-senior@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    llm_provider: azure_foundry_anthropic
    model: claude-sonnet-4-6
  env:
    AZURE_FOUNDRY_API_KEY: ${{ secrets.AZURE_FOUNDRY_API_KEY }}
    AZURE_FOUNDRY_RESOURCE: ${{ secrets.AZURE_FOUNDRY_RESOURCE }}
```

### Azure Foundry — OpenAI / Other Models

```yaml
- uses: datarootsio/nitpick-senior@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    llm_provider: azure_foundry_openai
    model: gpt-4o
  env:
    AZURE_FOUNDRY_API_KEY: ${{ secrets.AZURE_FOUNDRY_API_KEY }}
    AZURE_FOUNDRY_RESOURCE: ${{ secrets.AZURE_FOUNDRY_RESOURCE }}
```

### OpenRouter

Access 200+ models through OpenRouter's unified API:

```yaml
- uses: datarootsio/nitpick-senior@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    llm_provider: openrouter
    model: nvidia/nemotron-3-super-120b-a12b:free
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

Browse available models at [openrouter.ai/models](https://openrouter.ai/models).

## Using with GitHub Enterprise

For GitHub Enterprise Server, the action works the same way. Ensure your self-hosted runner has network access to your LLM provider.

## Inputs Reference

| Input | Default | Description |
|-------|---------|-------------|
| `github_token` | - | GitHub token for PR access |
| `llm_provider` | - | LLM provider (`openai`, `anthropic`, `google`, `azure`, `azure_foundry_anthropic`, `azure_foundry_openai`, `openrouter`) |
| `model` | - | Model name (e.g., `gpt-4o`, `claude-sonnet-4-6`) |
| `agent_spec_path` | `.github/ai-reviewer.md` | Path to agent spec file |
| `post_summary` | `true` | Post PR summary comment |
| `post_inline_comments` | `true` | Post inline code comments |
| `max_comments` | `10` | Maximum inline comments |
| `min_severity` | `warning` | Minimum severity (error, warning, info) |
| `context_enabled` | `true` | Include repo context in review |
| `context_max_tokens` | `5000` | Max tokens for context |
| `static_analysis_file` | - | Path to semgrep JSON output (see [Static Analysis](static-analysis.md)) |

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
