#!/bin/bash
set -e

echo "============================================"
echo "  ComfyUI + GDrive Sync (custom entrypoint)"
echo "============================================"

if [ -n "$workspace_def_b64" ] && [ -n "$GCP_SA_B64" ]; then
    echo "Workspace definition detected — starting sync..."
    python3 /app/gdrive_sync.py

    if [ $? -ne 0 ]; then
        echo "ERROR: Workspace sync failed. Halting boot."
        exit 1
    fi

    echo "Sync complete."
else
    echo "No workspace definition provided — skipping sync."
fi

echo "Handing off to ComfyUI..."

# The runpod/comfyui image uses /start.sh as its boot script.
# If it doesn't exist, fall back to running ComfyUI directly.
if [ -f /start.sh ]; then
    exec /start.sh "$@"
else
    exec python3 /workspace/ComfyUI/main.py --listen 0.0.0.0 "$@"
fi
