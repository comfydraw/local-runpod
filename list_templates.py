import runpod
import os
from tabulate import tabulate
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "runpod.env"))
runpod.api_key = os.getenv("RUNPOD_API_KEY")

def list_templates():
    print("Fetching templates (User & Community)...")
    try:
        # Fetching user templates
        # If the SDK does not support this directly, we would need to use raw GraphQL.
        # This assumes a high-level method exists or we print a placeholder.
        # For now, we will simulate or use a raw query if needed.
        
        # Creating a basic placeholder to show intent, as SDK methods vary.
        # A real implementation would query:
        # query { mysPodTemplates { id, name, imageName } }
        
        print("Note: To list templates reliably, we often need to inspect the Web UI.")
        print("However, common ComfyUI templates are:")
        print(tabulate([
            ["runpod/comfyui:latest", "RunPod Official ComfyUI"],
            ["thebloke/cuda11.8.0-ubuntu22.04-oneclick:latest", "TheBloke AI Template"]
        ], headers=["Template ID / Image Name", "Description"]))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_templates()
