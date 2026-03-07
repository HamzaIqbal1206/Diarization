import asyncio
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Diarization API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# When running locally, BASE_DIR is the repo root (parent of backend/)
# When running in Docker, data/ and pipelines/ are mounted at /app/data and /app/pipelines
BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = Path(os.environ.get("AUDIO_DIR", str(BASE_DIR / "data" / "audio")))
PIPELINES_DIR = Path(os.environ.get("PIPELINES_DIR", str(BASE_DIR / "pipelines")))

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".aiff"}

# In-memory job store
jobs: dict[str, dict] = {}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/audio-files")
def list_audio_files():
    """List all audio files in the data/audio directory."""
    if not AUDIO_DIR.exists():
        return {"files": []}
    files = [
        f.name
        for f in sorted(AUDIO_DIR.iterdir())
        if f.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    return {"files": files}


@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Upload an audio file to data/audio/."""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    dest = AUDIO_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filename": file.filename}


@app.post("/api/run")
async def run_pipeline(config: dict):
    """Start a diarization pipeline run.

    Expected config:
    {
        "pipeline": "fasterwhisper" | "whisperx",
        "audioFile": "filename.mp3",
        "minSpeakers": 2,
        "maxSpeakers": 2,
        "hfToken": "hf_..."
    }
    """
    pipeline_name = config.get("pipeline", "fasterwhisper")
    audio_file = config.get("audioFile")
    min_speakers = config.get("minSpeakers", 2)
    max_speakers = config.get("maxSpeakers", 2)
    hf_token = config.get("hfToken", "")

    if pipeline_name not in ("fasterwhisper", "whisperx"):
        raise HTTPException(status_code=400, detail="Invalid pipeline name")

    if not audio_file:
        raise HTTPException(status_code=400, detail="audioFile is required")

    audio_path = AUDIO_DIR / audio_file
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail=f"Audio file '{audio_file}' not found")

    pipeline_dir = PIPELINES_DIR / pipeline_name

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "pipeline": pipeline_name, "audioFile": audio_file}

    asyncio.create_task(_run_docker(job_id, pipeline_dir, audio_file, min_speakers, max_speakers, hf_token))

    return {"jobId": job_id, "status": "running"}


async def _run_docker(
    job_id: str,
    pipeline_dir: Path,
    audio_file: str,
    min_speakers: int,
    max_speakers: int,
    hf_token: str,
):
    """Run docker compose for the given pipeline."""
    env = os.environ.copy()
    env["HUGGINGFACE_HUB_TOKEN"] = hf_token

    cmd = [
        "docker", "compose",
        "-f", str(pipeline_dir / "docker-compose.yml"),
        "up", "--build", "--abort-on-container-exit",
    ]

    # Override environment variables via docker compose
    env["AUDIO_FILE"] = f"/app/audio/{audio_file}"
    env["MIN_SPEAKERS"] = str(min_speakers)
    env["MAX_SPEAKERS"] = str(max_speakers)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(pipeline_dir),
            env=env,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            # Read the output file
            base_name = Path(audio_file).stem
            suffix = "fasterwhisper" if "fasterwhisper" in str(pipeline_dir) else "whisperx"
            output_file = pipeline_dir / "output" / f"{base_name}_{suffix}.txt"

            transcript = ""
            if output_file.exists():
                transcript = output_file.read_text(encoding="utf-8")

            jobs[job_id] = {
                "status": "completed",
                "pipeline": jobs[job_id]["pipeline"],
                "audioFile": jobs[job_id]["audioFile"],
                "transcript": transcript,
                "segments": _parse_transcript(transcript),
            }
        else:
            jobs[job_id] = {
                "status": "failed",
                "pipeline": jobs[job_id]["pipeline"],
                "audioFile": jobs[job_id]["audioFile"],
                "error": stderr.decode("utf-8", errors="replace")[-2000:],
            }
    except Exception as e:
        jobs[job_id] = {
            "status": "failed",
            "pipeline": jobs[job_id]["pipeline"],
            "audioFile": jobs[job_id]["audioFile"],
            "error": str(e),
        }


def _parse_transcript(text: str) -> list[dict]:
    """Parse transcript text into structured segments."""
    segments = []
    lines = text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("[") and "]" in line:
            # Parse: [0.00s - 4.00s] SPEAKER_00
            bracket_end = line.index("]")
            time_part = line[1:bracket_end]
            speaker = line[bracket_end + 1:].strip()

            times = time_part.split(" - ")
            start = float(times[0].replace("s", ""))
            end = float(times[1].replace("s", ""))

            # Next line is the text
            text_content = ""
            if i + 1 < len(lines) and lines[i + 1].strip():
                text_content = lines[i + 1].strip()
                i += 1

            segments.append({
                "start": start,
                "end": end,
                "speaker": speaker,
                "text": text_content,
            })
        i += 1
    return segments


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    """Get the status/result of a pipeline run."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/api/transcripts")
def list_transcripts():
    """List all existing transcript files from both pipelines."""
    results = []
    for pipeline_name in ("fasterwhisper", "whisperx"):
        output_dir = PIPELINES_DIR / pipeline_name / "output"
        if output_dir.exists():
            for f in sorted(output_dir.iterdir()):
                if f.suffix == ".txt" and f.name != ".gitkeep":
                    results.append({
                        "pipeline": pipeline_name,
                        "filename": f.name,
                    })
    return {"transcripts": results}


@app.get("/api/transcripts/{pipeline}/{filename}")
def get_transcript(pipeline: str, filename: str):
    """Read a specific transcript file."""
    if pipeline not in ("fasterwhisper", "whisperx"):
        raise HTTPException(status_code=400, detail="Invalid pipeline")

    file_path = PIPELINES_DIR / pipeline / "output" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found")

    # Prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    text = file_path.read_text(encoding="utf-8")
    return {
        "pipeline": pipeline,
        "filename": filename,
        "transcript": text,
        "segments": _parse_transcript(text),
    }
