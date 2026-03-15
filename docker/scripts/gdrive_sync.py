"""
Google Drive → RunPod Volume sync script.

Reads a workspace definition and GCP Service Account credentials from
base64-encoded environment variables, then downloads any models that
are missing from the local ComfyUI models directory.

Environment variables:
    GCP_SA_B64          Base64-encoded GCP Service Account JSON
    workspace_def_b64   Base64-encoded workspace definition JSON

Workspace definition schema:
    {
        "workspace_id": "sdxl-architecture",
        "models": [
            {
                "drive_file_id": "1A2B3C...",
                "file_name": "model.safetensors",
                "parent_folder_name": "checkpoints"
            }
        ]
    }

Each model's parent_folder_name maps to a ComfyUI subdirectory:
    /workspace/ComfyUI/models/<parent_folder_name>/<file_name>
"""

import base64
import io
import json
import os
import sys
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

COMFYUI_MODELS_ROOT = "/workspace/ComfyUI/models"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

KNOWN_MODEL_DIRS = {
    "checkpoints",
    "clip",
    "clip_vision",
    "configs",
    "controlnet",
    "diffusers",
    "embeddings",
    "gligen",
    "hypernetworks",
    "loras",
    "style_models",
    "unet",
    "upscale_models",
    "vae",
    "vae_approx",
}


def decode_env(var_name: str) -> str:
    raw = os.environ.get(var_name)
    if not raw:
        print(f"[sync] ERROR: {var_name} not set", file=sys.stderr)
        sys.exit(1)
    try:
        return base64.b64decode(raw).decode("utf-8")
    except Exception as e:
        print(f"[sync] ERROR: failed to decode {var_name}: {e}", file=sys.stderr)
        sys.exit(1)


def build_drive_service(sa_json: str):
    info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def download_file(service, file_id: str, dest_path: str, file_name: str):
    """Download a single file from Google Drive with progress reporting."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    request = service.files().get_media(fileId=file_id)
    tmp_path = dest_path + ".tmp"

    with open(tmp_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request, chunksize=50 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"[sync]   {file_name}: {pct}%")

    os.rename(tmp_path, dest_path)


def get_remote_size(service, file_id: str) -> int | None:
    """Fetch the file size from Drive metadata (returns None if unavailable)."""
    try:
        meta = service.files().get(fileId=file_id, fields="size").execute()
        return int(meta["size"]) if "size" in meta else None
    except Exception:
        return None


def sync_workspace(service, workspace: dict) -> bool:
    models = workspace.get("models", [])
    if not models:
        print("[sync] Workspace has no models — nothing to sync.")
        return True

    total = len(models)
    downloaded = 0
    skipped = 0
    failed = 0

    for i, model in enumerate(models, 1):
        file_id = model["drive_file_id"]
        file_name = model["file_name"]
        parent = model["parent_folder_name"]

        if parent not in KNOWN_MODEL_DIRS:
            print(f"[sync] WARNING: '{parent}' is not a recognized ComfyUI model "
                  f"directory — syncing anyway.")

        dest = os.path.join(COMFYUI_MODELS_ROOT, parent, file_name)

        print(f"[sync] [{i}/{total}] {parent}/{file_name}")

        if os.path.exists(dest):
            local_size = os.path.getsize(dest)
            remote_size = get_remote_size(service, file_id)
            if remote_size and local_size == remote_size:
                print(f"[sync]   Already exists ({local_size:,} bytes) — skipping.")
                skipped += 1
                continue
            elif remote_size:
                print(f"[sync]   Size mismatch (local={local_size:,}, "
                      f"remote={remote_size:,}) — re-downloading.")
            else:
                print(f"[sync]   Already exists ({local_size:,} bytes) — skipping "
                      f"(remote size unknown).")
                skipped += 1
                continue

        start = time.time()
        try:
            download_file(service, file_id, dest, file_name)
            elapsed = time.time() - start
            size = os.path.getsize(dest)
            speed = size / elapsed / (1024 * 1024) if elapsed > 0 else 0
            print(f"[sync]   Done — {size:,} bytes in {elapsed:.1f}s "
                  f"({speed:.1f} MB/s)")
            downloaded += 1
        except Exception as e:
            print(f"[sync]   FAILED: {e}", file=sys.stderr)
            if os.path.exists(dest + ".tmp"):
                os.remove(dest + ".tmp")
            failed += 1

    print(f"\n[sync] Summary: {downloaded} downloaded, {skipped} skipped, "
          f"{failed} failed out of {total} models.")

    if failed > 0:
        print("[sync] WARNING: Some models failed to sync.", file=sys.stderr)
        return False

    return True


def cleanup_stale_files(workspace: dict):
    """Remove model files on the volume that are not part of this workspace."""
    wanted = set()
    for model in workspace.get("models", []):
        rel = os.path.join(model["parent_folder_name"], model["file_name"])
        wanted.add(rel)

    removed = 0
    for dirpath, _, filenames in os.walk(COMFYUI_MODELS_ROOT):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, COMFYUI_MODELS_ROOT)
            parts = rel.split(os.sep)
            # Only clean files that sit directly inside a known model subdirectory
            if len(parts) == 2 and parts[0] in KNOWN_MODEL_DIRS and rel not in wanted:
                print(f"[sync] Removing stale file: {rel}")
                os.remove(full)
                removed += 1

    if removed:
        print(f"[sync] Cleaned up {removed} stale file(s).")


def main():
    print("[sync] === Google Drive Workspace Sync ===")
    print(f"[sync] Models root: {COMFYUI_MODELS_ROOT}")

    sa_json = decode_env("GCP_SA_B64")
    ws_json = decode_env("workspace_def_b64")

    workspace = json.loads(ws_json)
    ws_id = workspace.get("workspace_id", "unknown")
    model_count = len(workspace.get("models", []))
    print(f"[sync] Workspace: {ws_id} ({model_count} models)")

    service = build_drive_service(sa_json)

    success = sync_workspace(service, workspace)

    if success:
        cleanup_stale_files(workspace)

    print("[sync] === Sync complete ===")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
