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
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", str(PROJECT_ROOT / "results")))

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".aiff"}

# In-memory job store
jobs: dict[str, dict] = {}
# In-memory batch store
batches: dict[str, dict] = {}

# No queuing - just run jobs directly
# Retry runs 3 at a time
RETRY_BATCH_SIZE = 3


def read_progress(pipeline_name: str, job_id: str | None = None) -> dict | None:
    """Read progress file from the results directory."""
    if job_id:
        progress_file = RESULTS_DIR / f"progress_{job_id}.json"
    else:
        progress_file = RESULTS_DIR / f"progress_{pipeline_name}.json"
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


@app.get("/api/system-info")
def get_system_info():
    """Get system info."""
    return {
        "totalMemoryGB": 16,
        "availableMemoryGB": 8,
        "cpuCount": 8,
        "recommendedConcurrent": RETRY_BATCH_SIZE,
    }


# Pause/Resume state
is_paused = False
running_containers: dict[str, str] = {}  # job_id -> container_name


@app.post("/api/pause")
async def pause_all_jobs():
    """Pause all running jobs by pausing their Docker containers."""
    global is_paused
    is_paused = True
    logger.info("Pausing all jobs...")

    paused_count = 0
    for job_id, container_name in list(running_containers.items()):
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "pause", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode == 0:
                paused_count += 1
                logger.info(f"[Job {job_id}] Paused container {container_name}")
            else:
                logger.warning(f"[Job {job_id}] Failed to pause: {stderr.decode()}")
        except Exception as e:
            logger.error(f"[Job {job_id}] Error pausing: {e}")

    return {"status": "paused", "pausedCount": paused_count}


@app.post("/api/resume")
async def resume_all_jobs():
    """Resume all paused jobs by unpausing their Docker containers."""
    global is_paused
    is_paused = False
    logger.info("Resuming all jobs...")

    resumed_count = 0
    for job_id, container_name in list(running_containers.items()):
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "unpause", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode == 0:
                resumed_count += 1
                logger.info(f"[Job {job_id}] Resumed container {container_name}")
            else:
                logger.warning(f"[Job {job_id}] Failed to resume: {stderr.decode()}")
        except Exception as e:
            logger.error(f"[Job {job_id}] Error resuming: {e}")

    return {"status": "running", "resumedCount": resumed_count}


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
    """Start a diarization pipeline run."""
    logger.info(f"=== Starting pipeline run ===")
    logger.info(f"Config received: {config}")

    pipeline_name = config.get("pipeline", "fasterwhisper")
    audio_file = config.get("audioFile")
    language = config.get("language")
    min_speakers = config.get("minSpeakers")
    max_speakers = config.get("maxSpeakers")
    hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN", "")

    if pipeline_name not in ("fasterwhisper", "whisperx"):
        raise HTTPException(status_code=400, detail="Invalid pipeline name")

    if not audio_file:
        raise HTTPException(status_code=400, detail="audioFile is required")

    audio_path = AUDIO_DIR / audio_file
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail=f"Audio file '{audio_file}' not found")

    pipeline_dir = PIPELINES_DIR / pipeline_name
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "pipeline": pipeline_name, "audioFile": audio_file}
    logger.info(f"Created job: {job_id}")

    # Run in background with semaphore
    asyncio.create_task(_run_job(
        job_id, pipeline_dir, audio_file, language, min_speakers, max_speakers, hf_token
    ))

    return {"jobId": job_id, "status": "queued"}


async def _run_job(
    job_id: str,
    pipeline_dir: Path,
    audio_file: str,
    language: str | None,
    min_speakers: int | None,
    max_speakers: int | None,
    hf_token: str,
):
    """Run a single job - no queuing, just run it."""
    jobs[job_id]["status"] = "running"
    logger.info(f"[Job {job_id}] Started")
    await _run_docker(job_id, pipeline_dir, audio_file, language, min_speakers, max_speakers, hf_token)


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

    logger.info(f"[Job {job_id}] Starting Docker: {audio_file}")

    env = os.environ.copy()
    env["HUGGINGFACE_HUB_TOKEN"] = hf_token
    env["JOB_ID"] = job_id
    env["AUDIO_FILE"] = f"/app/audio/{audio_file}"
    if language:
        env["LANGUAGE"] = language
    if min_speakers is not None:
        env["MIN_SPEAKERS"] = str(min_speakers)
    if max_speakers is not None:
        env["MAX_SPEAKERS"] = str(max_speakers)

    cmd = [
        "docker", "compose",
        "-p", project_name,
        "-f", str(pipeline_dir / "docker-compose.yml"),
        "up", "--abort-on-container-exit", "--remove-orphans",
    ]

    try:
        # Clean up any existing containers
        check_process = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a", "--filter", f"name={project_name}", "--format", "{{.Names}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        existing, _ = await check_process.communicate()
        if existing.decode().strip():
            rm_process = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", *existing.decode().strip().split(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await rm_process.communicate()

        # Start docker compose
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(pipeline_dir),
            env=env,
        )

        # Track container for pause/resume
        await asyncio.sleep(2)
        find_process = await asyncio.create_subprocess_exec(
            "docker", "ps", "--filter", f"name={project_name}", "--format", "{{.Names}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        names, _ = await find_process.communicate()
        container_name = names.decode().strip().split('\n')[0] if names.decode().strip() else None
        if container_name:
            running_containers[job_id] = container_name

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            # Find output file in results directory
            base_name = Path(audio_file).stem
            suffix = "fasterwhisper" if "fasterwhisper" in str(pipeline_dir) else "whisperx"
            pattern = f"{base_name}_{suffix}_*.txt"
            matches = sorted(glob_module.glob(str(RESULTS_DIR / pattern)), reverse=True)
            output_file = Path(matches[0]) if matches else None

            transcript = ""
            if output_file and output_file.exists():
                transcript = output_file.read_text(encoding="utf-8")

            jobs[job_id] = {
                "status": "completed",
                "pipeline": jobs[job_id]["pipeline"],
                "audioFile": jobs[job_id]["audioFile"],
                "transcript": transcript,
                "segments": _parse_transcript(transcript),
                "outputFilename": output_file.name if output_file else f"{base_name}_transcript.txt",
            }
            logger.info(f"[Job {job_id}] Completed successfully")
        else:
            error_msg = stderr.decode("utf-8", errors="replace")[-2000:]
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = error_msg
            logger.error(f"[Job {job_id}] Failed: {error_msg[:500]}")

    except Exception as e:
        logger.exception(f"[Job {job_id}] Exception: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
    finally:
        # Cleanup
        if job_id in running_containers:
            del running_containers[job_id]
        try:
            await asyncio.create_subprocess_exec(
                "docker", "compose", "-p", project_name,
                "-f", str(pipeline_dir / "docker-compose.yml"),
                "down", "--remove-orphans",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
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
            bracket_end = line.index("]")
            time_part = line[1:bracket_end]
            speaker = line[bracket_end + 1:].strip()

            times = time_part.split(" - ")
            start = float(times[0].replace("s", ""))
            end = float(times[1].replace("s", ""))

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

    job = jobs[job_id].copy()

    if job.get("status") == "running":
        pipeline_name = job.get("pipeline", "fasterwhisper")
        job["progress"] = read_progress(pipeline_name, job_id)
    else:
        job["progress"] = None

    return job


@app.post("/api/run-batch")
async def run_batch(config: dict):
    """Start a batch diarization run for multiple files in parallel."""
    logger.info(f"=== Starting batch pipeline run ===")

    pipeline_name = config.get("pipeline", "fasterwhisper")
    audio_files = config.get("audioFiles", [])
    language = config.get("language")
    min_speakers = config.get("minSpeakers")
    max_speakers = config.get("maxSpeakers")
    hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN", "")

    if pipeline_name not in ("fasterwhisper", "whisperx"):
        raise HTTPException(status_code=400, detail="Invalid pipeline name")

    if not audio_files:
        raise HTTPException(status_code=400, detail="audioFiles is required")

    for audio_file in audio_files:
        if not (AUDIO_DIR / audio_file).exists():
            raise HTTPException(status_code=404, detail=f"Audio file '{audio_file}' not found")

    pipeline_dir = PIPELINES_DIR / pipeline_name
    batch_id = str(uuid.uuid4())

    # Create jobs
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

    batches[batch_id] = {
        "status": "running",
        "pipeline": pipeline_name,
        "total": len(audio_files),
        "completed": 0,
        "failed": 0,
        "jobs": file_job_ids,
    }

    # Run batch in background
    asyncio.create_task(_run_batch(
        batch_id, pipeline_dir, file_job_ids, language, min_speakers, max_speakers, hf_token
    ))

    logger.info(f"Batch {batch_id} started with {len(audio_files)} files")
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
):
    """Run batch jobs - no queuing, run all in parallel."""
    batch_lock = asyncio.Lock()

    async def run_one(audio_file: str, job_id: str):
        jobs[job_id]["status"] = "running"
        logger.info(f"[Batch {batch_id}] Starting {audio_file}")
        await _run_docker(job_id, pipeline_dir, audio_file, language, min_speakers, max_speakers, hf_token)

        async with batch_lock:
            if jobs[job_id]["status"] == "completed":
                batches[batch_id]["completed"] += 1
            else:
                batches[batch_id]["failed"] += 1
            _update_batch_status(batch_id)

    tasks = [run_one(f, j) for f, j in file_job_ids.items()]
    await asyncio.gather(*tasks)
    logger.info(f"[Batch {batch_id}] All jobs completed")


def _update_batch_status(batch_id: str):
    """Update batch status based on individual job statuses."""
    batch = batches.get(batch_id)
    if not batch:
        return

    total = batch["total"]
    finished = batch["completed"] + batch["failed"]

    if finished == total:
        if batch["failed"] == 0:
            batch["status"] = "completed"
        elif batch["completed"] == 0:
            batch["status"] = "failed"
        else:
            batch["status"] = "partial_failure"
        logger.info(f"[Batch {batch_id}] Status: {batch['status']}")


@app.get("/api/batch/{batch_id}")
def get_batch(batch_id: str):
    """Get the status of a batch run."""
    if batch_id not in batches:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch = batches[batch_id].copy()

    job_details = {}
    for audio_file, job_id in batch["jobs"].items():
        if job_id in jobs:
            job = jobs[job_id].copy()
            if job.get("status") == "running":
                job["progress"] = read_progress(job.get("pipeline", "fasterwhisper"), job_id)
            job_details[audio_file] = job

    batch["jobDetails"] = job_details
    return batch


@app.post("/api/retry-failed")
async def retry_failed_jobs():
    """Retry all failed jobs - runs 3 shortest files at a time."""
    logger.info("=== Retrying failed jobs ===")

    # Find all failed jobs
    failed_jobs = [
        (job_id, job_data) for job_id, job_data in jobs.items()
        if job_data.get("status") == "failed"
    ]

    if not failed_jobs:
        return {"status": "no_failed_jobs", "retried": 0}

    # Get file sizes and sort by size (smallest first)
    jobs_with_sizes = []
    for job_id, job_data in failed_jobs:
        audio_file = job_data.get("audioFile")
        audio_path = AUDIO_DIR / audio_file
        if audio_path.exists():
            file_size = audio_path.stat().st_size
            jobs_with_sizes.append((file_size, job_id, job_data))

    # Sort by size (smallest first)
    jobs_with_sizes.sort(key=lambda x: x[0])

    hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN", "")
    retried_count = 0

    # Process in batches of 3
    for i in range(0, len(jobs_with_sizes), RETRY_BATCH_SIZE):
        batch = jobs_with_sizes[i:i + RETRY_BATCH_SIZE]
        batch_tasks = []

        for file_size, job_id, job_data in batch:
            audio_file = job_data.get("audioFile")
            pipeline_name = job_data.get("pipeline", "fasterwhisper")
            pipeline_dir = PIPELINES_DIR / pipeline_name

            # Create new job for retry
            new_job_id = str(uuid.uuid4())
            jobs[new_job_id] = {
                "status": "running",
                "pipeline": pipeline_name,
                "audioFile": audio_file,
                "retryOf": job_id,
            }

            logger.info(f"[Retry] Starting {audio_file} (size: {file_size})")
            retried_count += 1

            # Run in parallel within this batch
            task = _run_docker(
                new_job_id, pipeline_dir, audio_file,
                None, None, None, hf_token
            )
            batch_tasks.append(task)

        # Wait for this batch of 3 to complete before starting next batch
        await asyncio.gather(*batch_tasks)

    logger.info(f"Retry complete: {retried_count} jobs retried")
    return {"status": "retried", "retried": retried_count}


@app.get("/api/transcripts")
def list_transcripts():
    """List all existing transcript files from results directory."""
    results = []
    if RESULTS_DIR.exists():
        for f in sorted(RESULTS_DIR.iterdir(), key=lambda x: x.name, reverse=True):
            if f.suffix == ".txt" and f.name != ".gitkeep":
                # Determine pipeline from filename
                pipeline = "fasterwhisper" if "fasterwhisper" in f.name else "whisperx"
                results.append({"pipeline": pipeline, "filename": f.name})
    return {"transcripts": results}


@app.get("/api/transcripts/{pipeline}/{filename}")
def get_transcript(pipeline: str, filename: str):
    """Read a specific transcript file from results directory."""
    if pipeline not in ("fasterwhisper", "whisperx"):
        raise HTTPException(status_code=400, detail="Invalid pipeline")

    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = RESULTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found")

    text = file_path.read_text(encoding="utf-8")
    return {
        "pipeline": pipeline,
        "filename": filename,
        "transcript": text,
        "segments": _parse_transcript(text),
    }
