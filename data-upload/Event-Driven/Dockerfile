# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the watcher
COPY watcher.py .

# Create folders (also created at runtime, but good to have in image)
RUN mkdir -p /app/source /app/logs

# Default config — override with docker run -e
ENV SOURCE_FOLDER=/app/source
ENV BUCKET_NAME=upload_onprem_files
ENV GCS_PREFIX=landing
ENV LOG_FILE=/app/logs/upload_log.txt

CMD ["python", "watcher.py"]