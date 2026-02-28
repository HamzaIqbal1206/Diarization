from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
import os
from glob import glob


def resolve_audio_file() -> str:
    configured = os.environ.get("AUDIO_FILE", "sample6.m4a")
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

# Configuration
audio_file = resolve_audio_file()
model_size = "base"  # Options: tiny, base, small, medium, large-v2, large-v3
language = "ur"  # Set to None for auto-detection

# Get Hugging Face token from environment
hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN")

print("Starting transcription with faster-whisper...")
# 1. Transcription with faster-whisper
model = WhisperModel(model_size, device="cpu", compute_type="int8")
segments, info = model.transcribe(audio_file, language=language)

# Convert generator to list to reuse
segments_list = list(segments)
print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
print(f"Transcribed {len(segments_list)} segments\n")

print("Running speaker diarization...")
# 2. Diarization with pyannote
if not hf_token:
    print("\n⚠️  WARNING: HUGGINGFACE_HUB_TOKEN not found in environment variables!")
    print("Please follow these steps:")
    print("1. Visit https://huggingface.co/settings/tokens")
    print("2. Create a token (read access is sufficient)")
    print("3. Accept the terms at https://huggingface.co/pyannote/speaker-diarization-3.1")
    print("4. Set the token: export HUGGINGFACE_HUB_TOKEN='your_token_here'")
    print("\nAttempting to continue without token...\n")

try:
    if hf_token:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )
    else:
        # Try without token (will fail for gated models)
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
except Exception as e:
    print(f"Error loading pipeline: {e}")
    print("\nFalling back to transcription-only mode...\n")
    pipeline = None

if pipeline:
    diarization = pipeline(audio_file)
    print("Diarization complete!\n")
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
for result in merged_results:
    duration = result["end"] - result["start"]
    print(f"\n[{result['start']:.2f}s - {result['end']:.2f}s] {result['speaker']}")
    print(f"  {result['text'].strip()}")

print("\n" + "=" * 80)

# Optional: Save to file
output_file = os.environ.get("OUTPUT_FILE", "diarized_transcript.txt")
with open(output_file, "w", encoding="utf-8") as f:
    for result in merged_results:
        f.write(f"[{result['start']:.2f}s - {result['end']:.2f}s] {result['speaker']}\n")
        f.write(f"{result['text'].strip()}\n\n")

print(f"\nTranscript saved to: {output_file}")