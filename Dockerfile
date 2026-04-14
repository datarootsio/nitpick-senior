FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies then the package itself (non-editable: copies to site-packages)
RUN uv sync --frozen --no-dev && uv pip install --no-deps .

# Run the CLI - works from any working directory
ENTRYPOINT ["/app/.venv/bin/nitpick-senior"]
