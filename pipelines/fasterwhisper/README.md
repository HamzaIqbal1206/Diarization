# FasterWhisper Pipeline

Docker-based speaker diarization using Faster-Whisper + pyannote.

## What this folder runs

- Transcription with `faster-whisper`
- Speaker diarization with `pyannote/speaker-diarization-3.1`
- Output writer to `output/<audio-name>_fasterwhisper.txt`

Main script:
- `run_diarization.py`

## Prerequisites

- Docker + Docker Compose
- Hugging Face token with accepted model terms:
    - https://huggingface.co/pyannote/speaker-diarization-3.1
    - https://huggingface.co/pyannote/segmentation-3.0

## Run

From this folder:

```bash
HUGGINGFACE_HUB_TOKEN=hf_your_token_here docker compose up --build
```

Output:
- `output/<audio-name>_fasterwhisper.txt`

## Configuration

Edit `docker-compose.yml`:

- `AUDIO_FILE=/app/audio/sample3.mp3`

To process another file:
1. Put audio in `../../data/audio/`.
2. Update `AUDIO_FILE`.
3. Run compose again.

Output naming is automatic from input audio name:
- `hamza.mp3` → `output/hamza_fasterwhisper.txt`

## Common Commands

```bash
# stop containers
docker compose down

# run in background
docker compose up --build -d

# view logs
docker compose logs -f
```

## Troubleshooting

- **Token errors**: verify `HUGGINGFACE_HUB_TOKEN` and model access on Hugging Face.
- **Name conflict**: run `docker rm -f whisper-diarization` and retry.
- **First run slow**: model download is expected.

## Security

- Never commit a real token.
- Prefer passing token at runtime via environment variable.
