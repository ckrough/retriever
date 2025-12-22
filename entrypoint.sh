#!/bin/sh
# Entrypoint script for proper signal handling
# The 'exec' ensures uvicorn receives signals directly (SIGTERM for graceful shutdown)

set -e

# Use PORT environment variable, default to 8000
PORT=${PORT:-8000}

# Execute uvicorn with proper signal handling
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --no-access-log
