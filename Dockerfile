# Python 3.11 tanlaymiz (aiogram/old libs bilan mos bo'lishi uchun)
FROM python:3.11-slim

# build tools va ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# kutilgan fayllarni nusxalash
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Entry
CMD ["python", "main.py"]
