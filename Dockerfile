FROM python:3.12-slim

# ffmpeg o‘rnatamiz
RUN apt-get update && apt-get install -y ffmpeg

# ishchi papka
WORKDIR /app

# kutubxonalarni o‘rnatamiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# kodni yuklaymiz
COPY . .

# botni ishga tushiramiz
CMD ["python", "main.py"]
