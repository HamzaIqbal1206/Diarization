# Diarization Workspace

This repository contains two Docker-based diarization pipelines:

- `pipelines/fasterwhisper/` — Faster-Whisper + pyannote
- `pipelines/whisperx/` — WhisperX + pyannote

Both pipelines run on CPU by default, require a Hugging Face token for diarization, and write transcripts to their own local `output/` folders.

## Project Overview

- **Backend:** FastAPI service for diarization, runs at http://localhost:8000
- **Frontend:** Diarization web app, runs at http://localhost:4200

## Project Structure

```text
.  
├── data/  
│   └── audio/                   # shared input audio files  
└── pipelines/  
    ├── fasterwhisper/  
    │   ├── run_diarization.py  
    │   ├── Dockerfile  
    │   ├── docker-compose.yml  
    │   ├── requirements.txt  
    │   ├── output/  
    │   └── README.md  
    └── whisperx/  
        ├── run_diarization.py  
        ├── Dockerfile  
        ├── docker-compose.yml  
        ├── requirements.txt  
        ├── output/  
        └── README.md  
```

## Prerequisites

- Docker Desktop (or Docker Engine + Compose)
- Hugging Face token with access to pyannote models:
    - https://huggingface.co/pyannote/speaker-diarization-3.1
    - https://huggingface.co/pyannote/segmentation-3.0

## How to Run the Full Project

1. Make sure Docker is installed and running.
2. Set your Hugging Face token (replace with your actual token):

```bash
export HUGGINGFACE_HUB_TOKEN=hf_your_token_here
```

3. Start both backend and frontend using Docker Compose from the project root:

```bash
docker compose up --build
```

- Backend will be available at http://localhost:8000
- Frontend will be available at http://localhost:4200

## Frontend
- The web interface lets you upload audio files and view diarization results.
- If you want to run the frontend in development mode:

```bash
cd frontend
npm install
npm start
```

Then open http://localhost:4200 in your browser.

## Backend
- Handles API requests and runs diarization jobs using Docker.
- You can test the API directly at http://localhost:8000/docs

## Quick Start

**Important:** Before running a new diarization job, delete old transcript files from `pipelines/fasterwhisper/output` and `pipelines/whisperx/output` to avoid stale results. You can use:

```bash
rm pipelines/fasterwhisper/output/*.txt pipelines/whisperx/output/*.txt
```

This ensures the backend creates fresh outputs and updates job status correctly.

1) Put your audio file in `data/audio/`.

2) Run Faster-Whisper pipeline:

```bash
cd pipelines/fasterwhisper
HUGGINGFACE_HUB_TOKEN=hf_your_token_here docker compose up --build
```

Output: `pipelines/fasterwhisper/output/<audio-name>_fasterwhisper.txt`

3) Run WhisperX pipeline:

```bash
cd pipelines/whisperx
HUGGINGFACE_HUB_TOKEN=hf_your_token_here docker compose up --build
```

Output: `pipelines/whisperx/output/<audio-name>_whisperx.txt`

## Changing Input Audio

In each pipeline `docker-compose.yml`, set:

- `AUDIO_FILE=/app/audio/<your-audio-file>`

Then place that file in `data/audio/`.

## Useful Commands

From inside either pipeline folder:

```bash
docker compose down
docker compose up --build -d
docker compose logs -f
```

## Security

- Never commit real tokens.
- Prefer runtime environment variables (`HUGGINGFACE_HUB_TOKEN=...`).
