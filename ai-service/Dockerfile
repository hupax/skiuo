# Python AI Service with Qwen-VL-Max
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 python && \
    useradd -u 1000 -g python -s /bin/bash -m python

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create directories for generated protobuf
RUN mkdir -p /app/app/generated/proto && \
    chown -R python:python /app

# Copy protobuf files and generate Python code
COPY --chown=python:python ../proto /proto
RUN python -m grpc_tools.protoc \
    -I/proto \
    --python_out=/app/app/generated \
    --grpc_python_out=/app/app/generated \
    /proto/analysis.proto && \
    touch /app/app/generated/__init__.py && \
    touch /app/app/generated/proto/__init__.py && \
    chown -R python:python /app/app/generated

# Copy application code
COPY --chown=python:python app ./app

# Switch to non-root user
USER python:python

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application with production settings
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--log-level", "info", \
     "--access-log", \
     "--no-use-colors"]
