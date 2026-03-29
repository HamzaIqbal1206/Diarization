# Project Structure

Quick reference for all files and folders in the Diarization project.

---

## Root Directory

```
Diarization/
├── README.md                 # Project overview and quick-start
├── configurations.md         # Configuration guide for both pipelines
├── structure.md              # This file
├── .env                      # Environment variables (not in git)
├── .gitignore                # Git ignore rules
├── docker-compose.yml        # Multi-service Docker config
├── backend/                  # FastAPI backend
├── frontend/                 # Angular web UI
├── pipelines/                # Diarization pipelines
├── data/                     # Shared audio input
└── scripts/                  # Utility scripts
```

---

## Backend (`backend/`)

FastAPI REST API that manages jobs, file uploads, and pipeline orchestration.

```
backend/
├── main.py                   # FastAPI app with all endpoints
├── requirements.txt          # Python dependencies
├── Dockerfile                # Backend container
└── data/
    └── audio/                # Uploaded audio files (mounted to Docker)
```

### Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/upload` | Upload audio file |
| `POST /api/run` | Start diarization job |
| `GET /api/jobs/{id}` | Get job status/progress |
| `GET /api/transcripts` | List completed transcripts |
| `POST /api/pause` | Pause all jobs |
| `POST /api/resume` | Resume all jobs |

---

## Frontend (`frontend/`)

Angular 17+ single-page application.

```
frontend/
├── src/
│   ├── app/
│   │   ├── app.ts            # Root component
│   │   ├── app.config.ts     # App configuration
│   │   ├── app.routes.ts     # Routing
│   │   ├── components/
│   │   │   ├── dashboard/    # Main dashboard
│   │   │   ├── upload/       # File upload component
│   │   │   ├── job-queue/    # Job queue with progress
│   │   │   └── transcript/   # Transcript viewer
│   │   └── services/
│   │       └── api.ts        # Backend API service
│   ├── index.html
│   ├── main.ts
│   └── styles.scss
├── angular.json
├── package.json
├── proxy.conf.json           # API proxy config
└── README.md
```

### Components

| Component | Purpose |
|-----------|---------|
| `dashboard` | Main orchestrator - settings, file list, job management |
| `upload` | Drag & drop audio upload |
| `job-queue` | Progress tracking, pause/resume, job status |
| `transcript` | Speaker-segmented transcript display with download |

---

## Pipelines (`pipelines/`)

Docker-based diarization pipelines.

```
pipelines/
├── fasterwhisper/
│   ├── run_diarization.py    # Main script
│   ├── docker-compose.yml    # Container config
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   ├── README.md
│   └── output/               # Generated transcripts
│
└── whisperx/
    ├── run_diarization.py
    ├── docker-compose.yml
    ├── Dockerfile
    ├── requirements.txt
    ├── .env.example
    ├── README.md
    └── output/
```

### Pipeline Differences

| Feature | Faster Whisper | WhisperX |
|---------|---------------|----------|
| Transcription | faster-whisper | whisperx |
| Alignment | Built-in | Separate alignment step |
| Model config | In Python script | Via env vars |
| GPU detection | Manual | Automatic |

---

## Data (`data/`)

Shared input directory mounted into pipeline containers.

```
data/
└── audio/                    # Place audio files here
    └── .gitkeep
```

Supported formats: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac`, `.aiff`

---

## Scripts (`scripts/`)

Utility scripts.

```
scripts/
└── clean_outputs.sh          # Delete all transcript files
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | HuggingFace token and secrets |
| `docker-compose.yml` | Multi-service orchestration |
| `frontend/proxy.conf.json` | API proxy for development |
| `pipelines/*/docker-compose.yml` | Pipeline container config |
| `pipelines/*/.env.example` | Environment template |

---

## Output Files

Transcripts are saved with timestamps:

```
pipelines/fasterwhisper/output/filename_fasterwhisper_27032026_143045.txt
pipelines/whisperx/output/filename_whisperx_27032026_143045.txt
```

Format: `{original_name}_{pipeline}_{DDMYYYY}_{HHMMSS}.txt`

---

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code |
| `parallel` | Parallel processing feature branch |
