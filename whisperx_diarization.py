from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

audio_file = "/Users/hamzaiqbal/audio_test/sample2.mp3"

# 1️⃣ Transcription
model = WhisperModel("base")
segments, _ = model.transcribe(audio_file, language="en")

# 2️⃣ Diarization
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
diarization = pipeline(audio_file)

# 3️⃣ Merge
merged = []
for segment in segments:
    # Find the speaker who overlaps the most with the segment
    max_overlap = 0
    assigned_speaker = "Unknown"
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        overlap = max(0, min(turn.end, segment.end) - max(turn.start, segment.start))
        if overlap > max_overlap:
            max_overlap = overlap
            assigned_speaker = speaker
    merged.append((assigned_speaker, segment.text, segment.start, segment.end))

# 4️⃣ Print result
for speaker, text, start, end in merged:
    print(f"{speaker} [{start:.2f}-{end:.2f}]: {text}")
