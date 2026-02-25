from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu")

segments, info = model.transcribe("sample1.mp3")

for segment in segments:
    print(f"[{segment.start:.2f} -> {segment.end:.2f}] {segment.text}")

