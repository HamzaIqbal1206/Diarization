# WhisperX Pipeline

Docker-based speaker diarization using WhisperX + pyannote.

## What this folder runs

- Transcription + alignment with `whisperx`
- Speaker diarization with pyannote through WhisperX
- Output writer to `output/diarized_transcript_whisperx.txt`

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
- `output/diarized_transcript_whisperx.txt`

## Configuration

Edit `docker-compose.yml`:

- `AUDIO_FILE=/app/audio/sample2.mp3`
- `OUTPUT_FILE=/app/output/diarized_transcript_whisperx.txt`
- `WHISPERX_MODEL=small`
- `LANGUAGE=en`

To process another file:
1. Put audio in this folder.
2. Update `AUDIO_FILE`.
3. Run compose again.

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
- **Name conflict**: run `docker rm -f whisperx-diarization` and retry.
- **First run slow**: model download + alignment model download is expected.

## Security

- Never commit a real token.
- Prefer passing token at runtime via environment variable.
