# Multi-stage build for optimized production image
FROM python:3.11-slim AS builder

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim

# Install FFmpeg for media processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set PATH to include virtual environment (must be before USER directive)
ENV PATH="/app/.venv/bin:$PATH"

# Copy uv virtual environment from builder
COPY --from=builder /build/.venv /app/.venv

WORKDIR /app

# Copy application code
COPY app/ ./app/

# Create non-root user for running the application
RUN useradd -u 1001 -r -g 0 -m -d /app -s /sbin/nologin \
    -c "Application user" appuser && \
    chown -R 1001:0 /app && \
    chmod -R g=u /app

# Switch to non-root user
USER 1001

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD /app/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["/app/.venv/bin/uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
