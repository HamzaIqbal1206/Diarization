FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV AUDIO_DIR=/app/data/audio
ENV PIPELINES_DIR=/app/pipelines

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
