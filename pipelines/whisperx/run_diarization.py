import os
from glob import glob

import torch
import whisperx


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
    audio_name = os.path.basename(audio_path)
    base_name, _ = os.path.splitext(audio_name)
    if not base_name:
        base_name = "transcript"
    return f"/app/output/{base_name}_whisperx.txt"


def main() -> None:
    audio_file = resolve_audio_file()
    model_name = os.environ.get("WHISPERX_MODEL", "small")
    output_file = build_output_file(audio_file)
    language = os.environ.get("LANGUAGE", "en")
    hf_token = os.environ.get("HUGGINGFACE_HUB_TOKEN")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    print(f"Using device: {device}, compute_type: {compute_type}")
    print(f"Transcribing: {audio_file}")

    model = whisperx.load_model(model_name, device=device, compute_type=compute_type, language=language)
    audio = whisperx.load_audio(audio_file)
    result = model.transcribe(audio, batch_size=8)

    detected_language = result.get("language", language)
    print(f"Detected language: {detected_language}")

    try:
        align_model, metadata = whisperx.load_align_model(language_code=detected_language, device=device)
        result = whisperx.align(result["segments"], align_model, metadata, audio, device, return_char_alignments=False)
    except Exception as error:
        print(f"Alignment failed, continuing without alignment: {error}")

    min_speakers = int(os.environ.get("MIN_SPEAKERS", 2))
    max_speakers = int(os.environ.get("MAX_SPEAKERS", 2))

    if hf_token:
        print(f"Running whisperX diarization (min_speakers={min_speakers}, max_speakers={max_speakers})...")
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
        diarize_segments = diarize_model(audio_file, min_speakers=min_speakers, max_speakers=max_speakers)
        result = whisperx.assign_word_speakers(diarize_segments, result)
    else:
        print("HUGGINGFACE_HUB_TOKEN missing; continuing without speaker diarization.")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    print("=" * 80)
    print("WHISPERX DIARIZED TRANSCRIPTION")
    print("=" * 80)

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


if __name__ == "__main__":
    main()
