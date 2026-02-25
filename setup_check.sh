#!/bin/bash

# Diarization Setup Helper Script
# This script helps you set up Hugging Face authentication for speaker diarization

echo "============================================"
echo "  Faster-Whisper + Diarization Setup"
echo "============================================"
echo ""

# Check if we're in the right environment
if [[ "$VIRTUAL_ENV" != *"whisper_env"* ]]; then
    echo "⚠️  You need to activate the whisper_env environment first!"
    echo ""
    echo "Run this command:"
    echo "  source whisper_env/bin/activate"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✅ Virtual environment: whisper_env is active"
echo ""

# Check if token is already set
if [ -n "$HUGGINGFACE_HUB_TOKEN" ]; then
    echo "✅ HUGGINGFACE_HUB_TOKEN is already set"
    echo "   Token: ${HUGGINGFACE_HUB_TOKEN:0:7}...${HUGGINGFACE_HUB_TOKEN: -4}"
    echo ""
    echo "Ready to run diarization!"
    echo ""
    echo "Run: python diarize.py"
    exit 0
fi

echo "⚠️  HUGGINGFACE_HUB_TOKEN is not set"
echo ""
echo "To enable speaker diarization, follow these steps:"
echo ""
echo "1️⃣  Get your Hugging Face token:"
echo "   → Visit: https://huggingface.co/settings/tokens"
echo "   → Create a new token with 'Read' access"
echo ""
echo "2️⃣  Accept the model licenses:"
echo "   → Visit: https://huggingface.co/pyannote/speaker-diarization-3.1"
echo "   → Click 'Agree and access repository'"
echo "   → Also visit: https://huggingface.co/pyannote/segmentation-3.0"
echo ""
echo "3️⃣  Set your token (choose one option):"
echo ""
echo "   Option A - Just for this session:"
echo "   export HUGGINGFACE_HUB_TOKEN='hf_YourTokenHere'"
echo ""
echo "   Option B - Permanently (add to ~/.zshrc):"
echo "   echo 'export HUGGINGFACE_HUB_TOKEN=\"hf_YourTokenHere\"' >> ~/.zshrc"
echo "   source ~/.zshrc"
echo ""
echo "4️⃣  Run the diarization script:"
echo "   python diarize.py"
echo ""
echo "============================================"
echo ""
echo "NOTE: The script will still work without a token,"
echo "but it will only do transcription (no speaker labels)."
echo ""
