# Diarization

A web-based speaker diarization application that transcribes audio files and identifies speakers using state-of-the-art AI models.

**Author**: Mohammad Hamza Iqbal
**Supervisor**: Marko Milokovic

## Features

- **Two pipeline options**: Faster-Whisper + pyannote or WhisperX + pyannote
- **Web UI**: Upload audio, configure settings, and view transcripts
- **Speaker detection**: Automatically identify and label different speakers
- **Configurable speaker range**: Set min/max speakers for better accuracy
- **Real-time progress**: Progress bar with time estimation during processing
- **Download transcripts**: Save results as .txt files

## Overview

End-to-end speaker diarization app with:
- `backend/` FastAPI API
- `frontend/` Angular UI
- `pipelines/fasterwhisper/` Faster-Whisper + pyannote
- `pipelines/whisperx/` WhisperX + pyannote

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.10+) |
| Frontend | Angular |
| Transcription | Faster-Whisper / WhisperX |
| Diarization | pyannote.audio |

## Prerequisites

- Python 3.10+
- Node.js + npm
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

## Run with Docker (Recommended)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:4200 |
| Backend API | http://localhost:8000 |

To stop:

```bash
docker compose down
```

## Usage

1. **Upload audio** - Drag & drop or click to browse (mp3, wav, m4a, flac, ogg, aac, aiff)
2. **Select pipeline** - Choose Faster-Whisper or WhisperX
3. **Set speaker range** - Configure min/max expected speakers
4. **Run diarization** - Click the button and wait for processing
5. **View results** - Transcript with speaker labels appears in the right panel
6. **Download** - Click the download button to save the transcript

## Output Files

Transcripts are saved with timestamps to preserve history:

```
pipelines/fasterwhisper/output/audiofile_fasterwhisper_26032026_143045.txt
pipelines/whisperx/output/audiofile_whisperx_26032026_143045.txt
```

Format: `filename_pipeline_DDMYYYY_HHMMSS.txt`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Frontend changes not showing | Restart: `docker compose down && docker compose up --build` |
| Diarization fails immediately | Verify `HUGGINGFACE_HUB_TOKEN` is set correctly in `.env` |
| Model access denied | Accept terms for pyannote models on Hugging Face |

## Security

- Never commit your `.env` file or tokens
- `.env` is already in `.gitignore`
