# Docker Setup for Whisper Diarization

## Prerequisites
- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed (included with Docker Desktop)

## Quick Start

### 1. Build the Docker Image
```bash
docker-compose build
```

### 2. Run Diarization
```bash
docker-compose up
```

The results will be saved in the `output/` directory.

## Manual Docker Commands

### Build Image
```bash
docker build -t whisper-diarization .
```

### Run Container
```bash
docker run --rm \
  -v $(pwd):/app/audio:ro \
  -v $(pwd)/output:/app/output \
  -e HUGGINGFACE_HUB_TOKEN="hf_your_token_here" \
  whisper-diarization
```

### Interactive Mode (for debugging)
```bash
docker run -it --rm \
  -v $(pwd):/app/audio \
  -v $(pwd)/output:/app/output \
  -e HUGGINGFACE_HUB_TOKEN="hf_your_token_here" \
  whisper-diarization \
  /bin/bash
```

## Configuration

### Change Audio File
Edit `docker-compose.yml`:
```yaml
environment:
  - AUDIO_FILE=/app/audio/your_file.mp3
```

Or modify the script directly in `diarize_docker.py`.

### Environment Variables
- `HUGGINGFACE_HUB_TOKEN` - Your HF token (set in `.env` file)
- `AUDIO_FILE` - Path to audio file (default: `/app/audio/sample1.mp3`)

### GPU Support (NVIDIA)
Uncomment the GPU section in `docker-compose.yml`:
```yaml
runtime: nvidia
environment:
  - NVIDIA_VISIBLE_DEVICES=all
```

Also update `diarize_docker.py`:
```python
model = WhisperModel(model_size, device="cuda", compute_type="float16")
```

## Directory Structure
```
.
├── Dockerfile              # Container definition
├── docker-compose.yml      # Docker Compose config
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (HF token)
├── diarize_docker.py       # Main script (Docker version)
├── sample1.mp3            # Your audio file
└── output/                # Generated transcripts
    └── diarized_transcript.txt
```

## Troubleshooting

### "Permission denied" errors
```bash
mkdir -p output
chmod 755 output
```

### Container exits immediately
Check logs:
```bash
docker-compose logs
```

### Out of memory
Reduce model size in `diarize_docker.py`:
```python
model_size = "tiny"  # or "base"
```

### Token not working
Verify `.env` file:
```bash
cat .env
```

## Cleanup

Remove container:
```bash
docker-compose down
```

Remove image:
```bash
docker rmi whisper-diarization
```

Clean all Docker artifacts:
```bash
docker system prune -a
```

## Advantages of Docker

✅ **Isolated environment** - No conflicts with system packages  
✅ **Reproducible** - Same environment everywhere  
✅ **Easy deployment** - Share the Dockerfile with anyone  
✅ **Clean system** - No virtual envs cluttering your Desktop  
✅ **Portable** - Run on any machine with Docker  

## Next Steps

1. Place audio files in the project directory
2. Run `docker-compose up`
3. Check `output/diarized_transcript.txt` for results
