import requests
import json
from flask import Flask, request, jsonify
from gpt_engine import ask_gpt  # Assume you have this module already set up

HA_URL = "http://homeassistant.local:8123"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkYjdmNWFkYmIyMDY0NDgwODMyYzc0N2EwMjVmYTY1ZiIsImlhdCI6MTc0ODg1MTUzOCwiZXhwIjoyMDY0MjExNTM4fQ.kWfseEuz7bfvs70-hYk81JiWjiBuf-N0StsrhbbRVDo"
HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json"
}

app = Flask(__name__)

def get_all_entities():
    response = requests.get(f"{HA_URL}/api/states", headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        return []

def call_service(entity_id, service, service_data=None):
    domain = entity_id.split(".")[0]
    url = f"{HA_URL}/api/services/{domain}/{service}"
    payload = {"entity_id": entity_id}
    if service_data:
        payload.update(service_data)
    response = requests.post(url, headers=HEADERS, json=payload)
    return response.status_code == 200

def handle_voice_command(text):
    entities = get_all_entities()
    gpt_response = ask_gpt(text, entities)
    print("[GPT]", gpt_response)

    if gpt_response.get("entity") and gpt_response.get("intent"):
        success = call_service(
            gpt_response["entity"],
            gpt_response["intent"],
            gpt_response.get("data")
        )
        if success:
            return gpt_response.get("response", "Done.")
        else:
            return "I couldn’t complete that action."
    else:
        return gpt_response.get("response", "I'm not sure what to do.")

@app.route("/api/voice_trigger", methods=["POST"])
def voice_trigger():
    data = request.get_json()
    user_input = data.get("text", "")
    device = data.get("device", "unknown")

    print(f"[VOICE] Received from {device}: {user_input}")
    reply = handle_voice_command(user_input)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    print("✅ Jarvis Flask server running on port 5000...")
    app.run(host="0.0.0.0", port=5000")
