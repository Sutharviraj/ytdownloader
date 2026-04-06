FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 10000

# Start the application
CMD gunicorn app:app --bind 0.0.0.0:$PORT
