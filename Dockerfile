FROM python:3.11-slim

# System dependencies for building ChromaDB / onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --verbose -r requirements.txt 2>&1

# Remove build deps to keep image smaller
RUN apt-get purge -y --auto-remove build-essential gcc g++ && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN playwright install chromium --with-deps
# Copy application code
COPY api/ api/
COPY config/ config/
COPY core/ core/
COPY quality/ quality/
COPY storage/ storage/
COPY scripts/ scripts/

# Ensure data and logs directories exist (volumes mounted at runtime)
RUN mkdir -p /app/data /app/logs

# Expose API port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/api/health')" || exit 1

# Start the FastAPI server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8765"]
