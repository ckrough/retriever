# ============================================
# Stage 1: Builder
# ============================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Install build dependencies for compiling C/C++ extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files and README (needed for package metadata) for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies using uv with locked versions
# --frozen: Use exact versions from uv.lock (reproducible builds)
# --no-cache: Don't cache downloads (reduces image size)
# --no-dev: Exclude development dependencies
RUN uv sync --frozen --no-cache --no-dev

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.13-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Default port (can be overridden)
    PORT=8000 \
    # Python path
    PYTHONPATH=/app

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # SQLite library for better performance
        libsqlite3-0 \
        # curl for health checks
        curl \
        # ChromaDB native dependencies
        libstdc++6 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser src/ /app/src/
COPY --chown=appuser:appuser pyproject.toml /app/

# Copy and set permissions for entrypoint script
COPY --chown=appuser:appuser entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Create data directories with proper permissions
# These will be mounted as volumes in production
RUN mkdir -p /app/data/chroma /app/documents && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Health check
# Checks if the application is responding on the configured port
# Using shell form to allow PORT variable substitution
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD sh -c 'curl -f http://localhost:${PORT:-8000}/health || exit 1'

# Expose port (documentation only, actual port set by PORT env var)
EXPOSE 8000

# Start command using entrypoint script
# The entrypoint script uses 'exec' to ensure uvicorn receives signals directly
# This enables proper SIGTERM handling for graceful shutdowns
CMD ["/app/entrypoint.sh"]
