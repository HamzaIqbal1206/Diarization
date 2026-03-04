#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FW_OUTPUT_DIR="$ROOT_DIR/pipelines/fasterwhisper/output"
WX_OUTPUT_DIR="$ROOT_DIR/pipelines/whisperx/output"

clean_dir() {
  local dir_path="$1"
  if [[ -d "$dir_path" ]]; then
    find "$dir_path" -maxdepth 1 -type f -name "*.txt" -delete
  fi
}

clean_dir "$FW_OUTPUT_DIR"
clean_dir "$WX_OUTPUT_DIR"

echo "Output cleanup completed."
echo "- Cleared: $FW_OUTPUT_DIR/*.txt"
echo "- Cleared: $WX_OUTPUT_DIR/*.txt"
