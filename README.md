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

1. Add a CI pipeline for your platform:

<details>
<summary><strong>GitHub Actions</strong></summary>

Create `.github/workflows/nitpick-senior.yml`:

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

      - uses: datarootsio/nitpick-senior@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          llm_provider: openai
          model: gpt-4o
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

</details>

<details>
<summary><strong>GitLab CI</strong></summary>

Create `.gitlab-ci.yml`:

```yaml
nitpick-senior:
  image: python:3.12-slim
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - pip install nitpick-senior
    - nitpick-senior review
      --platform gitlab
      --project-id $CI_PROJECT_ID
      --mr-id $CI_MERGE_REQUEST_IID
      --model gpt-4o
  variables:
    OPENAI_API_KEY: $OPENAI_API_KEY
    GITLAB_TOKEN: $GITLAB_TOKEN
```

</details>

<details>
<summary><strong>Azure DevOps Pipelines</strong></summary>

Create `azure-pipelines.yml`:

```yaml
trigger: none

pr:
  branches:
    include:
      - main

pool:
  vmImage: ubuntu-latest

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.12'

  - script: |
      pip install nitpick-senior
      nitpick-senior review \
        --platform azure-devops \
        --organization $(System.CollectionUri) \
        --project $(System.TeamProject) \
        --repo $(Build.Repository.Name) \
        --pr-id $(System.PullRequest.PullRequestId) \
        --model gpt-4o
    env:
      OPENAI_API_KEY: $(OPENAI_API_KEY)
      AZURE_DEVOPS_TOKEN: $(System.AccessToken)
```

</details>

<details>
<summary><strong>Bitbucket Pipelines</strong></summary>

Create `bitbucket-pipelines.yml`:

```yaml
pipelines:
  pull-requests:
    '**':
      - step:
          name: Nitpick Senior Review
          image: python:3.12-slim
          script:
            - pip install nitpick-senior
            - nitpick-senior review
              --platform bitbucket
              --workspace $BITBUCKET_WORKSPACE
              --repo $BITBUCKET_REPO_SLUG
              --pr-id $BITBUCKET_PR_ID
              --model gpt-4o
          variables:
            OPENAI_API_KEY: $OPENAI_API_KEY
            BITBUCKET_TOKEN: $BITBUCKET_TOKEN
```

</details>

2. (Optional) Create an agent spec file to customize review behavior:

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
| `llm_provider` | Yes | - | LLM provider (see [LLM Providers](#llm-providers)) |
| `model` | Yes | - | Model name (e.g., `gpt-4o`, `claude-sonnet-4-6`) |
| `agent_spec_path` | No | `.github/ai-reviewer.md` | Path to agent spec file |
| `post_summary` | No | `true` | Post PR summary comment |
| `post_inline_comments` | No | `true` | Post inline review comments |
| `max_comments` | No | `10` | Maximum inline comments to post |
| `min_severity` | No | `warning` | Minimum severity to post (error, warning, info) |
| `static_analysis_file` | No | - | Path to semgrep JSON output ([docs](docs/static-analysis.md)) |

## LLM Providers

Nitpick Senior uses [Pydantic AI](https://ai.pydantic.dev/) for LLM interactions, providing structured outputs with automatic validation.

| Provider (`llm_provider`) | Example `model` | Required Environment Variables |
|---------------------------|-----------------|-------------------------------|
| `openai` | `gpt-4o` | `OPENAI_API_KEY` |
| `anthropic` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| `google` | `gemini-2.5-flash` | `GOOGLE_API_KEY` |
| `azure` | `gpt-4o` | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` |
| `azure_foundry_anthropic` | `claude-sonnet-4-6` | `AZURE_FOUNDRY_API_KEY`, `AZURE_FOUNDRY_RESOURCE` |
| `azure_foundry_openai` | `gpt-4o` | `AZURE_FOUNDRY_API_KEY`, `AZURE_FOUNDRY_RESOURCE` |
| `openrouter` | `nvidia/nemotron-3-super-120b-a12b:free` | `OPENROUTER_API_KEY` |

Browse OpenRouter models at [openrouter.ai/models](https://openrouter.ai/models).

## Local Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linter
uv run ruff check src/
```
