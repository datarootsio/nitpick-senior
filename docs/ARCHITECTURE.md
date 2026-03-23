# Architecture Overview

This document describes the high-level architecture of Nitpick Senior.

## Module Structure

```
src/
├── main.py              # Entry point
├── config.py            # Configuration from environment
├── constants.py         # Shared constants
├── utils/               # Shared utilities
│   └── tokens.py        # Token estimation/truncation
├── github/              # GitHub API interactions
│   ├── client.py        # PyGithub wrapper
│   ├── diff.py          # Diff parsing
│   └── comments.py      # Comment posting/syncing
├── llm/                 # LLM interactions
│   ├── client.py        # LiteLLM wrapper
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
    └── analyzer.py      # Main review flow
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub Action Trigger                        │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  main.py                                                             │
│  - Load Config from environment                                      │
│  - Initialize clients                                                │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  review/analyzer.py                                                  │
│  - Fetch PR diff from GitHub                                         │
│  - Collect repository context (optional)                             │
│  - Send to LLM for review                                            │
│  - Filter and validate comments                                      │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
┌──────────────────────┐ ┌──────────────┐ ┌────────────────────┐
│  github/client.py    │ │  llm/        │ │  context/          │
│  - Fetch PR diff     │ │  client.py   │ │  collector.py      │
│  - Fetch files       │ │  - Review    │ │  - Fetch README    │
│  - Post comments     │ │    via       │ │  - Resolve imports │
│                      │ │    LiteLLM   │ │  - Fetch related   │
└──────────────────────┘ └──────────────┘ └────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  github/comments.py                                                  │
│  - Format comment bodies                                             │
│  - Deduplicate and filter by severity                                │
│  - Sync with existing bot comments                                   │
│  - Post summary and inline comments                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Components

### Config (`src/config.py`)

Loads all configuration from GitHub Actions environment variables:
- `INPUT_*` variables from action.yml inputs
- `GITHUB_*` variables from the Actions runtime

### GitHub Client (`src/github/client.py`)

Wraps PyGithub with methods specific to PR review:
- Fetching PR diffs and files
- Posting review comments
- Managing existing bot comments (edit/delete)

### Context Collector (`src/context/collector.py`)

Gathers repository context to improve review quality:
- Fetches README for project understanding
- Extracts imports from changed files
- Resolves import paths to fetch related code

### LLM Client (`src/llm/client.py`)

Interfaces with LLMs via LiteLLM:
- Supports multiple providers (OpenAI, Anthropic, Azure, Bedrock, etc.)
- Returns structured `ReviewResponse` with comments
- Tracks token usage and costs

### Analyzer (`src/review/analyzer.py`)

Orchestrates the review process:
1. Fetch PR diff
2. Collect repository context (if enabled)
3. Truncate content to fit token limits
4. Send to LLM for review
5. Filter comments to valid changed lines

### Comments (`src/github/comments.py`)

Handles all comment operations:
- Formats comments with severity badges
- Deduplicates identical comments
- Syncs with existing bot comments (edit existing, delete outdated)
- Posts summary comment with confidence score

## Extension Points

### Custom Agent Specs

Define review behavior in `.github/ai-reviewer.md`:
- What to focus on
- What to ignore
- Project-specific context

### Adding New Providers

LiteLLM handles provider routing. To add a new provider:
1. Set the appropriate environment variables
2. Use the provider-specific model string (e.g., `bedrock/model-id`)

### Adding New Languages

To support import resolution for a new language:
1. Add extraction pattern in `context/extractors/imports.py`
2. Add extension mapping in `detect_language()`
3. Add resolution logic for local imports
