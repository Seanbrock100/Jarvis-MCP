import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

HA_URL = os.getenv("HA_URL", "http://homeassistant.local:8123")
HA_TOKEN = os.getenv("HA_TOKEN")

if not HA_TOKEN:
    raise ValueError("HA_TOKEN not set in environment variables")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json"
}

def fetch_entities():
    url = f"{HA_URL}/api/states"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        entities = response.json()
        with open("entities.json", "w") as f:
            json.dump(entities, f, indent=2)
        from datetime import datetime
        entities_summary = [{"entity_id": e["entity_id"], "name": e["attributes"].get("friendly_name", ""), "domain": e["entity_id"].split(".")[0]} for e in entities]
        with open("entities_summary.json", "w") as f_summary:
            json.dump(entities_summary, f_summary, indent=2)
        print(f"✅ Saved {len(entities)} entities to entities.json")
        print(f"✅ Summary saved to entities_summary.json at {datetime.now()}")
    else:
        print(f"❌ Failed to fetch entities: {response.status_code} - {response.text}")

# Utility function to load all entities from entities.json
def get_all_entities():
    try:
        with open("entities.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not load entities.json: {e}")
        return []

if __name__ == "__main__":
    fetch_entities()