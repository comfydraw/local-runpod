import time
import subprocess
import os
import runpod
from dotenv import load_dotenv
from launch_pod import launch_pod
from get_endpoint import get_endpoint

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), "runpod.env"))
runpod.api_key = os.getenv("RUNPOD_API_KEY")

def run_lifecycle_test(workflow_path, volume_id=None):
    print("=== Starting Lifecycle Test ===")
    
    # 1. Launch Pod
    gpu_type = os.getenv("RUNPOD_GPU_TYPE_ID", "NVIDIA GeForce RTX 3090")
    template_id = os.getenv("RUNPOD_TEMPLATE_ID", "runpod/comfyui:latest")
    
    # Use the passed volume_id, or fallback to environment variable
    vol_id = volume_id or os.getenv("RUNPOD_VOLUME_ID")
    
    pod_id = launch_pod(gpu_type, template_id, volume_id=vol_id)
    if not pod_id:
        print("Failed to launch pod. Exiting.")
        return

    try:
        # 2. Wait for Endpoint
        print("Waiting for endpoint to become available...")
        endpoint_http = None
        for i in range(30): # Wait up to 5 minutes (30 * 10s)
            endpoint_http = get_endpoint(pod_id)
            if endpoint_http:
                break
            time.sleep(10)
            print(f"Waiting... ({i+1}/30)")
        
        if not endpoint_http:
            print("Timed out waiting for endpoint.")
            raise Exception("Endpoint Timeout")

        endpoint_ws = endpoint_http.replace("https://", "wss://") + "/ws"
        print(f"Endpoint Ready: {endpoint_http}")

        # 3. Run Request Handler (via Docker Compose)
        print("=== Running Request Handler ===")
        
        # We use 'docker compose run' to inject the dynamic env vars
        cmd = [
            "docker", "compose", 
            "-f", "../../docker/docker-compose.runpod.yml", 
            "run", 
            "-e", f"COMFY_ENDPOINT_HTTP={endpoint_http}",
            "-e", f"COMFY_ENDPOINT_WS={endpoint_ws}",
            "request-handler", 
            "python", "main.py", "--workflow", workflow_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("Output:", result.stdout)
        print("Errors:", result.stderr)
        
        if result.returncode == 0:
            print("✅ Job Completed Successfully")
        else:
            print("❌ Job Failed")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # 4. Cleanup
        print(f"=== Terminating Pod {pod_id} ===")
        runpod.terminate_pod(pod_id)
        print("Pod Terminated.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, help="Path to workflow JSON (inside container)")
    parser.add_argument("--volume_id", default=None, help="Network Volume ID to attach (e.g., nv-xxxxxxx)")
    args = parser.parse_args()
    
    run_lifecycle_test(args.workflow, volume_id=args.volume_id)
