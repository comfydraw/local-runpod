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

The custom image (`ghcr.io/comfydraw/runpod-comfyui-sync:latest` or your fork’s equivalent) needs a **My Template** in RunPod so pods can be launched with the right image and environment variables.

### Prerequisites

- Docker image built and pushed (e.g. via GitHub Actions from this repo).
- RunPod account and API key in `runpod.env`.
- (Optional) GCP Service Account JSON and workspace definition for Google Drive sync.

### Step 1: Create RunPod Secrets (for sensitive data)

Store credentials as RunPod Secrets so they are not in plain text.

1. Go to [RunPod Secrets](https://www.console.runpod.io/user/secrets).
2. Click **Create Secret** for each:

   | Secret Name     | Description                               | Value                                  |
   |-----------------|-------------------------------------------|----------------------------------------|
   | `gcp_sa_b64`    | Base64-encoded GCP Service Account JSON   | `base64 -w0 credentials/your-sa.json`  |
   | `workspace_def_b64` | Base64-encoded workspace definition | `base64 -w0 workspace_def.json`        |

   Generate the value locally, e.g.:

   ```bash
   base64 -w0 credentials/your-sa.json
   ```

   Paste the output into the **Secret Value** field.

### Step 2: Create the My Template

1. Go to [RunPod My Templates](https://www.console.runpod.io/user/templates).
2. Click **New Template**.
3. Configure:

   | Setting          | Value                                                                 |
   |------------------|-----------------------------------------------------------------------|
   | **Name**         | `comfyui-gdrive-sync` (or similar)                                   |
   | **Container Image** | `ghcr.io/comfydraw/runpod-comfyui-sync:latest` (or your org’s path) |
   | **Container Disk**  | 20 GB or more                                                        |
   | **TCP Ports**    | Add SSH (22)                                                          |
   | **HTTP Ports**   | Add ComfyUI (8188)                                                    |

4. Expand **Environment Variables** and add:

   | Key            | Value                                         |
   |----------------|-----------------------------------------------|
   | `GCP_SA_B64`   | `{{ RUNPOD_SECRET_gcp_sa_b64 }}`              |
   | `WORKSPACE_DEF_B64` | `{{ RUNPOD_SECRET_workspace_def_b64 }}` |

   Use the secret selector (key icon) to pick the matching secrets.  
   If you skip sync, you can omit these; the entrypoint will detect their absence and start ComfyUI without syncing.

5. Click **Save Template**.

### Step 3: Configure `runpod.env`

Set the template or image in `runpod.env`:

```
RUNPOD_TEMPLATE_ID=<your-template-id>
```

Use your **My Template ID** (a short alphanumeric string like `ppny3n7iri`, visible in the template URL or API). The `launch_pod.py` script treats values with `/` or `:` as Docker image names; otherwise it uses them as template IDs.

Alternatively, use the image directly (no secrets from the template):

```
RUNPOD_TEMPLATE_ID=ghcr.io/comfydraw/runpod-comfyui-sync:latest
```

### Step 4: Launch a Pod

```bash
source .venv/bin/activate
python3 launch_pod.py --template <your-template-id>
```

Or set `RUNPOD_TEMPLATE_ID` in `runpod.env` and run:

```bash
python3 launch_pod.py
```

### Notes

- **GHCR images:** Public GHCR images work without extra registry config. For private images, configure RunPod registry credentials in the template or account settings.
- **Secrets:** The `{{ RUNPOD_SECRET_* }}` syntax is resolved at pod start. The container receives the decoded values as environment variables.
- **Optional sync:** If `GCP_SA_B64` and `WORKSPACE_DEF_B64` are not set, the entrypoint skips sync and starts ComfyUI directly.
