#!/bin/sh
set -e

# Use PORT environment variable if set, otherwise default to 8000
PORT=${PORT:-8000}

echo "Starting uvicorn on port $PORT"

# Start uvicorn with the configured port
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
