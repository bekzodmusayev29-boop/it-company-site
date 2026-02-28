FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ffmpeg for yt-dlp)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Environment variables (Can be overridden in docker-compose)
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
