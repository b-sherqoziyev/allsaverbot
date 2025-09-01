FROM python:3.12-slim

# ffmpeg va build-tools (gcc, musl-dev, libc-dev) o‘rnatamiz
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
