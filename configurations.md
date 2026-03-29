# Configurations

Both pipelines are configured through **environment variables** passed to Docker containers. The backend API also reads configurations when starting jobs.

---

## Backend API Configuration

Settings are passed per-request from the frontend. No backend config file needed.

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pipeline` | string | `fasterwhisper` | Pipeline to use (`fasterwhisper` or `whisperx`) |
| `audioFile` | string | required | Audio filename to process |
| `language` | string | `null` | Language code (null = auto-detect) |
| `minSpeakers` | number | `null` | Minimum expected speakers |
| `maxSpeakers` | number | `null` | Maximum expected speakers |

### Supported Languages

| Code | Language |
|------|----------|
| `en` | English |
| `es` | Spanish |
| `fr` | French |
| `de` | German |
| `it` | Italian |
| `pt` | Portuguese |
| `nl` | Dutch |
| `ru` | Russian |
| `zh` | Chinese |
| `ja` | Japanese |
| `ko` | Korean |
| `ar` | Arabic |
| `hi` | Hindi |
| `tr` | Turkish |
| `pl` | Polish |
| `uk` | Ukrainian |
| `vi` | Vietnamese |
| `null` | Auto-detect |

---

## Docker Pipeline Configuration

Both pipelines read configuration from environment variables in `docker-compose.yml`.

### Common Variables (Both Pipelines)

| Variable | Default | Description |
|----------|---------|-------------|
| `HUGGINGFACE_HUB_TOKEN` | required | HF token for pyannote models |
| `AUDIO_FILE` | auto-detect | Audio filename to process |
| `MIN_SPEAKERS` | `null` | Minimum speakers for diarization |
| `MAX_SPEAKERS` | `null` | Maximum speakers for diarization |

---

## Faster Whisper Pipeline

**Location**: `pipelines/fasterwhisper/`
**Script**: `run_diarization.py`

### Environment Variables (`docker-compose.yml`)

```yaml
environment:
  - HUGGINGFACE_HUB_TOKEN=${HUGGINGFACE_HUB_TOKEN}
  - AUDIO_FILE=/app/audio/yourfile.mp3
  - MIN_SPEAKERS=2
  - MAX_SPEAKERS=4
```

### Script Configuration (`run_diarization.py`)

| Setting | Location | Options |
|---------|----------|---------|
| Model size | Line ~38 | `tiny`, `base`, `small`, `medium`, `large-v1`, `large-v2`, `large-v3` |
| Device | Line ~52 | `cpu`, `cuda` |
| Compute type | Line ~52 | `int8` (CPU), `float16` (GPU), `float32` |

### Model Size Comparison

| Model | Speed | Accuracy | VRAM |
|-------|-------|----------|------|
| `tiny` | Fastest | Lowest | ~1 GB |
| `base` | Very fast | Low | ~1 GB |
| `small` | Fast | Moderate | ~2 GB |
| `medium` | Moderate | Good | ~5 GB |
| `large-v3` | Slow | Best | ~10 GB |

### GPU Support

Uncomment in `docker-compose.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

---

## WhisperX Pipeline

**Location**: `pipelines/whisperx/`
**Script**: `run_diarization.py`

### Environment Variables (`docker-compose.yml`)

```yaml
environment:
  - HUGGINGFACE_HUB_TOKEN=${HUGGINGFACE_HUB_TOKEN}
  - AUDIO_FILE=/app/audio/yourfile.mp3
  - WHISPERX_MODEL=small
  - LANGUAGE=en
  - MIN_SPEAKERS=2
  - MAX_SPEAKERS=4
```

### Additional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPERX_MODEL` | `small` | Whisper model size |
| `LANGUAGE` | auto | Language code for transcription |

### Auto-Detection

WhisperX automatically detects:
- **Device**: `cuda` if GPU available, else `cpu`
- **Compute type**: `float16` for GPU, `int8` for CPU

---

## Quick Reference

| Setting | Faster Whisper | WhisperX |
|---------|---------------|----------|
| Audio file | `docker-compose.yml` → `AUDIO_FILE` | `docker-compose.yml` → `AUDIO_FILE` |
| Model size | `run_diarization.py` → `model_size` | `docker-compose.yml` → `WHISPERX_MODEL` |
| Language | `run_diarization.py` → `language` | `docker-compose.yml` → `LANGUAGE` |
| Speakers | `docker-compose.yml` → `MIN/MAX_SPEAKERS` | `docker-compose.yml` → `MIN/MAX_SPEAKERS` |
| Device | `run_diarization.py` → `device` | Auto-detected |
| HF Token | `docker-compose.yml` or `.env` | `docker-compose.yml` or `.env` |

---

## HuggingFace Token Setup

1. Create token: https://huggingface.co/settings/tokens
2. Accept model terms:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
3. Add to `.env`:
   ```bash
   HUGGINGFACE_HUB_TOKEN=hf_your_token_here
   ```
