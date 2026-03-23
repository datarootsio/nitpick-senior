# Contributing to Nitpick Senior

Thank you for your interest in contributing! This guide will help you get started.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/datarootsio/github-reviewer.git
   cd github-reviewer
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Set up pre-commit hooks:
   ```bash
   uv run pre-commit install
   ```

## Running Tests

```bash
uv run pytest
```

With coverage:
```bash
uv run pytest --cov=src --cov-report=term-missing
```

## Code Style

We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting.

```bash
# Check for issues
uv run ruff check src/

# Auto-fix issues
uv run ruff check src/ --fix

# Format code
uv run ruff format src/
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, focused commits
3. Ensure all tests pass and linting is clean
4. Update documentation if needed
5. Submit a PR with a clear description

### PR Checklist

- [ ] Tests added/updated for new functionality
- [ ] Code passes `ruff check` and `ruff format`
- [ ] Documentation updated if applicable
- [ ] Commit messages are clear and descriptive

## Project Structure

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a detailed overview of the codebase.

## Testing Locally

To test the action locally against a PR:

```bash
export GITHUB_TOKEN="your-token"
export GITHUB_REPOSITORY="owner/repo"
export PR_NUMBER="123"
export INPUT_MODEL="gpt-4o"
export OPENAI_API_KEY="your-key"

uv run python -m src.main
```

## Questions?

Open an issue if you have questions or need help getting started.
