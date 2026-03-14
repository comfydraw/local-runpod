import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "runpod.env"))
api_key = os.getenv("RUNPOD_API_KEY")

def list_network_volumes():
    """
    Lists all RunPod Network Volumes for the account via the GraphQL API.
    """
    url = "https://api.runpod.io/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    query = """
    query {
      myself {
        networkVolumes {
          id
          name
          size
          dataCenterId
        }
      }
    }
    """

    print("Fetching network volumes...\n")
    response = requests.post(url, json={"query": query}, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print("Error from GraphQL API:")
            for err in data["errors"]:
                print(f" - {err.get('message')}")
            return
        
        volumes = data.get("data", {}).get("myself", {}).get("networkVolumes", [])
        if not volumes:
            print("No network volumes found.")
            return

        print(f"{'ID':<30} | {'NAME':<25} | {'SIZE (GB)':<10} | {'DATACENTER':<15}")
        print("-" * 85)
        for vol in volumes:
            print(f"{vol.get('id'):<30} | {vol.get('name'):<25} | {vol.get('size'):<10} | {vol.get('dataCenterId'):<15}")
    else:
        print(f"Failed to connect to API. Status code: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    if not api_key:
        print("Error: RUNPOD_API_KEY environment variable not set.")
        exit(1)
        
    list_network_volumes()
