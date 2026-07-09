FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Upgrade pip first and install with verbose error reporting
RUN pip install --upgrade pip setuptools wheel
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt || { cat /tmp/pip-error.log; exit 1; }

COPY . .

# Change ownership of app directory to non-root user
RUN chown -R appuser:appuser /app

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
