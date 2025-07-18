FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for processing
RUN mkdir -p /tmp/processing && chmod 755 /tmp/processing

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /tmp/processing
USER appuser

# Default command
CMD ["celery", "-A", "src.celery_app", "worker", "--loglevel=info"]