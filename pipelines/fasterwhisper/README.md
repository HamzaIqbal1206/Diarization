# Faster Whisper Pipeline

Docker-based speaker diarization using Faster-Whisper + pyannote.

## What This Pipeline Does

1. **Transcription**: Converts speech to text using Faster-Whisper
2. **Diarization**: Identifies speakers using pyannote.audio
3. **Output**: Generates timestamped transcript with speaker labels

## Files

```
pipelines/fasterwhisper/
├── run_diarization.py    # Main script
├── docker-compose.yml    # Container configuration
├── Dockerfile            # Python 3.9-slim with ffmpeg
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
├── README.md             # This file
└── output/               # Generated transcripts
```

## Prerequisites

- Docker + Docker Compose
- Hugging Face token with accepted model terms:
  - https://huggingface.co/pyannote/speaker-diarization-3.1
  - https://huggingface.co/pyannote/segmentation-3.0

## Quick Start

From project root:

```bash
cd pipelines/fasterwhisper
HUGGINGFACE_HUB_TOKEN=hf_your_token docker compose up --build
```

Or with `.env` file in project root:

```bash
docker compose up --build
```

## Output

Transcripts are saved to:

```
output/<audio-name>_fasterwhisper_DDMYYYY_HHMMSS.txt
```

Example output format:

```
[00:00:00 - 00:00:05] SPEAKER_01: Hello, how are you today?
[00:00:06 - 00:00:10] SPEAKER_02: I'm doing great, thanks for asking!
```

## Configuration

### Environment Variables (`docker-compose.yml`)

| Variable | Default | Description |
|----------|---------|-------------|
| `HUGGINGFACE_HUB_TOKEN` | required | Your HF token |
| `AUDIO_FILE` | auto | Audio filename to process |
| `MIN_SPEAKERS` | null | Minimum speakers |
| `MAX_SPEAKERS` | null | Maximum speakers |

### Script Settings (`run_diarization.py`)

Edit these directly in the script:

| Setting | Line | Default | Options |
|---------|------|---------|---------|
| `model_size` | ~38 | `medium` | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `device` | ~52 | `cpu` | `cpu`, `cuda` |
| `compute_type` | ~52 | `int8` | `int8`, `float16`, `float32` |

### Model Sizes

| Model | Speed | Accuracy | Memory |
|-------|-------|----------|--------|
| tiny | Fastest | Lowest | ~1 GB |
| base | Very fast | Low | ~1 GB |
| small | Fast | Moderate | ~2 GB |
| medium | Moderate | Good | ~5 GB |
| large-v3 | Slow | Best | ~10 GB |

### GPU Support

Uncomment the GPU section in `docker-compose.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

Then update in `run_diarization.py`:

```python
model = WhisperModel(model_size, device="cuda", compute_type="float16")
```

## Processing Another File

1. Place audio in `data/audio/` directory
2. Update `AUDIO_FILE` in `docker-compose.yml`:
   ```yaml
   - AUDIO_FILE=/app/audio/yourfile.mp3
   ```
3. Run again:
   ```bash
   docker compose up --build
   ```

## Common Commands

```bash
# Run pipeline
docker compose up --build

# Run in background
docker compose up --build -d

# View logs
docker compose logs -f

# Stop containers
docker compose down

# Remove container (if name conflict)
docker rm -f fasterwhisper-diarization
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Token errors | Verify `HUGGINGFACE_HUB_TOKEN` is correct and model terms accepted |
| Container name conflict | Run `docker rm -f fasterwhisper-diarization` |
| First run slow | Model download is expected (1-2 GB) |
| Out of memory | Use smaller model (`tiny`, `base`, `small`) |

## Security

- Never commit your HuggingFace token
- Use `.env` file or pass token at runtime
- Token is already excluded via `.gitignore`
