# RunPod Interface Scripts

CLI utilities for managing RunPod GPU pods, network volumes, and the ComfyUI worker lifecycle.

## Setup

```bash
cd /mnt/Hot/Services/runpod

# Create the virtual environment (one-time)
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

All scripts load `RUNPOD_API_KEY` from `runpod.env` in this directory.
`launch_pod.py` also reads `RUNPOD_GPU_TYPE_ID` and `RUNPOD_TEMPLATE_ID` as defaults.

## Scripts

### Inventory

```bash
# List available GPU types and VRAM
python3 list_gpus.py

# List known ComfyUI templates (static reference list)
python3 list_templates.py
```

### Pod Management

```bash
# Launch a pod (uses RUNPOD_GPU_TYPE_ID and RUNPOD_TEMPLATE_ID from runpod.env)
python3 launch_pod.py

# Override GPU or template
python3 launch_pod.py --gpu "NVIDIA RTX 4090" --template "runpod/comfyui:latest"

# Attach a network volume
python3 launch_pod.py --volume_id "nv-xxxxxxx"

# Launch with a workspace override
python3 launch_pod.py --workspace path/to/workspace.json

# List active pods and their ComfyUI URLs
python3 list_pods.py

# Get the ComfyUI endpoint for a specific pod
python3 get_endpoint.py --pod_id "abc123def"

# Terminate the most recently launched pod (reads .active_pod_id)
python3 terminate_pod.py

# Terminate a specific pod
python3 terminate_pod.py --pod_id "abc123def"
```

`launch_pod.py` saves the pod ID to `.active_pod_id` so that `terminate_pod.py` can pick it up without arguments.
It also retries automatically on capacity errors (up to 10 attempts with 15s backoff).

### Network Volumes

```bash
# List all network volumes on the account
python3 list_volumes.py

# Create a new volume (50 GB default)
python3 create_volume.py --name "comfyui-models" --region "US-TX"
python3 create_volume.py --name "comfyui-models" --size 100 --region "EU-RO"

# Delete a volume
python3 delete_volume.py --id "nv-xxxxxxx"
```

### Full Lifecycle Test

```bash
# Launch pod -> wait for endpoint -> run ComfyUI workflow -> terminate pod
python3 runpod_request.py --workflow ../workflows/test.json

# With a network volume attached
python3 runpod_request.py --workflow ../workflows/test.json --volume_id "nv-xxxxxxx"
```

This requires a `docker-compose.runpod.yml` to be present at `../../docker/docker-compose.runpod.yml`
relative to this directory, with a `request-handler` service configured.

---

## Creating the ComfyUI + GDrive Sync My Template

The custom image (`ghcr.io/comfydraw/runpod-comfyui-sync:latest` or your fork's equivalent) needs a **My Template** in RunPod so pods can be launched with the right image, credentials, and a default workspace.

### Prerequisites

- Docker image built and pushed (e.g. via GitHub Actions from this repo).
- RunPod account and API key in `runpod.env`.
- GCP Service Account JSON for Google Drive access.
- A default workspace definition JSON (the baseline model set for new pods).

### Step 1: Create RunPod Secrets

Store the GCP credential and a default workspace definition as RunPod Secrets.

1. Go to [RunPod Secrets](https://www.console.runpod.io/user/secrets).
2. Click **Create Secret** for each:

   | Secret Name          | Description                             | How to generate the value              |
   |----------------------|-----------------------------------------|----------------------------------------|
   | `gcp_sa_b64`         | GCP Service Account JSON (base64)       | `base64 -w0 credentials/your-sa.json`  |
   | `workspace_def_b64`  | Default workspace definition (base64)   | `base64 -w0 workspace_default.json`    |

   `gcp_sa_b64` is a real credential and must be a Secret. `workspace_def_b64` is not sensitive, but storing the default as a Secret keeps all template config in one place and makes it easy to update without editing launch scripts.

### Step 2: Create the My Template

1. Go to [RunPod My Templates](https://www.console.runpod.io/user/templates).
2. Click **New Template**.
3. Configure:

   | Setting              | Value                                                                 |
   |----------------------|-----------------------------------------------------------------------|
   | **Name**             | `comfyui-gdrive-sync` (or similar)                                   |
   | **Container Image**  | `ghcr.io/comfydraw/runpod-comfyui-sync:latest` (or your org's path)  |
   | **Container Disk**   | 20 GB or more                                                        |
   | **TCP Ports**        | Add SSH (22)                                                          |
   | **HTTP Ports**       | Add ComfyUI (8188)                                                    |

4. Expand **Environment Variables** and add:

   | Key                  | Value                                         |
   |----------------------|-----------------------------------------------|
   | `GCP_SA_B64`         | `{{ RUNPOD_SECRET_gcp_sa_b64 }}`              |
   | `workspace_def_b64`  | `{{ RUNPOD_SECRET_workspace_def_b64 }}`       |

   The `workspace_def_b64` here is the **default** workspace — the fallback model set used when no override is provided at launch time.

5. Click **Save Template**.

### Step 3: Configure `runpod.env`

```
RUNPOD_TEMPLATE_ID=<your-template-id>
```

Use the **My Template ID** (a short alphanumeric string like `ppny3n7iri`, visible in the template URL or API). The `launch_pod.py` script treats values containing `/` or `:` as Docker image names; anything else is used as a template ID.

### Step 4: Launch a Pod

```bash
source .venv/bin/activate

# Launch with the default workspace (from the template Secret)
python3 launch_pod.py

# Launch with a specific workspace (overrides the default)
python3 launch_pod.py --workspace path/to/workspace.json
```

### Workspace Override System

The template stores a **default** workspace definition as a Secret. This ensures every pod — whether launched from the CLI, the RunPod Console, or the API — always has a baseline set of models to sync.

The `--workspace` flag (or the `workspace_json` parameter when calling `launch_pod()` programmatically) lets callers **override** the default at launch time. When provided, the workspace JSON is base64-encoded and injected as `workspace_def_b64` via the pod's `env` dict, which takes precedence over the template-level value.

| Launch method | Workspace used |
|---|---|
| RunPod Console (Deploy on template) | Default (from template Secret) |
| `launch_pod.py` (no `--workspace`) | Default (from template Secret) |
| `launch_pod.py --workspace custom.json` | Override (from the provided file) |
| Frontend service (dashboard launch action) | Override (current workspace from registry) |

The entrypoint and sync script are unchanged — they read `workspace_def_b64` from the environment regardless of where it originated.

**Updating the default:** Re-encode a new workspace JSON, then update the `workspace_def_b64` Secret in the [RunPod Secrets](https://www.console.runpod.io/user/secrets) console. All future pods launched without an explicit override will pick up the new default.

### Notes

- **GHCR images:** Public GHCR images work without extra registry config. For private images, configure RunPod registry credentials in the template or account settings.
- **Secrets resolution:** `{{ RUNPOD_SECRET_* }}` is resolved at pod start. The container receives the values as plain environment variables.
- **Env override precedence:** The `env` dict passed to `create_pod()` overrides template-level env vars with the same key.
- **Optional sync:** If neither `GCP_SA_B64` nor `workspace_def_b64` is set, the entrypoint skips sync and starts ComfyUI directly.
