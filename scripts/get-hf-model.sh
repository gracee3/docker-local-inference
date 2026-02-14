#!/usr/bin/env bash
set -euo pipefail

# Clone or update a Hugging Face model repo using git-lfs.
#
# Usage:
#   ./scripts/get-hf-model.sh <hf-repo-id> [dest-dir]
#
# Examples:
#   ./scripts/get-hf-model.sh Qwen/Qwen2.5-14B-Instruct-AWQ
#   ./scripts/get-hf-model.sh Qwen/Qwen2.5-7B-Instruct-AWQ /data/models/qwen2p5-7b-instruct-awq

REPO_ID="${1:?Usage: $0 <hf-repo-id> [dest-dir]}"
DEST="${2:-/data/models/$(basename "$REPO_ID")}"

if ! command -v git-lfs &>/dev/null; then
  echo "ERROR: git-lfs is not installed. Run: sudo apt install git-lfs && git lfs install"
  exit 1
fi

if [ -d "$DEST/.git" ]; then
  echo "Directory $DEST exists, pulling latest..."
  git -C "$DEST" pull
else
  echo "Cloning $REPO_ID -> $DEST ..."
  git clone "https://huggingface.co/$REPO_ID" "$DEST"
fi

echo "Done. Model at: $DEST"
