FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for C/C++ extensions (XGBoost, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY . .

# Set default environment variables for production container
ENV PORT=8080
ENV ENVIRONMENT=production
ENV DEBUG=False

EXPOSE 8080

# Start Uvicorn bound to 0.0.0.0 and PORT environment variable
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
