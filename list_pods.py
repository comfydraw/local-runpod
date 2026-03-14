import runpod
import os
from tabulate import tabulate
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "runpod.env"))
runpod.api_key = os.getenv("RUNPOD_API_KEY")

def list_pods():
    try:
        pods = runpod.get_pods()
        
        if pods:
            # Debug: print keys of first pod to find correct GPU field
            # print("DEBUG Pod Keys:", pods[0].keys())
            pass

        table_data = []
        for pod in pods:
            # Construct endpoint URL if ports are available
            endpoint = "N/A"
            if pod.get('runtime') and pod['runtime'].get('ports'):
                for port in pod['runtime']['ports']:
                    if port['privatePort'] == 8188 and port['isIpPublic']:
                        endpoint = f"https://{pod['id']}-8188.proxy.runpod.net"
            
            # Use .get() for safety
            gpu_name = pod.get('gpu_name', pod.get('machine', {}).get('gpuDisplayName', 'N/A'))

            table_data.append([
                pod.get('id', 'N/A'),
                pod.get('name', 'N/A'),
                gpu_name,
                pod.get('desiredStatus', 'N/A'),
                endpoint
            ])
            
        print(tabulate(table_data, headers=["ID", "Name", "GPU", "Status", "ComfyUI URL"]))
        
    except Exception as e:
        print(f"Error listing pods: {e}")

if __name__ == "__main__":
    list_pods()
