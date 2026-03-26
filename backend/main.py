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
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/diarization_backend.log", mode='a'),
    ],
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
PROJECT_ROOT = BASE_DIR.parent  # Go up from backend/ to project root
AUDIO_DIR = Path(os.environ.get("AUDIO_DIR", str(BASE_DIR / "data" / "audio")))
PIPELINES_DIR = Path(os.environ.get("PIPELINES_DIR", str(PROJECT_ROOT / "pipelines")))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(PROJECT_ROOT / "pipelines")))

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".aiff"}

# In-memory job store
jobs: dict[str, dict] = {}
# In-memory batch store
batches: dict[str, dict] = {}


def read_progress(pipeline_name: str, job_id: str | None = None) -> dict | None:
    """Read progress file from the pipeline's output directory."""
    if job_id:
        progress_file = PIPELINES_DIR / pipeline_name / "output" / f"progress_{job_id}.json"
    else:
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
    project_name = f"diarize_{job_id[:8]}"

    logger.info(f"[Job {job_id}] ========== STARTING DOCKER EXECUTION ==========")
    logger.info(f"[Job {job_id}] Project name: {project_name}")
    logger.info(f"[Job {job_id}] Pipeline dir: {pipeline_dir}")
    logger.info(f"[Job {job_id}] Audio file: {audio_file}")
    logger.info(f"[Job {job_id}] Language: {language}")
    logger.info(f"[Job {job_id}] Min/Max speakers: {min_speakers}/{max_speakers}")

    env = os.environ.copy()
    env["HUGGINGFACE_HUB_TOKEN"] = hf_token
    env["JOB_ID"] = job_id  # For unique progress file tracking

    cmd = [
        "docker", "compose",
        "-p", project_name,
        "-f", str(pipeline_dir / "docker-compose.yml"),
        "up", "--abort-on-container-exit", "--remove-orphans",
    ]

    # Override environment variables via docker compose
    env["AUDIO_FILE"] = f"/app/audio/{audio_file}"
    if language:
        env["LANGUAGE"] = language
    if min_speakers is not None:
        env["MIN_SPEAKERS"] = str(min_speakers)
    if max_speakers is not None:
        env["MAX_SPEAKERS"] = str(max_speakers)

    logger.info(f"[Job {job_id}] Full command: {' '.join(cmd)}")
    logger.info(f"[Job {job_id}] Working directory: {pipeline_dir}")

    # Log all environment variables being passed
    logger.info(f"[Job {job_id}] Environment variables:")
    for key in ["AUDIO_FILE", "LANGUAGE", "MIN_SPEAKERS", "MAX_SPEAKERS", "JOB_ID"]:
        if key in env:
            logger.info(f"[Job {job_id}]   {key}={env[key]}")

    try:
        # First, check if any containers with this project name already exist
        check_cmd = ["docker", "ps", "-a", "--filter", f"name={project_name}", "--format", "{{.Names}}"]
        check_process = await asyncio.create_subprocess_exec(
            *check_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        existing_containers, _ = await check_process.communicate()
        if existing_containers.decode().strip():
            logger.warning(f"[Job {job_id}] Existing containers found: {existing_containers.decode().strip()}")
            # Remove them
            logger.info(f"[Job {job_id}] Removing existing containers...")
            rm_process = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f",
                *existing_containers.decode().strip().split(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await rm_process.communicate()

        logger.info(f"[Job {job_id}] Starting docker compose up...")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(pipeline_dir),
            env=env,
        )
        logger.info(f"[Job {job_id}] Docker process PID: {process.pid}")
        stdout, stderr = await process.communicate()

        logger.info(f"[Job {job_id}] Docker process finished with return code: {process.returncode}")

        if stdout:
            stdout_text = stdout.decode('utf-8', errors='replace')
            logger.info(f"[Job {job_id}] Docker stdout:\n{stdout_text}")
        if stderr:
            stderr_text = stderr.decode('utf-8', errors='replace')
            logger.warning(f"[Job {job_id}] Docker stderr:\n{stderr_text}")

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
    finally:
        # Clean up docker containers
        cleanup_cmd = [
            "docker", "compose",
            "-p", f"diarize_{job_id[:8]}",
            "-f", str(pipeline_dir / "docker-compose.yml"),
            "down", "--remove-orphans",
        ]
        try:
            await asyncio.create_subprocess_exec(
                *cleanup_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=str(pipeline_dir),
            )
        except Exception:
            pass


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
        progress = read_progress(pipeline_name, job_id)
        job["progress"] = progress
        logger.debug(f"Job {job_id} progress: {progress}")
    else:
        # Clear progress file for completed/failed jobs
        job["progress"] = None

    logger.debug(f"Returning job {job_id} status: {job.get('status')}")
    return job


@app.post("/api/run-batch")
async def run_batch(config: dict):
    """Start a batch diarization run for multiple files in parallel.

    Expected config:
    {
        "pipeline": "fasterwhisper" | "whisperx",
        "audioFiles": ["file1.mp3", "file2.mp3", ...],
        "maxConcurrent": 2,  // optional, default 2
        "language": "en" | null,
        "minSpeakers": 2 | null,
        "maxSpeakers": 2 | null
    }
    """
    logger.info(f"=== Starting batch pipeline run ===")
    logger.info(f"Config received: {config}")

    pipeline_name = config.get("pipeline", "fasterwhisper")
    audio_files = config.get("audioFiles", [])
    max_concurrent = config.get("maxConcurrent", 2)
    language = config.get("language")
    min_speakers = config.get("minSpeakers")
    max_speakers = config.get("maxSpeakers")
    hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN", "")

    if pipeline_name not in ("fasterwhisper", "whisperx"):
        logger.error(f"Invalid pipeline name: {pipeline_name}")
        raise HTTPException(status_code=400, detail="Invalid pipeline name")

    if not audio_files:
        logger.error("No audio files specified")
        raise HTTPException(status_code=400, detail="audioFiles is required and must be non-empty")

    # Validate all files exist
    for audio_file in audio_files:
        audio_path = AUDIO_DIR / audio_file
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            raise HTTPException(status_code=404, detail=f"Audio file '{audio_file}' not found")

    pipeline_dir = PIPELINES_DIR / pipeline_name
    batch_id = str(uuid.uuid4())

    # Create individual jobs for each file
    file_job_ids = {}
    for audio_file in audio_files:
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "status": "queued",
            "pipeline": pipeline_name,
            "audioFile": audio_file,
            "batchId": batch_id,
        }
        file_job_ids[audio_file] = job_id
        logger.info(f"Created job {job_id} for file {audio_file}")

    # Store batch info
    batches[batch_id] = {
        "status": "running",
        "pipeline": pipeline_name,
        "total": len(audio_files),
        "completed": 0,
        "failed": 0,
        "jobs": file_job_ids,
    }

    # Start batch processing in background
    asyncio.create_task(
        _run_batch(
            batch_id,
            pipeline_dir,
            file_job_ids,
            language,
            min_speakers,
            max_speakers,
            hf_token,
            max_concurrent,
        )
    )

    logger.info(f"Batch {batch_id} started with {len(audio_files)} files, max concurrent: {max_concurrent}")
    return {
        "batchId": batch_id,
        "status": "running",
        "total": len(audio_files),
        "jobs": file_job_ids,
    }


async def _run_batch(
    batch_id: str,
    pipeline_dir: Path,
    file_job_ids: dict[str, str],
    language: str | None,
    min_speakers: int | None,
    max_speakers: int | None,
    hf_token: str,
    max_concurrent: int,
):
    """Run multiple Docker containers with concurrency limit."""
    from asyncio import Semaphore

    semaphore = Semaphore(max_concurrent)

    async def run_with_semaphore(audio_file: str, job_id: str):
        async with semaphore:
            # Update job status to running
            jobs[job_id]["status"] = "running"
            logger.info(f"[Batch {batch_id}] Starting job {job_id} for {audio_file}")
            await _run_docker(
                job_id, pipeline_dir, audio_file, language, min_speakers, max_speakers, hf_token
            )
            # Update batch counters
            if jobs[job_id]["status"] == "completed":
                batches[batch_id]["completed"] += 1
            else:
                batches[batch_id]["failed"] += 1
            # Update batch status
            _update_batch_status(batch_id)

    tasks = [
        run_with_semaphore(audio_file, job_id)
        for audio_file, job_id in file_job_ids.items()
    ]
    await asyncio.gather(*tasks)
    logger.info(f"[Batch {batch_id}] All jobs completed")


def _update_batch_status(batch_id: str):
    """Update batch status based on individual job statuses."""
    batch = batches.get(batch_id)
    if not batch:
        return

    total = batch["total"]
    completed = batch["completed"]
    failed = batch["failed"]
    finished = completed + failed

    if finished == total:
        if failed == 0:
            batch["status"] = "completed"
        elif completed == 0:
            batch["status"] = "failed"
        else:
            batch["status"] = "partial_failure"
        logger.info(f"[Batch {batch_id}] Status updated to: {batch['status']}")


@app.get("/api/batch/{batch_id}")
def get_batch(batch_id: str):
    """Get the status of a batch run."""
    if batch_id not in batches:
        logger.warning(f"Batch not found: {batch_id}")
        raise HTTPException(status_code=404, detail="Batch not found")

    batch = batches[batch_id].copy()

    # Include individual job details with progress
    job_details = {}
    for audio_file, job_id in batch["jobs"].items():
        if job_id in jobs:
            job = jobs[job_id].copy()
            if job.get("status") == "running":
                pipeline_name = job.get("pipeline", "fasterwhisper")
                job["progress"] = read_progress(pipeline_name, job_id)
            job_details[audio_file] = job

    batch["jobDetails"] = job_details
    return batch


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
