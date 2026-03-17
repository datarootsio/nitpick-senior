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
  <a href="#supported-providers">Providers</a> •
  <a href="#configuration">Configuration</a>
</p>

---

A GitHub Action that automatically reviews pull requests using AI. It analyzes code changes and posts inline comments on issues, bugs, and best practice violations.

## Features

- **Multi-provider support**: Works with OpenAI, Anthropic, Azure OpenAI, AWS Bedrock, Google Vertex AI, and more via LiteLLM
- **Language agnostic**: Review behavior is defined by an agent spec file in your repo
- **Inline comments**: Posts comments directly on problematic lines with fix suggestions
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

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `github_token` | Yes | - | GitHub token for API access |
| `model` | Yes | - | LiteLLM model string |
| `agent_spec_path` | No | `.github/ai-reviewer.md` | Path to agent spec file |
| `post_summary` | No | `true` | Post PR summary comment |
| `post_inline_comments` | No | `true` | Post inline review comments |
| `max_comments` | No | `10` | Maximum inline comments to post |
| `min_severity` | No | `warning` | Minimum severity to post (error, warning, info) |
| `resolve_outdated` | No | `true` | Resolve outdated comments from previous runs |

## Supported Providers

| Provider | Model Format | Required Environment Variables |
|----------|-------------|-------------------------------|
| OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-sonnet-4-5-20250929` | `ANTHROPIC_API_KEY` |
| Azure OpenAI | `azure/gpt-4o` | `AZURE_API_KEY`, `AZURE_API_BASE` |
| AWS Bedrock | `bedrock/anthropic.claude-3-5-sonnet` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION_NAME` |
| Google Vertex | `vertex_ai/gemini-pro` | `GOOGLE_APPLICATION_CREDENTIALS` |
| Google AI Studio | `gemini/gemini-1.5-pro` | `GEMINI_API_KEY` |

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
    AZURE_API_KEY: ${{ secrets.AZURE_API_KEY }}
    AZURE_API_BASE: https://your-resource.openai.azure.com
```

### AWS Bedrock

```yaml
- uses: datarootsio/github-reviewer@v1
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    model: bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    AWS_REGION_NAME: us-east-1
```

## Local Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linter
uv run ruff check src/
```

## License

MIT
