import runpod
import os
from tabulate import tabulate
from dotenv import load_dotenv

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), "runpod.env"))
api_key = os.getenv("RUNPOD_API_KEY")

if not api_key:
    print("Error: RUNPOD_API_KEY not found in environment.")
    exit(1)

runpod.api_key = api_key

def list_gpus():
    try:
        # Note: runpod.get_gpus() returns static GPU specs, not live market data.
        # Use the Web UI to check current pricing and availability.
        gpus = runpod.get_gpus()
        
        table_data = []
        for gpu in gpus:
            table_data.append([
                gpu.get('id', 'N/A'),
                gpu.get('displayName', 'N/A'),
                gpu.get('memoryInGb', 'N/A')
            ])
            
        print(tabulate(table_data, headers=["ID", "Name", "VRAM (GB)"]))
        print("\nNote: Pricing and Availability are dynamic. Please check RunPod console if launch fails.")
        
    except Exception as e:
        print(f"Failed to list GPUs: {e}")

if __name__ == "__main__":
    list_gpus()
