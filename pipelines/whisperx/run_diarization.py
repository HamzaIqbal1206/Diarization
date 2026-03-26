import os
import json
import time
from glob import glob

import torch
import whisperx


PROGRESS_FILE = "/app/output/progress.json"
_start_time = None


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

    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "stage": stage,
            "percent": percent,
            "message": message,
            "elapsed_seconds": round(elapsed),
            "remaining_seconds": round(remaining)
        }, f)


def resolve_audio_file() -> str:
    configured = os.environ.get("AUDIO_FILE", "sample2.mp3")
    candidates = [
        configured,
        os.path.join("/app/audio", configured),
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    audio_extensions = ("*.mp3", "*.wav", "*.m4a", "*.flac", "*.ogg", "*.aac", "*.aiff")
    for audio_dir in ["/app/audio", "."]:
        for ext in audio_extensions:
            matches = sorted(glob(os.path.join(audio_dir, ext)))
            if matches:
                return matches[0]

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
    return f"/app/output/{base_name}_whisperx_{timestamp}.txt"


def main() -> None:
    audio_file = resolve_audio_file()
    model_name = os.environ.get("WHISPERX_MODEL", "small")
    output_file = build_output_file(audio_file)
    language = os.environ.get("LANGUAGE") or None  # None for auto-detect
    hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    print(f"Using device: {device}, compute_type: {compute_type}")
    print(f"Transcribing: {audio_file}")

    update_progress("loading", 5, "Initializing...")
    update_progress("loading", 10, "Loading WhisperX model...")
    model = whisperx.load_model(model_name, device=device, compute_type=compute_type, language=language if language else None)
    update_progress("loading", 20, "Model loaded successfully")

    update_progress("transcribing", 25, "Loading audio file...")
    audio = whisperx.load_audio(audio_file)
    update_progress("transcribing", 30, "Transcribing audio...")

    result = model.transcribe(audio, batch_size=8)

    detected_language = result.get("language", language)
    print(f"Detected language: {detected_language}")
    update_progress("transcribing", 45, f"Detected language: {detected_language}")

    try:
        update_progress("transcribing", 50, "Aligning transcription...")
        align_model, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
        result = whisperx.align(result["segments"], align_model, metadata, audio, device, return_char_alignments=False)
        update_progress("transcribing", 55, "Alignment complete")
    except Exception as error:
        print(f"Alignment failed, continuing without alignment: {error}")

    min_speakers = int(os.environ.get("MIN_SPEAKERS")) if os.environ.get("MIN_SPEAKERS") else None
    max_speakers = int(os.environ.get("MAX_SPEAKERS")) if os.environ.get("MAX_SPEAKERS") else None

    if hf_token:
        speaker_hint = f"min_speakers={min_speakers}, max_speakers={max_speakers}" if min_speakers or max_speakers else "auto speaker detection"
        print(f"Running whisperX diarization ({speaker_hint})...")
        update_progress("diarizing", 60, "Loading diarization model...")
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
        update_progress("diarizing", 70, "Running speaker diarization...")
        diarize_kwargs = {}
        if min_speakers is not None:
            diarize_kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            diarize_kwargs["max_speakers"] = max_speakers
        diarize_segments = diarize_model(audio_file, **diarize_kwargs)
        update_progress("diarizing", 85, "Assigning speakers to segments...")
        result = whisperx.assign_word_speakers(diarize_segments, result)
        update_progress("diarizing", 90, "Diarization complete")
    else:
        print("HUGGINGFACE_HUB_TOKEN missing; continuing without speaker diarization.")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    print("=" * 80)
    print("WHISPERX DIARIZED TRANSCRIPTION")
    print("=" * 80)
    update_progress("saving", 90, "Saving transcript...")

    with open(output_file, "w", encoding="utf-8") as handle:
        for segment in result.get("segments", []):
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            speaker = segment.get("speaker", "SPEAKER")
            text = segment.get("text", "").strip()

            print(f"\n[{start:.2f}s - {end:.2f}s] {speaker}")
            print(f"  {text}")

            handle.write(f"[{start:.2f}s - {end:.2f}s] {speaker}\n")
            handle.write(f"{text}\n\n")

    print("\n" + "=" * 80)
    print(f"Transcript saved to: {output_file}")
    update_progress("saving", 100, "Complete!")


if __name__ == "__main__":
    main()
