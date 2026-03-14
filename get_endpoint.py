import runpod
import os
import argparse
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "runpod.env"))
runpod.api_key = os.getenv("RUNPOD_API_KEY")

def get_endpoint(pod_id):
    try:
        pod = runpod.get_pod(pod_id)
        if not pod:
            print("Pod not found.")
            return None
            
        endpoint = None
        if pod.get('runtime') and pod['runtime'].get('ports'):
            for port in pod['runtime']['ports']:
                if port['privatePort'] == 8188 and port['isIpPublic']:
                    endpoint = f"https://{pod['id']}-8188.proxy.runpod.net"
        
        if endpoint:
            print(endpoint)
            return endpoint
        else:
            print("Endpoint not ready or port 8188 not exposed publicly.")
            return None
            
    except Exception as e:
        print(f"Error fetching pod: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pod_id", required=True, help=" The ID of the pod (e.g. v12345)")
    args = parser.parse_args()
    
    get_endpoint(args.pod_id)
