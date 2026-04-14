FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv (faster than pip)
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/

# Set PYTHONPATH so imports work regardless of working directory
ENV PYTHONPATH=/app

# Use --directory to ensure uv runs from /app
ENTRYPOINT ["uv", "run", "--directory", "/app", "python", "-m", "src.main"]
