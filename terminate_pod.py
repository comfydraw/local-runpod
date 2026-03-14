import runpod
import os
import argparse
from dotenv import load_dotenv

# Load env vars
env_path = os.path.join(os.path.dirname(__file__), "runpod.env")
load_dotenv(env_path)
api_key = os.getenv("RUNPOD_API_KEY")

if not api_key:
    print("Error: RUNPOD_API_KEY not found in environment.")
    exit(1)

runpod.api_key = api_key

def terminate_pod(pod_id):
    print(f"Terminating pod {pod_id}...")
    try:
        runpod.terminate_pod(pod_id)
        print(f"Pod {pod_id} termination requested successfully.")
    except Exception as e:
        print(f"Failed to terminate pod: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pod_id", required=False, help="The ID of the pod to terminate (defaults to .active_pod_id)")
    args = parser.parse_args()
    
    pod_to_terminate = args.pod_id
    active_id_path = os.path.join(os.path.dirname(__file__), ".active_pod_id")
    
    if not pod_to_terminate:
        if os.path.exists(active_id_path):
            with open(active_id_path, "r") as f:
                pod_to_terminate = f.read().strip()
        
    if pod_to_terminate:
        terminate_pod(pod_to_terminate)
        
        # Clean up the tracking file
        if os.path.exists(active_id_path):
            try:
                os.remove(active_id_path)
            except:
                pass
    else:
        print("No pod_id provided and .active_pod_id not found. Nothing to terminate.")
