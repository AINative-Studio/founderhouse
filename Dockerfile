# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security first
RUN useradd -m -u 1000 appuser

# Copy Python packages from builder to appuser's home with proper ownership
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy entrypoint script and make it executable
COPY --chown=appuser:appuser docker-entrypoint.sh /home/appuser/docker-entrypoint.sh
RUN chmod +x /home/appuser/docker-entrypoint.sh

# Copy application code with proper ownership
COPY --chown=appuser:appuser backend/ .

# Switch to non-root user
USER appuser

# Add local bin to PATH for appuser
ENV PATH=/home/appuser/.local/bin:$PATH

# Health check (use PORT env var or default to 8000)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Expose port (Railway uses dynamic ports)
EXPOSE 8000

# Run the application using entrypoint script
ENTRYPOINT ["/home/appuser/docker-entrypoint.sh"]
