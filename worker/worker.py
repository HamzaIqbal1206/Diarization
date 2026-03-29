"""
Persistent Diarization Worker
- Loads model ONCE on startup
- Processes multiple files in parallel
- Keeps model in memory for fast processing
"""

import asyncio
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

app = FastAPI(title="Diarization Worker")

# Global model instances (loaded once)
whisper_model = None
diarization_pipeline = None
model_lock = asyncio.Lock()

# Results storage
results_dir = Path(os.environ.get("RESULTS_DIR", "/app/results"))
results_dir.mkdir(parents=True, exist_ok=True)

# Job status tracking
jobs = {}


def load_models():
    """Load models once on startup."""
    global whisper_model, diarization_pipeline

    print("Loading Whisper model...")
    model_size = os.environ.get("MODEL_SIZE", "small")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
    print(f"Whisper model loaded on {device}")

    # Load diarization pipeline
    hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if hf_token:
        print("Loading pyannote diarization pipeline...")
        try:
            diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token
            )
            if device == "cuda":
                diarization_pipeline = diarization_pipeline.to(torch.device("cuda"))
            print("Diarization pipeline loaded!")
        except Exception as e:
            print(f"Warning: Could not load diarization pipeline: {e}")
            diarization_pipeline = None
    else:
        print("Warning: No HuggingFace token, diarization disabled")


@app.on_event("startup")
async def startup_event():
    """Load models on startup."""
    load_models()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "whisper_loaded": whisper_model is not None,
        "diarization_loaded": diarization_pipeline is not None
    }


async def process_audio(
    job_id: str,
    audio_path: str,
    language: Optional[str] = None,
    min_speakers: int = 2,
    max_speakers: int = 2,
):
    """Process audio file with loaded models."""
    try:
        jobs[job_id]["status"] = "transcribing"

        # Use lock to ensure thread-safe model access
        async with model_lock:
            # Transcribe with Whisper
            segments, info = whisper_model.transcribe(
                audio_path,
                language=language,
                beam_size=5
            )
            segments_list = list(segments)

        detected_language = info.language
        print(f"[{job_id}] Transcribed {len(segments_list)} segments, language: {detected_language}")

        # Diarization
        jobs[job_id]["status"] = "diarizing"
        results = []

        if diarization_pipeline:
            async with model_lock:
                diarization = diarization_pipeline(
                    audio_path,
                    min_speakers=min_speakers,
                    max_speakers=max_speakers
                )

            # Merge transcription with diarization
            turns = list(diarization.itertracks(yield_label=True))
            for segment in segments_list:
                # Find matching speaker
                speaker = "SPEAKER_00"
                for turn, _, label in turns:
                    if turn.start <= segment.start < turn.end:
                        speaker = label
                        break

                results.append({
                    "start": segment.start,
                    "end": segment.end,
                    "speaker": speaker,
                    "text": segment.text.strip()
                })
        else:
            # No diarization, just transcription
            for segment in segments_list:
                results.append({
                    "start": segment.start,
                    "end": segment.end,
                    "speaker": "SPEAKER_00",
                    "text": segment.text.strip()
                })

        # Save result
        audio_name = Path(audio_path).stem
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        output_file = results_dir / f"{audio_name}_fasterwhisper_{timestamp}.txt"

        with open(output_file, "w") as f:
            for r in results:
                f.write(f"[{r['start']:.2f}s - {r['end']:.2f}s] {r['speaker']}\n")
                f.write(f"  {r['text']}\n\n")

        jobs[job_id] = {
            "status": "completed",
            "output_file": str(output_file),
            "segments": results,
            "transcript": open(output_file).read()
        }
        print(f"[{job_id}] Completed! Saved to {output_file}")

    except Exception as e:
        print(f"[{job_id}] Error: {e}")
        jobs[job_id] = {
            "status": "failed",
            "error": str(e)
        }


@app.post("/process")
async def process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: Optional[str] = None,
    min_speakers: int = 2,
    max_speakers: int = 2,
):
    """Submit audio file for processing."""
    import uuid
    job_id = str(uuid.uuid4())[:8]

    # Save uploaded file temporarily
    suffix = Path(file.filename).suffix
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    shutil.copyfileobj(file.file, temp_file)
    temp_file.close()

    jobs[job_id] = {"status": "queued"}

    # Process in background
    background_tasks.add_task(
        process_audio,
        job_id,
        temp_file.name,
        language,
        min_speakers,
        max_speakers
    )

    return {"job_id": job_id, "status": "queued"}


@app.post("/process-file")
async def process_file(
    background_tasks: BackgroundTasks,
    audio_path: str,
    language: Optional[str] = None,
    min_speakers: int = 2,
    max_speakers: int = 2,
):
    """Process audio file by path (for mounted volumes)."""
    import uuid
    job_id = str(uuid.uuid4())[:8]

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    jobs[job_id] = {"status": "queued"}

    # Process in background
    background_tasks.add_task(
        process_audio,
        job_id,
        audio_path,
        language,
        min_speakers,
        max_speakers
    )

    return {"job_id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Get job status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]
