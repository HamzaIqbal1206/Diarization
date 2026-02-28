# Diarization Workspace

This repository contains two separate, Docker-based diarization pipelines:

- `fasterwhisper/` — Faster-Whisper + pyannote diarization
- `whisperX/` — WhisperX + pyannote diarization

Both pipelines:
- run from CPU by default,
- require a Hugging Face token for diarization,
- write transcripts to their local `output/` folder.

## Project Structure

```text
.
├── fasterwhisper/
│   ├── run_diarization.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── sample2.mp3
│   └── output/
└── whisperX/
		├── run_diarization.py
		├── Dockerfile
		├── docker-compose.yml
		├── requirements.txt
		├── sample2.mp3
		└── output/
```

## Prerequisites

- Docker Desktop (or Docker Engine + Compose)
- Hugging Face token with access to pyannote models:
	- https://huggingface.co/pyannote/speaker-diarization-3.1
	- https://huggingface.co/pyannote/segmentation-3.0

## Quick Start

### 1) Run Faster-Whisper Pipeline

```bash
cd fasterwhisper
HUGGINGFACE_HUB_TOKEN=hf_your_token_here docker compose up --build
```

Output:
- `fasterwhisper/output/diarized_transcript.txt`

### 2) Run WhisperX Pipeline

```bash
cd whisperX
HUGGINGFACE_HUB_TOKEN=hf_your_token_here docker compose up --build
```

Output:
- `whisperX/output/diarized_transcript_whisperx.txt`

## Changing Input Audio

In each folder, edit `docker-compose.yml`:

- `AUDIO_FILE=/app/audio/<your-audio-file>`

Then place that file in the same folder as the compose file.

## Useful Commands

From inside either `fasterwhisper/` or `whisperX/`:

```bash
# stop and remove containers
docker compose down

# run in background
docker compose up --build -d

# follow logs
docker compose logs -f
```

## Troubleshooting

- **Diarization not running**: token missing/invalid, or pyannote terms not accepted.
- **Container name conflict**: remove old container with
	`docker rm -f whisper-diarization` or `docker rm -f whisperx-diarization`.
- **Slow run on CPU**: expected for larger models; first run also downloads models.

## Security

- Never commit real tokens.
- Prefer environment variables (`HUGGINGFACE_HUB_TOKEN=...`) when running commands.
