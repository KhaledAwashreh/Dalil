# Dalil API — Multi-stage Docker build
# https://github.com/KhaledAwashreh/Dalil

# ---- Stage 1: Dependencies ----
FROM python:3.11-slim AS deps

WORKDIR /app

# Install only production dependencies first (cache-friendly layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Runtime ----
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application source
COPY dalil/ dalil/
COPY requirements.txt .

# Create directories for logs and auth storage
RUN mkdir -p /app/logs /app/.dalil_auth

# Environment defaults — override via docker-compose or `docker run -e`
ENV DALIL_CONFIG=""
ENV MUNINN_URL="http://muninndb:8476"
ENV MUNINN_TOKEN=""
ENV LLM_API_KEY=""
ENV LLM_BASE_URL=""
ENV LLM_MODEL="mistral"
ENV LOG_LEVEL="INFO"

EXPOSE 8000

# Health check against the /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "dalil.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
