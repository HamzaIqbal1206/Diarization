# Diarization Workspace

This repository contains two Docker-based diarization pipelines:

- `pipelines/fasterwhisper/` — Faster-Whisper + pyannote
- `pipelines/whisperx/` — WhisperX + pyannote

Both pipelines run on CPU by default, require a Hugging Face token for diarization, and write transcripts to their own local `output/` folders.

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
