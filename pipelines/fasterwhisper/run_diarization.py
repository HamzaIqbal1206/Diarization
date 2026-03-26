from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
import os
import json
import sys
import time
from glob import glob

# Flush all output immediately
import functools
print = functools.partial(print, flush=True)

PROGRESS_FILE = "/app/output/progress.json"
_start_time = None

def log(msg: str):
    """Print with timestamp and flush."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def update_progress(stage: str, percent: int, message: str):
    """Write progress to file for backend to read."""
    global _start_time
    if _start_time is None:
        _start_time = time.time()

    elapsed = time.time() - _start_time
    # Estimate remaining time based on progress
    if percent > 0:
        estimated_total = elapsed / (percent / 100)
        remaining = estimated_total - elapsed
    else:
        remaining = 0

    log(f"Progress: {stage} ({percent}%) - {message}")
    try:
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
        with open(PROGRESS_FILE, "w") as f:
            json.dump({
                "stage": stage,
                "percent": percent,
                "message": message,
                "elapsed_seconds": round(elapsed),
                "remaining_seconds": round(remaining)
            }, f)
        log(f"Progress file written to: {PROGRESS_FILE}")
    except Exception as e:
        log(f"ERROR writing progress file: {e}")


def resolve_audio_file() -> str:
    configured = os.environ.get("AUDIO_FILE", "sample6.m4a")
    log(f"AUDIO_FILE env var: {configured}")

    candidates = [
        configured,
        os.path.join("/app/audio", configured),
    ]

    log(f"Checking audio file candidates...")
    for candidate in candidates:
        log(f"  Checking: {candidate} -> exists: {os.path.exists(candidate)}")
        if os.path.exists(candidate):
            log(f"Found audio file: {candidate}")
            return candidate

    log("No direct match, searching for any audio file...")
    audio_extensions = ("*.mp3", "*.wav", "*.m4a", "*.flac", "*.ogg", "*.aac", "*.aiff")
    for audio_dir in ["/app/audio", "."]:
        log(f"  Searching in: {audio_dir}")
        for ext in audio_extensions:
            matches = sorted(glob(os.path.join(audio_dir, ext)))
            if matches:
                log(f"  Found: {matches[0]}")
                return matches[0]

    log(f"No audio file found, returning configured: {configured}")
    return configured


def build_output_file(audio_path: str) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    audio_name = os.path.basename(audio_path)
    base_name, _ = os.path.splitext(audio_name)
    if not base_name:
        base_name = "transcript"
    # Use TZ env var for local timezone (e.g., Asia/Karachi)
    tz_name = os.environ.get("TZ", "UTC")
    try:
        tz = ZoneInfo(tz_name)
        timestamp = datetime.now(tz).strftime("%d%m%Y_%H%M%S")
    except Exception:
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
    return f"/app/output/{base_name}_fasterwhisper_{timestamp}.txt"

# Configuration
log("=" * 60)
log("FASTER-WHISPER DIARIZATION PIPELINE")
log("=" * 60)

log(f"Environment variables:")
log(f"  AUDIO_FILE: {os.environ.get('AUDIO_FILE', 'not set')}")
log(f"  LANGUAGE: {os.environ.get('LANGUAGE', 'not set')}")
log(f"  MIN_SPEAKERS: {os.environ.get('MIN_SPEAKERS', 'not set')}")
log(f"  MAX_SPEAKERS: {os.environ.get('MAX_SPEAKERS', 'not set')}")
log(f"  HUGGINGFACE_HUB_TOKEN: {'set' if os.environ.get('HUGGINGFACE_HUB_TOKEN') else 'not set'}")

audio_file = resolve_audio_file()
model_size = "medium"  # Options: tiny, base, small, medium, large-v1, large-v2, large-v3
language = os.environ.get("LANGUAGE") or None  # None for auto-detection

log(f"Resolved audio file: {audio_file}")
log(f"Model size: {model_size}")
log(f"Language: {language or 'auto-detect'}")

# Get Hugging Face token from environment
hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN")

# Speaker count hints for diarization (set via env vars, None for auto)
min_speakers = int(os.environ.get("MIN_SPEAKERS")) if os.environ.get("MIN_SPEAKERS") else None
max_speakers = int(os.environ.get("MAX_SPEAKERS")) if os.environ.get("MAX_SPEAKERS") else None

log("Starting transcription with faster-whisper...")
update_progress("loading", 5, "Loading Whisper model...")

# 1. Transcription with faster-whisper
log(f"Loading Whisper model: {model_size}")
model = WhisperModel(model_size, device="cpu", compute_type="int8")
log("Whisper model loaded successfully")
update_progress("transcribing", 10, "Transcribing audio...")

log(f"Starting transcription of: {audio_file}")
segments, info = model.transcribe(audio_file, language=language)

# Convert generator to list to reuse
log("Converting segments to list...")
segments_list = list(segments)
log(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
log(f"Transcribed {len(segments_list)} segments")
update_progress("transcribing", 40, f"Transcribed {len(segments_list)} segments")

print("Running speaker diarization...")
update_progress("diarizing", 50, "Loading diarization model...")

# 2. Diarization with pyannote
log("Initializing pyannote diarization...")
if not hf_token:
    log("WARNING: HUGGINGFACE_HUB_TOKEN not found!")
    log("Diarization requires a HuggingFace token:")
    log("  1. Visit https://huggingface.co/settings/tokens")
    log("  2. Create a read token")
    log("  3. Accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1")
    log("  4. Set HUGGINGFACE_HUB_TOKEN env var")
    log("Attempting to continue without token...")

try:
    log("Loading pyannote pipeline...")
    if hf_token:
        log("Using HF token for authentication")
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )
    else:
        log("Loading without token (may fail for gated models)")
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
    log("Pyannote pipeline loaded successfully!")
except Exception as e:
    log(f"ERROR loading diarization pipeline: {type(e).__name__}: {e}")
    log("Falling back to transcription-only mode...")
    pipeline = None

if pipeline:
    speaker_hint = f"min_speakers={min_speakers}, max_speakers={max_speakers}" if min_speakers or max_speakers else "auto speaker detection"
    print(f"Diarization with {speaker_hint}")
    update_progress("diarizing", 60, "Running speaker diarization...")
    diarization_kwargs = {}
    if min_speakers is not None:
        diarization_kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        diarization_kwargs["max_speakers"] = max_speakers
    diarization = pipeline(audio_file, **diarization_kwargs)
    print("Diarization complete!\n")
    update_progress("diarizing", 85, "Diarization complete")
else:
    diarization = None
    print("Skipping diarization (not available)\n")

# 3. Merge transcription with diarization
if diarization:
    print("Merging transcription with speaker labels...\n")
    merged_results = []
    for segment in segments_list:
        # Find the speaker who overlaps the most with this segment
        max_overlap = 0
        assigned_speaker = "UNKNOWN"
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # Calculate overlap between segment and speaker turn
            overlap_start = max(turn.start, segment.start)
            overlap_end = min(turn.end, segment.end)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > max_overlap:
                max_overlap = overlap
                assigned_speaker = speaker
        
        merged_results.append({
            "speaker": assigned_speaker,
            "text": segment.text,
            "start": segment.start,
            "end": segment.end
        })
else:
    # No diarization, just use transcription
    print("Using transcription without speaker labels...\n")
    merged_results = []
    for segment in segments_list:
        merged_results.append({
            "speaker": "SPEAKER",
            "text": segment.text,
            "start": segment.start,
            "end": segment.end
        })

# 4. Print results
print("=" * 80)
print("DIARIZED TRANSCRIPTION")
print("=" * 80)
update_progress("saving", 90, "Saving transcript...")
for result in merged_results:
    duration = result["end"] - result["start"]
    print(f"\n[{result['start']:.2f}s - {result['end']:.2f}s] {result['speaker']}")
    print(f"  {result['text'].strip()}")

print("\n" + "=" * 80)

# Save to file
output_file = build_output_file(audio_file)
os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, "w", encoding="utf-8") as f:
    for result in merged_results:
        f.write(f"[{result['start']:.2f}s - {result['end']:.2f}s] {result['speaker']}\n")
        f.write(f"{result['text'].strip()}\n\n")

print(f"\nTranscript saved to: {output_file}")
update_progress("saving", 100, "Complete!")