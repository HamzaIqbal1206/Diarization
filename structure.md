# Project Structure Reference

Quick map of every file and folder so you don't have to read through everything.

---

## Root

```
.
├── README.md              # Project overview, quick-start instructions
├── configurations.md      # All tuneable parameters for both pipelines
├── structure.md           # This file — project map
├── .gitignore             # Git ignore rules
├── data/
├── pipelines/
└── scripts/
```

---

## data/

Shared input directory mounted into both Docker containers.

```
data/
└── audio/            # Place audio files here (.mp3, .wav, .m4a, .flac, .ogg, .aac, .aiff)
    └── .gitkeep      # Keeps the empty folder in git
```

---

## pipelines/fasterwhisper/

Faster-Whisper + pyannote speaker diarization pipeline.

```
pipelines/fasterwhisper/
├── run_diarization.py      # Main script — transcription + diarization logic
├── Dockerfile              # Python 3.9-slim, installs ffmpeg + pip deps
├── docker-compose.yml      # Container config — env vars, volumes, command
├── requirements.txt        # faster-whisper 1.0.3, pyannote.audio 3.1.1, torch 2.4.1
├── .env.example            # Template for environment variables
├── README.md               # Pipeline-specific docs
└── output/                 # Transcripts written here (<audioname>_fasterwhisper.txt)
    └── .gitkeep
```

**Key details:**
- Model size, language, device, and compute type are set **in the Python script** (`run_diarization.py`)
- Speaker count and audio file are set **in `docker-compose.yml`** as env vars
- Runs on CPU with int8 by default

---

## pipelines/whisperx/

WhisperX + pyannote speaker diarization pipeline.

```
pipelines/whisperx/
├── run_diarization.py      # Main script — transcription, alignment, diarization
├── Dockerfile              # Python 3.10-slim, installs ffmpeg + pip deps
├── docker-compose.yml      # Container config — env vars, volumes, command
├── requirements.txt        # whisperx 3.3.1, torch 2.4.1, huggingface-hub 0.19.4
├── .env.example            # Template for environment variables
├── README.md               # Pipeline-specific docs
└── output/                 # Transcripts written here (<audioname>_whisperx.txt)
    └── .gitkeep
```

**Key details:**
- Model size, language are set **in `docker-compose.yml`** as env vars (`WHISPERX_MODEL`, `LANGUAGE`)
- Device and compute type are **auto-detected** (GPU if available, else CPU)
- Includes a word-level alignment step after transcription

---

## scripts/

Utility scripts for the project.

```
scripts/
└── clean_outputs.sh    # Deletes all .txt transcript files from both output/ folders
```

---

## Branches

- **`main`** — production branch
- **`document-branch`** — documentation and project structure work

---

## Config Locations Cheat Sheet

| Setting               | Faster Whisper                          | WhisperX                                |
|-----------------------|-----------------------------------------|-----------------------------------------|
| Audio file            | `docker-compose.yml` → `AUDIO_FILE`    | `docker-compose.yml` → `AUDIO_FILE`    |
| Model size            | `run_diarization.py` → `model_size`    | `docker-compose.yml` → `WHISPERX_MODEL`|
| Language              | `run_diarization.py` → `language`      | `docker-compose.yml` → `LANGUAGE`      |
| Min/Max speakers      | `docker-compose.yml` → env vars        | `docker-compose.yml` → env vars        |
| Device (CPU/GPU)      | `run_diarization.py` → `device`        | Auto-detected                           |
| Compute type          | `run_diarization.py` → `compute_type`  | Auto-detected                           |
| HF token              | `docker-compose.yml` or shell export   | `docker-compose.yml` or shell export   |

Full configuration docs → `configurations.md`
