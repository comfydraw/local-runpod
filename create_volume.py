import os
import argparse
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "runpod.env"))
api_key = os.getenv("RUNPOD_API_KEY")

def create_network_volume(name: str, size: int, datacenter_id: str):
    """
    Creates a RunPod Network Volume via the GraphQL API.
    """
    url = "https://api.runpod.io/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    query = """
    mutation CreateNetworkVolume($input: NetworkVolumeCreateInput!) {
      networkVolumeCreate(input: $input) {
        id
        name
        size
        dataCenterId
      }
    }
    """

    variables = {
        "input": {
            "name": name,
            "size": size,
            "dataCenterId": datacenter_id
        }
    }

    print(f"Creating volume '{name}' ({size}GB) in {datacenter_id}...")
    response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print("Error from GraphQL API:")
            for err in data["errors"]:
                print(f" - {err.get('message')}")
            return None
        
        vol = data.get("data", {}).get("networkVolumeCreate", {})
        if vol:
            print("Volume created successfully!")
            print(f"ID: {vol.get('id')}")
            print(f"Name: {vol.get('name')}")
            print(f"Size: {vol.get('size')} GB")
            print(f"Datacenter: {vol.get('dataCenterId')}")
            return vol.get("id")
    else:
        print(f"Failed to connect to API. Status code: {response.status_code}")
        print(response.text)
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a RunPod Network Volume")
    parser.add_argument("--name", required=True, help="Name of the volume (e.g., comfyui-models)")
    parser.add_argument("--size", type=int, default=50, help="Size of the volume in GB (default: 50)")
    parser.add_argument("--region", required=True, help="Datacenter ID (e.g., US-NJ, EU-RO)")
    args = parser.parse_args()
    
    if not api_key:
        print("Error: RUNPOD_API_KEY environment variable not set.")
        exit(1)
        
    create_network_volume(args.name, args.size, args.region)
