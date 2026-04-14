FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies and the package itself (creates CLI entry point)
RUN uv sync --frozen --no-dev && uv pip install --no-deps -e .

# Ensure src is importable from any working directory
ENV PYTHONPATH=/app

# Run the CLI - works from any directory
ENTRYPOINT ["/app/.venv/bin/nitpick-senior"]
