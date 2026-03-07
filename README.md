# Diarization Workspace

## Author

Mohammad Hamza Iqbal
Under the supervision of Marko Milokovic

End-to-end speaker diarization app with:
- `backend/` FastAPI API
- `frontend/` Angular UI
- `pipelines/fasterwhisper/` Faster-Whisper + pyannote
- `pipelines/whisperx/` WhisperX + pyannote

## Services

- Frontend: `http://localhost:4200`
- Backend: `http://localhost:8000`

## Prerequisites

- Python `3.10+`
- Node.js + npm (for local frontend run)
- Docker Desktop (for Compose run)
- Hugging Face token with access to:
1. `pyannote/speaker-diarization-3.1`
2. `pyannote/segmentation-3.0`

## Environment Setup

Create `.env` in project root:

```bash
HUGGINGFACE_HUB_TOKEN=hf_your_token_here
```

`.env` is ignored by git.

## Run with Docker Compose (Recommended)

From repo root:

```bash
docker compose up --build
```

Behavior:
- Backend runs in container on `8000`
- Frontend runs Angular dev server in container on `4200`
- Changes in `frontend/src/` hot reload automatically

Stop:

```bash
docker compose down
```

## Run Without Docker

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm start
```

## How It Works

1. Upload/select audio in UI.
2. Choose pipeline (`fasterwhisper` or `whisperx`) and speaker range.
3. Run diarization.
4. View generated transcript + segments in the right panel.

Outputs are written to:
- `pipelines/fasterwhisper/output/`
- `pipelines/whisperx/output/`

## Troubleshooting

- If frontend changes do not appear on `4200`, make sure Angular dev server is running (not static Nginx build) and restart:

```bash
docker compose down
docker compose up --build
```

- If diarization fails quickly, verify `HUGGINGFACE_HUB_TOKEN` is set in `.env`.

## Security

- Never commit real tokens.
- Keep secrets in `.env` or runtime environment variables.
