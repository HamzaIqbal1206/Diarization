# Diarization

A web-based speaker diarization application that transcribes audio files and identifies speakers using state-of-the-art AI models.

**Author**: Mohammad Hamza Iqbal
**Supervisor**: Marko Milokovic

## Features

- **Two pipeline options**: Faster-Whisper + pyannote or WhisperX + pyannote
- **Web UI**: Upload audio, configure settings, and view transcripts in real-time
- **Speaker detection**: Automatically identify and label different speakers
- **Configurable speaker range**: Set min/max speakers for better accuracy
- **Language support**: 16 languages + auto-detect
- **Parallel processing**: All jobs run immediately in parallel (no queue)
- **Retry failed jobs**: One-click retry for failed jobs (3 at a time, shortest first)
- **Real-time progress**: Collective progress bar with time estimation
- **Download transcripts**: Save results as .txt files
- **Previous transcripts**: View and reload past transcripts

## Memory & Parallelism

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB+ |
| CPU | 4 cores | 8+ cores |
| Disk | 10 GB | 20 GB+ |

### Memory Usage

- **Per container**: ~2 GB RAM (with small model)
- **Model download**: ~1-2 GB per pipeline (first run only)

### Parallel Processing

Jobs run **immediately and in parallel** - there is no queue. All submitted jobs start Docker containers at the same time.

**Example**: Submitting 10 files → 10 containers start immediately

### Handling Failures

If jobs fail (typically due to memory exhaustion):

1. A **"Retry All Failed"** button appears in the job queue
2. Clicking it retries all failed jobs **3 at a time**
3. Files are sorted by size (smallest first) to maximize success rate

### Adjusting Concurrency

To limit concurrent jobs, edit `backend/main.py`:

```python
# Around line 49-50, add:
MAX_CONCURRENT_JOBS = 3  # Change this number
job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

# Then in _run_job function, wrap with:
async with job_semaphore:
    # ... existing code ...
```

**Recommended limits based on RAM:**

| Available RAM | Max Concurrent |
|---------------|----------------|
| 8 GB | 2-3 jobs |
| 16 GB | 4-6 jobs |
| 32 GB | 8-12 jobs |

## Overview

```
Diarization/
├── backend/                    # FastAPI backend
├── frontend/                   # Angular web UI
├── pipelines/
│   ├── fasterwhisper/          # Faster-Whisper + pyannote pipeline
│   └── whisperx/               # WhisperX + pyannote pipeline
├── data/audio/                 # Shared audio input directory
└── scripts/                    # Utility scripts
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.10+) |
| Frontend | Angular 17+ |
| Transcription | Faster-Whisper / WhisperX |
| Diarization | pyannote.audio 3.1 |
| Containerization | Docker + Docker Compose |

## Prerequisites

- Python 3.10+
- Node.js 18+ & npm
- Docker Desktop
- Hugging Face token with access to:
  - `pyannote/speaker-diarization-3.1`
  - `pyannote/segmentation-3.0`

## Setup

1. Create `.env` file in project root:

```bash
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
```

2. Accept model terms on Hugging Face:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0

3. Install backend dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

4. Install frontend dependencies:

```bash
cd frontend
npm install
```

## Running the Application

### Option 1: Run Services Individually (Development)

**Terminal 1 - Backend:**
```bash
source .venv/bin/activate
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend && ng serve
```

### Option 2: Docker Compose (Production)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:4200 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

To stop:
```bash
docker compose down
```

## Usage

1. **Upload audio** - Drag & drop or click to browse
   - Supported formats: mp3, wav, m4a, flac, ogg, aac, aiff
   - Multiple files allowed

2. **Configure settings**
   - Select pipeline: Faster-Whisper or WhisperX
   - Set language (or auto-detect)
   - Set min/max speakers

3. **Add files** - Click "Add" or "Add All Files"
   - Jobs start **immediately** (no queue)
   - All jobs run in parallel

4. **Monitor progress** - View collective progress bar and individual job status

5. **If jobs fail** - Click "Retry All Failed" button
   - Retries 3 jobs at a time
   - Shortest files processed first

6. **View results** - Click "View" on completed jobs to see transcripts

7. **Download** - Save transcripts as .txt files

8. **Access history** - View previous transcripts from the right panel

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/audio-files` | List uploaded audio files |
| POST | `/api/upload` | Upload audio file |
| POST | `/api/run` | Start diarization job |
| GET | `/api/jobs/{id}` | Get job status/progress |
| POST | `/api/run-batch` | Start batch processing |
| GET | `/api/batch/{id}` | Get batch status |
| POST | `/api/retry-failed` | Retry all failed jobs (3 at a time) |
| GET | `/api/transcripts` | List all transcripts |
| GET | `/api/transcripts/{pipeline}/{filename}` | Get specific transcript |
| POST | `/api/pause` | Pause all jobs |
| POST | `/api/resume` | Resume all jobs |
| GET | `/api/system-info` | Get system resources |

## Output Files

Transcripts are saved with timestamps:

```
pipelines/fasterwhisper/output/audiofile_fasterwhisper_27032026_143045.txt
pipelines/whisperx/output/audiofile_whisperx_27032026_143045.txt
```

Format: `filename_pipeline_DDMYYYY_HHMMSS.txt`

## Documentation

- [Configuration Guide](configurations.md) - All tuneable parameters
- [Project Structure](structure.md) - File and folder map

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Jobs fail with memory error | Reduce concurrent jobs or add semaphore (see Memory & Parallelism section) |
| Frontend changes not showing | Restart: `docker compose down && docker compose up --build` |
| Diarization fails immediately | Verify `HUGGINGFACE_HUB_TOKEN` is set correctly in `.env` |
| Model access denied | Accept terms for pyannote models on Hugging Face |
| Container name conflict | Run `docker rm -f <container-name>` and retry |
| First run slow | Model download is expected (1-2 GB) |
| Too many containers running | System has no limit - submit fewer files at once if needed |

## Security

- Never commit your `.env` file or tokens
- `.env` is already in `.gitignore`
- Pass HuggingFace token via environment variable, not hardcoded

## License

This project is for educational purposes. Ensure you comply with the licenses of:
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper)
- [WhisperX](https://github.com/m-bain/whisperX)
- [pyannote.audio](https://github.com/pyannote/pyannote-audio)
