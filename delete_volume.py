import os
import argparse
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "runpod.env"))
api_key = os.getenv("RUNPOD_API_KEY")

def delete_network_volume(volume_id: str):
    """
    Deletes a RunPod Network Volume via the GraphQL API.
    """
    url = "https://api.runpod.io/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    query = """
    mutation DeleteNetworkVolume($id: String!) {
      networkVolumeDelete(id: $id)
    }
    """

    variables = {
        "id": volume_id
    }

    print(f"Deleting volume '{volume_id}'...")
    response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print("Error from GraphQL API:")
            for err in data["errors"]:
                print(f" - {err.get('message')}")
            return False
        
        # networkVolumeDelete returns a boolean indicating success
        success = data.get("data", {}).get("networkVolumeDelete")
        if success:
            print(f"Volume '{volume_id}' deleted successfully!")
            return True
        else:
            print(f"Failed to delete volume '{volume_id}'. It might be attached to a running pod or not exist.")
            return False
    else:
        print(f"Failed to connect to API. Status code: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete a RunPod Network Volume")
    parser.add_argument("--id", required=True, help="ID of the volume to delete (e.g., nv-xxxxxxx)")
    args = parser.parse_args()
    
    if not api_key:
        print("Error: RUNPOD_API_KEY environment variable not set.")
        exit(1)
        
    delete_network_volume(args.id)
