FROM python:3.11-slim-bookworm

WORKDIR /app

# Apply OS security patches then install runtime + build deps.
# curl is a runtime dependency (healthcheck); build-essential is only needed to
# compile any Python packages without wheels and is purged again below so that
# build-only packages (gcc, linux-libc-dev, ...) do not ship in the runtime image.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (better caching), then drop the
# build toolchain so the runtime image has a smaller CVE/attack surface.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Railway uses dynamic PORT)
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the application - Railway sets PORT env var dynamically
CMD ["/bin/sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
