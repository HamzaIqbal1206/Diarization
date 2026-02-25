# Faster-Whisper + Diarization Setup Guide

## Current Status
✅ **Transcription is working** with faster-whisper  
⚠️ **Diarization needs Hugging Face authentication**

## Quick Start

### 1. Activate the Environment
```bash
source whisper_env/bin/activate
```

### 2. Set Up Hugging Face Token (Required for Diarization)

#### Step A: Create a Token
1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Give it a name (e.g., "pyannote-diarization")
4. Set permissions to "Read"
5. Copy the token

#### Step B: Accept Model License
1. Visit https://huggingface.co/pyannote/speaker-diarization-3.1
2. Click "Agree and access repository"
3. Also accept: https://huggingface.co/pyannote/segmentation-3.0

#### Step C: Set the Token
```bash
# Temporary (current session only)
export HUGGINGFACE_HUB_TOKEN='hf_your_token_here'

# OR Permanent (add to your ~/.zshrc or ~/.bashrc)
echo 'export HUGGINGFACE_HUB_TOKEN="hf_your_token_here"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Run Diarization
```bash
python diarize.py
```

## What Each Script Does

### `diarize.py` (RECOMMENDED)
- **Transcribes** audio with faster-whisper
- **Identifies speakers** with pyannote.audio
- **Merges** transcripts with speaker labels
- Saves output to `diarized_transcript.txt`

### `whisperx_diarization.py`
- Original implementation (similar approach)
- Hardcoded audio path

## How It Works

```
Audio File (sample1.mp3)
    ↓
1. Faster-Whisper Transcription
   → Segments with text + timestamps
    ↓
2. Pyannote Diarization
   → Speaker turns with timestamps
    ↓
3. Overlap Matching Algorithm
   → Assigns speakers to transcribed segments
    ↓
Output: Timestamped transcript with speaker labels
```

## Troubleshooting

### "Module not found: pyannote.audio"
- Make sure you activated the environment: `source whisper_env/bin/activate`

### "Could not download pipeline"
- You need to set up the Hugging Face token (see step 2 above)
- Accept the model licenses on Hugging Face

### "No module named 'faster_whisper'"
```bash
source whisper_env/bin/activate
pip install faster-whisper
```

### Slow transcription
- The script uses CPU by default
- For GPU acceleration, install CUDA and change `device="cpu"` to `device="cuda"` in diarize.py

## Output Format

```
[0.00s - 2.50s] SPEAKER_00
  Hello, welcome to the podcast.

[2.50s - 5.30s] SPEAKER_01
  Thanks for having me!
```

## Configuration Options

Edit `diarize.py` to change:

```python
model_size = "base"  # tiny, base, small, medium, large-v2, large-v3
language = "en"      # or None for auto-detection
audio_file = "sample1.mp3"  # your audio file path
```

## Model Sizes & Performance

| Model  | Speed      | Accuracy | RAM Usage |
|--------|------------|----------|-----------|
| tiny   | Very Fast  | Low      | ~1 GB     |
| base   | Fast       | Good     | ~1 GB     |
| small  | Medium     | Better   | ~2 GB     |
| medium | Slow       | Great    | ~5 GB     |
| large  | Very Slow  | Best     | ~10 GB    |

## Next Steps

Once your token is set up:
1. Run `python diarize.py`
2. Check `diarized_transcript.txt` for results
3. Adjust model size if needed for better accuracy

## Need Help?

- Faster-Whisper docs: https://github.com/guillaumekln/faster-whisper
- Pyannote docs: https://github.com/pyannote/pyannote-audio
- Hugging Face: https://huggingface.co/pyannote/speaker-diarization-3.1
