# Whisper Diarization with Docker

Automated speaker diarization using faster-whisper and pyannote models. Identifies speakers in audio and generates timestamped transcripts.

## Features

✅ **Fast Transcription** - Uses faster-whisper for quick, accurate speech-to-text  
✅ **Speaker Diarization** - Identifies and labels different speakers  
✅ **Docker Ready** - Reproducible environment, works on any machine  
✅ **Easy Setup** - One command to run

## Quick Start

### Prerequisites
- Docker & Docker Compose ([Install Docker](https://docs.docker.com/get-docker/))
- Hugging Face token ([Get token](https://huggingface.co/settings/tokens))

### 1. Set Up Token

Create `.env` file with your Hugging Face token:
```bash
cp .env.example .env
# Edit .env and add your token:
# HUGGINGFACE_HUB_TOKEN=hf_your_token_here
```

### 2. Run Diarization

```bash
docker-compose up
```

Results saved to `output/diarized_transcript.txt`

## Configuration

### Change Audio File

Edit `diarize_docker.py`:
```python
audio_file = "/app/audio/your_file.mp3"
```

### Model Size

In `diarize_docker.py`, change:
```python
model_size = "base"  # tiny, base, small, medium, large-v2, large-v3
```

## Project Structure

```
.
├── Dockerfile              # Container definition
├── docker-compose.yml      # Docker Compose config
├── requirements.txt        # Python dependencies
├── diarize.py             # Native Python script
├── diarize_docker.py      # Docker version
├── .env.example           # Token template
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── sample1.mp3            # Example audio (your file)
└── output/                # Generated transcripts
    └── diarized_transcript.txt
```

## Scripts

### Native Python (requires local environment)
```bash
source whisper_env/bin/activate
python diarize.py
```

### Docker (recommended)
```bash
docker-compose up
```

## Output Format

```
[0.00s - 5.00s] SPEAKER_00
Cortex reads more, it's able to deliver maybe better code.

[6.40s - 8.60s] SPEAKER_01
Can you speak to the difference is there?
```

## Troubleshooting

### "Token not found" error
- Check `.env` file has your token
- File should be: `HUGGINGFACE_HUB_TOKEN=hf_your_token_here`

### Container fails to start
```bash
docker-compose logs
```

### Low accuracy
Try larger model:
```python
model_size = "medium"  # or "large-v2"
```

## Requirements

- **Disk space**: ~2GB (for models)
- **Memory**: 4GB+ recommended
- **GPU**: Optional (CPU works fine for base model)

## Dependencies

- faster-whisper 1.0.3
- pyannote.audio 3.1.1
- torch 2.4.1
- torchaudio 2.4.1

## Performance

| Model  | Speed  | Accuracy | VRAM |
|--------|--------|----------|------|
| tiny   | Fast   | Low      | 1GB  |
| base   | Normal | Good     | 2GB  |
| small  | Slow   | Better   | 3GB  |
| medium | Slower | Great    | 5GB  |

## Security

⚠️ **IMPORTANT**: Never commit `.env` file with your token!
- Use `.env.example` as template
- Add `.env` to `.gitignore` (already done)
- Token is for GitHub only, regenerate if exposed

## Next Steps on New Laptop

1. Clone the repository
2. Copy `.env.example` to `.env`
3. Add your Hugging Face token to `.env`
4. Run `docker-compose up`

## Resources

- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper)
- [Pyannote Audio](https://github.com/pyannote/pyannote-audio)
- [Hugging Face Hub](https://huggingface.co)

## License

MIT
