import os
import json
import requests
from flask import Flask, request, jsonify
from gpt_engine import ask_gpt
from dotenv import load_dotenv

load_dotenv()

HA_URL = os.getenv("HA_URL", "http://homeassistant.local:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
SPEAKER_ENTITY = os.getenv("TTS_SPEAKER", "media_player.kitchen")

if not HA_TOKEN:
    raise ValueError("HA_TOKEN not set in environment variables")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json"
}

app = Flask(__name__)


def get_all_entities():
    try:
        with open("entities.json", "r") as f:
            entities = json.load(f)
            controllable = [e for e in entities if e["entity_id"] == "switch.conservatory_lights_switch_1"]
            print(f"[INFO] Using fixed entity: {controllable}")
            return controllable
    except Exception as e:
        print(f"[ERROR] Failed to load entities.json: {e}")
        return []


def call_service(entity_id, service, service_data=None):
    domain = entity_id.split(".")[0]
    url = f"{HA_URL}/api/services/{domain}/{service}"
    payload = {"entity_id": entity_id}
    if service_data:
        payload.update(service_data)
    response = requests.post(url, headers=HEADERS, json=payload)
    return response.status_code == 200


def speak_response(message):
    url = f"{HA_URL}/api/services/tts/google_translate_say"
    payload = {
        "entity_id": SPEAKER_ENTITY,
        "message": message
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    print(f"[TTS] Sent to {SPEAKER_ENTITY}: {message} | Status: {response.status_code}")
    return response.status_code == 200


def handle_voice_command(text):
    print(f"[DEBUG] Passing to ask_gpt: {text}")
    entities = get_all_entities()
    gpt_response = ask_gpt(text, entities)
    print("[DEBUG] GPT response received:", gpt_response)

    if not gpt_response:
        return {"error": "Failed to get response from GPT"}, 500

    try:
        parsed = gpt_response if isinstance(gpt_response, dict) else json.loads(gpt_response)
        entity = parsed.get("entity")
        valid_entities = [e["entity_id"] for e in entities]
        if entity not in valid_entities:
            print(f"[WARNING] Entity '{entity}' not in valid controllable entities.")
            return {"error": f"Unknown or unsupported entity: {entity}"}, 400
        intent = parsed.get("intent")
        message = parsed.get("response")

        if entity and intent:
            if call_service(entity, intent):
                speak_response(message)
                return {"reply": message}, 200
            else:
                return {"error": "Failed to control device"}, 500
        else:
            return {"error": "Incomplete GPT response"}, 400
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"error": "Exception while handling response"}, 500


@app.route("/api/voice_trigger", methods=["POST"])
def voice_trigger():
    data = request.get_json()
    user_input = data.get("text", "")
    device = data.get("device", "unknown")
    print(f"[VOICE] Received from {device}: {user_input}")
    result = handle_voice_command(user_input)
    status_code = result[1] if isinstance(result, tuple) else 500
    result = result[0] if isinstance(result, tuple) else result
    return jsonify(result), status_code


if __name__ == "__main__":
    print("✅ Jarvis Flask server running on port 5000...")
    app.run(host="0.0.0.0", port=5000)
