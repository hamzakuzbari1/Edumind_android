# EduSpark API development and deployment image
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    UPLOAD_DIR=/app/uploads

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ara \
    libgl1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Keep dependency installation in its own layer so source-only changes do not
# invalidate the dependency cache.
COPY requirements.txt requirements-voice.txt ./
RUN pip install --no-cache-dir -r requirements-voice.txt

# The runtime needs the application, migrations, and shared configuration.
# Local .env files are excluded by .dockerignore.
COPY . .
RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
