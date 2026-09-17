# EduSpark API — development & deployment image
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

COPY requirements.txt requirements-voice.txt ./
RUN pip install --no-cache-dir -r requirements-voice.txt

COPY app ./app
RUN mkdir -p /app/uploads

EXPOSE 8000

# Override with --reload in docker-compose for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
