import asyncio
import glob as glob_module
import json
import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Diarization API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# When running in Docker, data/ and pipelines/ are mounted at /app/data and /app/pipelines
# BASE_DIR is /app (where main.py lives)
BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = Path(os.environ.get("AUDIO_DIR", str(BASE_DIR / "data" / "audio")))
PIPELINES_DIR = Path(os.environ.get("PIPELINES_DIR", str(BASE_DIR / "pipelines")))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(BASE_DIR / "pipelines")))

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".aiff"}

# In-memory job store
jobs: dict[str, dict] = {}


def read_progress(pipeline_name: str) -> dict | None:
    """Read progress file from the pipeline's output directory."""
    progress_file = PIPELINES_DIR / pipeline_name / "output" / "progress.json"
    logger.debug(f"Reading progress from: {progress_file}")
    if progress_file.exists():
        try:
            content = progress_file.read_text(encoding="utf-8")
            logger.debug(f"Progress file content: {content}")
            return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to parse progress file: {e}")
            return None
    logger.debug(f"Progress file does not exist: {progress_file}")
    return None


@app.get("/api/health")
def health():
    logger.info("Health check OK")
    return {"status": "ok"}


@app.get("/api/audio-files")
def list_audio_files():
    """List all audio files in the data/audio directory."""
    logger.info(f"Listing audio files from {AUDIO_DIR}")
    if not AUDIO_DIR.exists():
        logger.warning(f"Audio directory does not exist: {AUDIO_DIR}")
        return {"files": []}
    files = [
        f.name
        for f in sorted(AUDIO_DIR.iterdir())
        if f.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    logger.info(f"Found {len(files)} audio files: {files}")
    return {"files": files}


@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Upload an audio file to data/audio/."""
    logger.info(f"Uploading file: {file.filename}")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.error(f"Unsupported file type: {ext}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    dest = AUDIO_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    logger.info(f"File uploaded successfully: {dest}")
    return {"filename": file.filename}


@app.post("/api/run")
async def run_pipeline(config: dict):
    """Start a diarization pipeline run.

    Expected config:
    {
        "pipeline": "fasterwhisper" | "whisperx",
        "audioFile": "filename.mp3",
        "language": "en" | null,
        "minSpeakers": 2 | null,
        "maxSpeakers": 2 | null
    }
    """
    logger.info(f"=== Starting pipeline run ===")
    logger.info(f"Config received: {config}")

    pipeline_name = config.get("pipeline", "fasterwhisper")
    audio_file = config.get("audioFile")
    language = config.get("language")  # null for auto-detect
    min_speakers = config.get("minSpeakers")
    max_speakers = config.get("maxSpeakers")
    hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN", "")

    logger.info(f"Pipeline: {pipeline_name}, Audio: {audio_file}, Language: {language}")
    logger.info(f"Min speakers: {min_speakers}, Max speakers: {max_speakers}")
    logger.info(f"HF token present: {bool(hf_token)}")

    if pipeline_name not in ("fasterwhisper", "whisperx"):
        logger.error(f"Invalid pipeline name: {pipeline_name}")
        raise HTTPException(status_code=400, detail="Invalid pipeline name")

    if not audio_file:
        logger.error("No audio file specified")
        raise HTTPException(status_code=400, detail="audioFile is required")

    audio_path = AUDIO_DIR / audio_file
    if not audio_path.exists():
        logger.error(f"Audio file not found: {audio_path}")
        raise HTTPException(status_code=404, detail=f"Audio file '{audio_file}' not found")

    logger.info(f"Audio file exists at: {audio_path}")

    pipeline_dir = PIPELINES_DIR / pipeline_name
    logger.info(f"Pipeline directory: {pipeline_dir}")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "pipeline": pipeline_name, "audioFile": audio_file}
    logger.info(f"Created job: {job_id}")

    asyncio.create_task(_run_docker(job_id, pipeline_dir, audio_file, language, min_speakers, max_speakers, hf_token))

    logger.info(f"Pipeline task started for job {job_id}")
    return {"jobId": job_id, "status": "running"}


async def _run_docker(
    job_id: str,
    pipeline_dir: Path,
    audio_file: str,
    language: str | None,
    min_speakers: int | None,
    max_speakers: int | None,
    hf_token: str,
):
    """Run docker compose for the given pipeline."""
    logger.info(f"[Job {job_id}] Starting Docker execution")
    logger.info(f"[Job {job_id}] Pipeline dir: {pipeline_dir}")
    logger.info(f"[Job {job_id}] Audio file: {audio_file}")

    env = os.environ.copy()
    env["HUGGINGFACE_HUB_TOKEN"] = hf_token

    cmd = [
        "docker", "compose",
        "-f", str(pipeline_dir / "docker-compose.yml"),
        "up", "--build", "--abort-on-container-exit",
    ]

    # Override environment variables via docker compose
    env["AUDIO_FILE"] = f"/app/audio/{audio_file}"
    if language:
        env["LANGUAGE"] = language
        logger.info(f"[Job {job_id}] Setting LANGUAGE={language}")
    if min_speakers is not None:
        env["MIN_SPEAKERS"] = str(min_speakers)
        logger.info(f"[Job {job_id}] Setting MIN_SPEAKERS={min_speakers}")
    if max_speakers is not None:
        env["MAX_SPEAKERS"] = str(max_speakers)
        logger.info(f"[Job {job_id}] Setting MAX_SPEAKERS={max_speakers}")

    logger.info(f"[Job {job_id}] Running command: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(pipeline_dir),
            env=env,
        )
        logger.info(f"[Job {job_id}] Docker process started, waiting for completion...")
        stdout, stderr = await process.communicate()

        logger.info(f"[Job {job_id}] Docker process finished with return code: {process.returncode}")

        if stdout:
            logger.info(f"[Job {job_id}] Docker stdout:\n{stdout.decode('utf-8', errors='replace')}")
        if stderr:
            logger.warning(f"[Job {job_id}] Docker stderr:\n{stderr.decode('utf-8', errors='replace')}")

        if process.returncode == 0:
            # Read the output file
            base_name = Path(audio_file).stem
            suffix = "fasterwhisper" if "fasterwhisper" in str(pipeline_dir) else "whisperx"
            # Find the most recent output file for this audio
            output_dir = pipeline_dir / "output"
            pattern = f"{base_name}_{suffix}_*.txt"
            logger.info(f"[Job {job_id}] Looking for output files matching: {output_dir / pattern}")
            matches = sorted(glob_module.glob(str(output_dir / pattern)), reverse=True)
            output_file = Path(matches[0]) if matches else None

            if output_file:
                logger.info(f"[Job {job_id}] Found output file: {output_file}")
            else:
                logger.warning(f"[Job {job_id}] No output file found matching pattern")

            transcript = ""
            if output_file and output_file.exists():
                transcript = output_file.read_text(encoding="utf-8")
                logger.info(f"[Job {job_id}] Read transcript ({len(transcript)} chars)")

            jobs[job_id] = {
                "status": "completed",
                "pipeline": jobs[job_id]["pipeline"],
                "audioFile": jobs[job_id]["audioFile"],
                "transcript": transcript,
                "segments": _parse_transcript(transcript),
                "outputFilename": output_file.name if output_file else f"{base_name}_transcript.txt",
            }
            logger.info(f"[Job {job_id}] Job completed successfully")
        else:
            error_msg = stderr.decode("utf-8", errors="replace")[-2000:]
            logger.error(f"[Job {job_id}] Docker process failed: {error_msg}")
            jobs[job_id] = {
                "status": "failed",
                "pipeline": jobs[job_id]["pipeline"],
                "audioFile": jobs[job_id]["audioFile"],
                "error": error_msg,
            }
    except Exception as e:
        logger.exception(f"[Job {job_id}] Exception during Docker execution: {e}")
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
        logger.warning(f"Job not found: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id].copy()

    # Include progress for running jobs only
    if job.get("status") == "running":
        pipeline_name = job.get("pipeline", "fasterwhisper")
        progress = read_progress(pipeline_name)
        job["progress"] = progress
        logger.debug(f"Job {job_id} progress: {progress}")
    else:
        # Clear progress file for completed/failed jobs
        job["progress"] = None

    logger.debug(f"Returning job {job_id} status: {job.get('status')}")
    return job


@app.get("/api/transcripts")
def list_transcripts():
    """List all existing transcript files from both pipelines, newest first."""
    results = []
    for pipeline_name in ("fasterwhisper", "whisperx"):
        output_dir = PIPELINES_DIR / pipeline_name / "output"
        if output_dir.exists():
            for f in sorted(output_dir.iterdir(), key=lambda x: x.name, reverse=True):
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
