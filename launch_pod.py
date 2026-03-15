import base64
import json
import runpod
import os
import argparse
import time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "runpod.env"))
runpod.api_key = os.getenv("RUNPOD_API_KEY")


def launch_pod(
    gpu_type_id,
    template_id,
    max_attempts: int = 10,
    backoff_seconds: int = 15,
    volume_id: str = None,
    workspace_json: str = None,
):
    """
    Launch a Runpod GPU pod, retrying on capacity/unavailability errors.

    If volume_id is provided, the network volume will be attached to the pod.
    If workspace_json is provided (raw JSON string), it will be base64-encoded
    and injected as workspace_def_b64, overriding the template default.

    Returns the pod ID on success, or None after exhausting retries or on non-capacity errors.
    """
    print(f"Launching pod with {gpu_type_id} using {template_id}...")
    if volume_id:
        print(f"Attaching network volume: {volume_id}")

    # Distinguish image name (e.g. ghcr.io/org/img:tag) from My Template ID (alphanumeric)
    use_template = "/" not in template_id and ":" not in template_id

    env_overrides = {}
    if workspace_json:
        env_overrides["workspace_def_b64"] = base64.b64encode(
            workspace_json.encode()
        ).decode()
        ws = json.loads(workspace_json)
        print(f"Workspace override: {ws.get('workspace_id', 'unknown')} "
              f"({len(ws.get('models', []))} models)")

    for attempt in range(1, max_attempts + 1):
        try:
            pod_kwargs = {
                "name": f"ComfyUI-Worker-{int(time.time())}",
                "gpu_type_id": gpu_type_id,
                "cloud_type": "COMMUNITY",
                "ports": "8188/http",
                "container_disk_in_gb": 20,
            }
            if use_template:
                pod_kwargs["template_id"] = template_id
                pod_kwargs["image_name"] = ""
            else:
                pod_kwargs["image_name"] = template_id
            if volume_id:
                pod_kwargs["volume_id"] = volume_id
            if env_overrides:
                pod_kwargs["env"] = env_overrides

            pod = runpod.create_pod(**pod_kwargs)

            print(f"Pod launched successfully on attempt {attempt}!")
            print(f"Pod ID: {pod['id']}")
            print(f"Initial Status: {pod.get('status', 'UNKNOWN')}")

            # Save the active pod ID to a hidden file for the terminate script
            active_id_path = os.path.join(os.path.dirname(__file__), ".active_pod_id")
            with open(active_id_path, "w") as f:
                f.write(pod["id"])

            return pod["id"]

        except Exception as e:
            msg = str(e)
            # Heuristic: treat common capacity/unavailability messages as retriable
            lower = msg.lower()
            is_capacity_issue = any(
                keyword in lower
                for keyword in [
                    "no capacity",
                    "insufficient capacity",
                    "unavailable",
                    "temporarily unavailable",
                    "try again later",
                ]
            )

            print(f"[Attempt {attempt}/{max_attempts}] Failed to launch pod: {e}")

            # If this looks like a capacity issue and we have attempts left, back off and retry
            if is_capacity_issue and attempt < max_attempts:
                print(f"Capacity not available yet. Retrying in {backoff_seconds} seconds...")
                time.sleep(backoff_seconds)
                continue

            # Non-capacity error or out of attempts: give up
            if not is_capacity_issue:
                print("Non-capacity error encountered; not retrying.")
            else:
                print("Max retry attempts reached; giving up.")
            return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", default=os.getenv("RUNPOD_GPU_TYPE_ID", "NVIDIA GeForce RTX 3090"))
    parser.add_argument("--template", default=os.getenv("RUNPOD_TEMPLATE_ID", "runpod/comfyui:latest"))
    parser.add_argument("--volume_id", default=os.getenv("RUNPOD_VOLUME_ID", None),
                        help="Network Volume ID to attach (e.g., nv-xxxxxxx)")
    parser.add_argument("--workspace", default=None,
                        help="Path to workspace definition JSON (overrides template default)")
    args = parser.parse_args()

    ws_json = None
    if args.workspace:
        with open(args.workspace) as f:
            ws_json = f.read()

    launch_pod(args.gpu, args.template, volume_id=args.volume_id, workspace_json=ws_json)
