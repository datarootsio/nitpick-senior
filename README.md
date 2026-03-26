<p align="center">
  <img src="assets/logo.png" alt="Nitpick Senior" width="150" />
</p>

<h1 align="center">Nitpick Senior</h1>

<p align="center">
  <em>Um, actually... AI-powered code review that catches what you missed</em>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#git-platforms">Git Platforms</a> •
  <a href="#llm-providers">LLM Providers</a> •
  <a href="#configuration">Configuration</a>
</p>

---

An AI-powered code reviewer that works across multiple Git platforms. It analyzes code changes and posts inline comments on issues, bugs, and best practice violations.

## Features

- **Multi-platform**: Works with GitHub, GitLab, Azure DevOps, and Bitbucket
- **Flexible LLM support**: Use OpenAI, Anthropic, Azure OpenAI directly, or access 200+ models via [OpenRouter](https://openrouter.ai)
- **Powered by Pydantic AI**: Structured outputs with automatic validation and retries
- **Language agnostic**: Review behavior is defined by an agent spec file in your repo
- **Static analysis integration**: Enrich reviews with [Semgrep findings](docs/static-analysis.md)
- **Inline comments**: Posts comments directly on problematic lines
- **PR summaries**: Generates a brief summary of the changes
- **Cost tracking**: Logs token usage and estimated costs
- **Smart filtering**: Filter comments by severity, auto-resolve outdated comments

## Quick Start

1. Create `.github/workflows/nitpick-senior.yml`:

```yaml
name: Nitpick Senior Review

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: datarootsio/github-reviewer@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          model: gpt-4o
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

2. (Optional) Create `.github/ai-reviewer.md` to customize review behavior:

```markdown
# Nitpick Senior Configuration

You are a senior code reviewer for this project.

## What to Review
- Security vulnerabilities
- Performance issues
- Logic errors
- Best practice violations

## Project Context
- This is a Python FastAPI backend
- We use SQLAlchemy for ORM

## Do NOT Comment On
- Formatting (handled by Black)
- Import ordering (handled by isort)
```

## Git Platforms

Nitpick Senior works with all major Git platforms:

| Platform | Documentation | Status |
|----------|---------------|--------|
| GitHub | [Setup Guide](docs/github.md) | Full support |
| GitLab | [Setup Guide](docs/gitlab.md) | Full support |
| Azure DevOps | [Setup Guide](docs/azure-devops.md) | Full support |
| Bitbucket | [Setup Guide](docs/bitbucket.md) | Full support |

See the [Provider Overview](docs/PROVIDERS.md) for feature comparison across platforms.

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `github_token` | Yes | - | GitHub token for API access |
| `model` | Yes | - | Model string (see [LLM Providers](#llm-providers)) |
| `agent_spec_path` | No | `.github/ai-reviewer.md` | Path to agent spec file |
| `post_summary` | No | `true` | Post PR summary comment |
| `post_inline_comments` | No | `true` | Post inline review comments |
| `max_comments` | No | `10` | Maximum inline comments to post |
| `min_severity` | No | `warning` | Minimum severity to post (error, warning, info) |
| `static_analysis_file` | No | - | Path to semgrep JSON output ([docs](docs/static-analysis.md)) |

## LLM Providers

Nitpick Senior uses [Pydantic AI](https://ai.pydantic.dev/) for LLM interactions, providing structured outputs with automatic validation.

### Direct Providers

| Provider | Model Format | Required Environment Variables |
|----------|-------------|-------------------------------|
| OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-sonnet-4-5-20250929` | `ANTHROPIC_API_KEY` |
| Azure OpenAI | `azure/gpt-4o` | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` |

### OpenRouter (200+ Models)

[OpenRouter](https://openrouter.ai) provides access to models from OpenAI, Anthropic, Google, Meta, Mistral, and many more through a single API.

| Provider | Model Format | Required Environment Variables |
|----------|-------------|-------------------------------|
| OpenRouter | `openrouter/anthropic/claude-3.5-sonnet` | `OPENROUTER_API_KEY` |

Browse available models at [openrouter.ai/models](https://openrouter.ai/models).

## Provider Examples

### OpenAI

```yaml
- uses: datarootsio/github-reviewer@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    model: gpt-4o
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Anthropic

```yaml
- uses: datarootsio/github-reviewer@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    model: anthropic/claude-sonnet-4-5-20250929
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Azure OpenAI

```yaml
- uses: datarootsio/github-reviewer@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    model: azure/gpt-4o
  env:
    AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
    AZURE_OPENAI_ENDPOINT: https://your-resource.openai.azure.com
```

### OpenRouter

Access any model through OpenRouter's unified API:

```yaml
- uses: datarootsio/github-reviewer@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    model: openrouter/anthropic/claude-3.5-sonnet
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

Popular models via OpenRouter:
- `openrouter/openai/gpt-4o` - OpenAI GPT-4o
- `openrouter/anthropic/claude-3.5-sonnet` - Anthropic Claude 3.5 Sonnet
- `openrouter/google/gemini-pro-1.5` - Google Gemini Pro
- `openrouter/meta-llama/llama-3.1-405b-instruct` - Meta Llama 3.1 405B
- `openrouter/mistralai/mistral-large` - Mistral Large

## Local Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linter
uv run ruff check src/
```
