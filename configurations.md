# Configurations

Both pipelines are configured through **environment variables** set in their respective `docker-compose.yml` files. Below is a breakdown of every tuneable parameter.

---

## Common Configuration (Both Pipelines)

These environment variables are shared across the Faster Whisper and WhisperX pipelines.

### `HUGGINGFACE_HUB_TOKEN`
- **Where to set:** `docker-compose.yml` or shell environment
- **Default:** _(empty)_
- Your Hugging Face access token. **Required** for speaker diarization (pyannote models are gated).
- Generate one at https://huggingface.co/settings/tokens and accept the model terms at https://huggingface.co/pyannote/speaker-diarization-3.1.

### `AUDIO_FILE`
- **Where to set:** `docker-compose.yml`
- **Default:** `sample6.m4a` (Faster Whisper) / `sample2.mp3` (WhisperX)
- Path to the audio file to process. Can be a filename inside the mounted `/app/audio` directory or an absolute path.
- Supported formats: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac`, `.aiff`
- If the file is not found, the pipeline auto-discovers the first audio file in `/app/audio`.

### `MIN_SPEAKERS`
- **Where to set:** `docker-compose.yml`
- **Default:** `2`
- Minimum number of speakers expected in the audio. Helps the diarization model when you know the speaker count in advance.

### `MAX_SPEAKERS`
- **Where to set:** `docker-compose.yml`
- **Default:** `2`
- Maximum number of speakers expected. Set equal to `MIN_SPEAKERS` if you know the exact count; widen the range if unsure.

---

## Faster Whisper Pipeline

**File:** `pipelines/fasterwhisper/docker-compose.yml`  
**Script:** `pipelines/fasterwhisper/run_diarization.py`

### Whisper Model Size

Set directly in `run_diarization.py` (line 38):

```python
model_size = "medium"
```

Available options:

- **`tiny`** — Fastest / Lowest accuracy / ~1 GB VRAM
- **`base`** — Very fast / Low accuracy / ~1 GB VRAM
- **`small`** — Fast / Moderate accuracy / ~2 GB VRAM
- **`medium`** — Moderate speed / Good accuracy / ~5 GB VRAM
- **`large-v1`** — Slow / High accuracy / ~10 GB VRAM
- **`large-v2`** — Slow / Higher accuracy / ~10 GB VRAM
- **`large-v3`** — Slow / Highest accuracy / ~10 GB VRAM

### Language

Set in `run_diarization.py` (line 39):

```python
language = "en"
```

- Set to a language code (`"en"`, `"fr"`, `"de"`, etc.) to force that language.
- Set to `None` for **auto-detection** (slower, as the model must identify the language first).

### Device & Compute Type

Set in `run_diarization.py` (line 52):

```python
model = WhisperModel(model_size, device="cpu", compute_type="int8")
```

- **`device`** — `"cpu"` or `"cuda"`
  - Use `"cuda"` if you have an NVIDIA GPU and the container has GPU access.
- **`compute_type`** — `"int8"`, `"float16"`, or `"float32"`
  - `int8` is best for CPU; `float16` is ideal for GPU; `float32` gives maximum precision at the cost of speed/memory.

To enable GPU inside Docker, uncomment the GPU section in `docker-compose.yml`:

```yaml
runtime: nvidia
environment:
  - NVIDIA_VISIBLE_DEVICES=all
```

### Diarization Model

The pyannote diarization model is set in `run_diarization.py` (line 76):

```python
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=hf_token)
```

You can swap this for another pyannote pipeline (e.g., `"pyannote/speaker-diarization"`) if needed.

---

## WhisperX Pipeline

**File:** `pipelines/whisperx/docker-compose.yml`  
**Script:** `pipelines/whisperx/run_diarization.py`

### Whisper Model Size

Set via the `WHISPERX_MODEL` environment variable in `docker-compose.yml`:

```yaml
- WHISPERX_MODEL=small
```

Same model options as the Faster Whisper pipeline: `tiny`, `base`, `small`, `medium`, `large-v1`, `large-v2`, `large-v3`.

### Language

Set via the `LANGUAGE` environment variable in `docker-compose.yml`:

```yaml
- LANGUAGE=en
```

Use any supported language code. The pipeline will also attempt alignment for the detected language.

### Device & Compute Type

Automatically selected in `run_diarization.py`:

```python
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"
```

- If a GPU is available in the container, it uses `cuda` + `float16`.
- Otherwise falls back to `cpu` + `int8`.
- No manual change needed unless you want to override this logic.

### Batch Size

Set in `run_diarization.py` (line 56):

```python
result = model.transcribe(audio, batch_size=8)
```

- Higher values speed up transcription but use more memory.
- Lower values (e.g., `1` or `4`) are safer on memory-constrained systems.

### Word-level Alignment

WhisperX runs a secondary alignment step after transcription. This is automatic but can fail for unsupported languages. If alignment fails, the pipeline continues with the original segment timestamps.

---

## Quick Reference — Where to Change What

> **Audio file**
> - Faster Whisper: `docker-compose.yml` → `AUDIO_FILE`
> - WhisperX: `docker-compose.yml` → `AUDIO_FILE`

> **Model size**
> - Faster Whisper: `run_diarization.py` → `model_size`
> - WhisperX: `docker-compose.yml` → `WHISPERX_MODEL`

> **Language**
> - Faster Whisper: `run_diarization.py` → `language`
> - WhisperX: `docker-compose.yml` → `LANGUAGE`

> **Speaker count**
> - Both: `docker-compose.yml` → `MIN_SPEAKERS` / `MAX_SPEAKERS`

> **CPU vs GPU**
> - Faster Whisper: `run_diarization.py` → `device`
> - WhisperX: Automatic (needs GPU in container)

> **Compute precision**
> - Faster Whisper: `run_diarization.py` → `compute_type`
> - WhisperX: Automatic

> **HF token**
> - Both: `docker-compose.yml` or shell export
