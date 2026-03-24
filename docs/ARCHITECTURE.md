# Architecture Overview

This document describes the high-level architecture of Nitpick Senior.

## Module Structure

```
src/
├── main.py              # Entry point
├── config.py            # Configuration from environment
├── constants.py         # Shared constants
├── utils/               # Shared utilities
│   ├── tokens.py        # Token estimation/truncation
│   └── env.py           # Environment variable utilities
├── providers/           # Git provider abstraction layer
│   ├── protocol.py      # GitProvider protocol definition
│   ├── base.py          # BaseProvider with common functionality
│   ├── config.py        # Provider config dataclasses
│   ├── factory.py       # Provider factory and detection
│   ├── github.py        # GitHub implementation
│   ├── gitlab.py        # GitLab implementation
│   ├── azure_devops.py  # Azure DevOps implementation
│   └── bitbucket.py     # Bitbucket implementation
├── github/              # GitHub-specific utilities (legacy)
│   ├── client.py        # PyGithub wrapper
│   └── diff.py          # Diff parsing
├── llm/                 # LLM interactions
│   ├── client.py        # Pydantic AI wrapper
│   └── response.py      # Response models
├── context/             # Repository context collection
│   ├── collector.py     # Main orchestrator
│   ├── models.py        # Context data models
│   └── extractors/      # Content extractors
│       ├── files.py     # File fetching
│       └── imports.py   # Import resolution
├── prompts/             # Prompt management
│   ├── loader.py        # Agent spec loading
│   ├── defaults.py      # Default prompts
│   └── enhanced.py      # Enhanced prompt building
└── review/              # Review orchestration
    ├── analyzer.py      # Main review flow
    ├── comments.py      # Comment posting/syncing
    └── formatters.py    # Comment formatting utilities
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│              CI/CD Trigger (GitHub, GitLab, Azure, Bitbucket)        │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  main.py                                                             │
│  - Load Config from environment                                      │
│  - Detect/create Git provider                                        │
│  - Initialize LLM client                                             │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  review/analyzer.py                                                  │
│  - Fetch PR diff via provider                                        │
│  - Collect repository context (optional)                             │
│  - Send to LLM for review                                            │
│  - Filter and validate comments                                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
┌──────────────────────┐ ┌──────────────┐ ┌────────────────────┐
│  providers/          │ │  llm/        │ │  context/          │
│  - GitHubProvider    │ │  client.py   │ │  collector.py      │
│  - GitLabProvider    │ │  - Review    │ │  - Fetch README    │
│  - AzureDevOps       │ │    via       │ │  - Resolve imports │
│  - Bitbucket         │ │  Pydantic AI │ │  - Fetch related   │
└──────────────────────┘ └──────────────┘ └────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  review/comments.py                                                  │
│  - Format comment bodies (via formatters.py)                         │
│  - Deduplicate and filter by severity                                │
│  - Sync with existing bot comments                                   │
│  - Post summary and inline comments                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Components

### Config (`src/config.py`)

Loads all configuration from CI/CD environment variables:
- `INPUT_*` variables from action inputs
- Provider-specific variables (GITHUB_*, CI_*, SYSTEM_*, BITBUCKET_*)
- Uses shared utilities from `src/utils/env.py`

### Git Providers (`src/providers/`)

Unified abstraction for multiple Git platforms:

| Provider | Class | Platforms |
|----------|-------|-----------|
| GitHub | `GitHubProvider` | GitHub, GitHub Enterprise |
| GitLab | `GitLabProvider` | GitLab.com, self-hosted |
| Azure DevOps | `AzureDevOpsProvider` | Azure Pipelines |
| Bitbucket | `BitbucketProvider` | Bitbucket Cloud |

All providers inherit from `BaseProvider` which provides:
- PR info caching (`_get_cached_pr`, `_cache_pr`)
- Standardized error handling (`_safe_api_call`)

Provider config dataclasses (`GitHubConfig`, `GitLabConfig`, etc.) enable cleaner factory usage.

### Context Collector (`src/context/collector.py`)

Gathers repository context to improve review quality:
- Fetches README for project understanding
- Extracts imports from changed files
- Resolves import paths to fetch related code

### LLM Client (`src/llm/client.py`)

Interfaces with LLMs via Pydantic AI:
- Supports multiple providers (OpenAI, Anthropic, Azure, OpenRouter)
- Returns structured `ReviewResponse` with comments
- Tracks token usage and costs

### Analyzer (`src/review/analyzer.py`)

Orchestrates the review process:
1. Fetch PR diff via provider
2. Collect repository context (if enabled)
3. Truncate content to fit token limits
4. Send to LLM for review
5. Filter comments to valid changed lines

### Comments (`src/review/comments.py`)

Handles all comment operations:
- Formats comments with severity badges (via `formatters.py`)
- Deduplicates identical comments
- Syncs with existing bot comments (edit existing, delete outdated)
- Posts summary comment with confidence score

## Extension Points

### Custom Agent Specs

Define review behavior in `.github/ai-reviewer.md`:
- What to focus on
- What to ignore
- Project-specific context

### Adding New Git Providers

1. Create provider class in `src/providers/` inheriting from `BaseProvider`
2. Implement the `GitProvider` protocol methods
3. Add config dataclass in `src/providers/config.py`
4. Register in `src/providers/factory.py`

### Adding New LLM Providers

Pydantic AI handles provider routing via OpenAI-compatible API:
1. Set the appropriate environment variables
2. Use the provider-specific model string (e.g., `openrouter/model-id`)

### Adding New Languages

To support import resolution for a new language:
1. Add extraction pattern in `context/extractors/imports.py`
2. Add extension mapping in `detect_language()`
3. Add resolution logic for local imports
