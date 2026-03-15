#!/bin/bash

echo "============================================"
echo "  ComfyUI + GDrive Sync (custom entrypoint)"
echo "============================================"

if [ -n "$workspace_def_b64" ] && [ -n "$GCP_SA_B64" ]; then
    echo "Workspace definition detected — sync will run after ComfyUI setup."

    # Start the base image's boot script in background.
    # /start.sh clones ComfyUI, installs deps, then launches it.
    /start.sh "$@" &
    START_PID=$!

    # Wait for ComfyUI's models directory to appear (created by /start.sh).
    MODELS_ROOT="${COMFYUI_MODELS_ROOT:-/workspace/runpod-slim/ComfyUI/models}"
    TIMEOUT=300
    ELAPSED=0
    echo "Waiting for ComfyUI setup to complete..."
    while [ ! -d "$MODELS_ROOT" ] && [ $ELAPSED -lt $TIMEOUT ]; do
        sleep 3
        ELAPSED=$((ELAPSED + 3))
    done

    if [ ! -d "$MODELS_ROOT" ]; then
        echo "WARNING: Models directory not found after ${TIMEOUT}s. Skipping sync."
    else
        echo "ComfyUI ready — starting workspace sync..."
        python3 /app/gdrive_sync.py
        if [ $? -ne 0 ]; then
            echo "WARNING: Workspace sync failed. ComfyUI is still running."
        else
            echo "Sync complete. Models are available."
        fi
    fi

    wait $START_PID
else
    echo "No workspace definition provided — skipping sync."
    echo "Handing off to ComfyUI..."
    if [ -f /start.sh ]; then
        exec /start.sh "$@"
    else
        exec python3 /workspace/ComfyUI/main.py --listen 0.0.0.0 "$@"
    fi
fi
