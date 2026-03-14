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
