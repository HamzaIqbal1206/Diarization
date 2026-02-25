# Use official Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY diarize_docker.py diarize.py

# Create output directory
RUN mkdir -p /app/output

# Set environment variable for Hugging Face token
ENV HUGGINGFACE_HUB_TOKEN=""

# Run the application
CMD ["python", "diarize.py"]
