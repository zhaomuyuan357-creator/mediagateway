FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ffmpeg for video frame extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create storage directories
RUN mkdir -p /app/storage/videos /app/storage/temp /app/storage/images

# Expose port
EXPOSE 3001

# Run application
CMD ["python", "run.py"]
