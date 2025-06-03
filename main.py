import os
import json
import requests
import tempfile
import base64
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import speech_recognition as sr
from io import BytesIO
import wave

load_dotenv()

HA_URL = os.getenv("HA_URL", "http://10.0.0.103:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
SPEAKER_ENTITY = os.getenv("TTS_SPEAKER", "media_player.kitchen")

if not HA_TOKEN:
    raise ValueError("HA_TOKEN not set in environment variables")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json"
}

app = Flask(__name__)

# Initialize speech recognition
recognizer = sr.Recognizer()

# Speaker mapping for location-aware responses
SPEAKER_MAP = {
    "kitchen_mic": "media_player.kitchen",
    "bathroom_mic": "media_player.bathroom", 
    "ensuite_mic": "media_player.ensuite",
    "conservatory_mic": "media_player.kitchen",  # fallback to kitchen
}

def transcribe_audio_whisper_api(audio_data):
    """Transcribe audio using OpenAI Whisper API"""
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Save audio data to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file.flush()
            
            # Transcribe using Whisper API
            with open(temp_file.name, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
                
            os.unlink(temp_file.name)  # Clean up temp file
            return transcript.text
            
    except Exception as e:
        print(f"[ERROR] Whisper API transcription failed: {e}")
        return None

def transcribe_audio_google(audio_data):
    """Transcribe audio using Google Speech Recognition (free, offline-capable)"""
    try:
        # Convert audio data to AudioFile
        audio_file = sr.AudioFile(BytesIO(audio_data))
        
        with audio_file as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.record(source)
        
        # Use Google Speech Recognition
        text = recognizer.recognize_google(audio)
        print(f"[STT] Google recognized: '{text}'")
        return text
        
    except sr.UnknownValueError:
        print("[STT] Google could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"[STT] Google error: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] STT processing failed: {e}")
        return None

def transcribe_audio_sphinx(audio_data):
    """Transcribe audio using PocketSphinx (completely offline)"""
    try:
        # Convert audio data to AudioFile
        audio_file = sr.AudioFile(BytesIO(audio_data))
        
        with audio_file as source:
            audio = recognizer.record(source)
        
        # Use PocketSphinx (offline)
        text = recognizer.recognize_sphinx(audio)
        print(f"[STT] Sphinx recognized: '{text}'")
        return text
        
    except sr.UnknownValueError:
        print("[STT] Sphinx could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"[STT] Sphinx error: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Sphinx STT failed: {e}")
        return None

def transcribe_audio(audio_data):
    """Try multiple STT methods in order of preference"""
    print("[STT] Starting transcription...")
    
    # Method 1: Try OpenAI Whisper API (best quality)
    if os.getenv("OPENAI_API_KEY"):
        print("[STT] Trying OpenAI Whisper API...")
        result = transcribe_audio_whisper_api(audio_data)
        if result:
            return result
    
    # Method 2: Try Google Speech Recognition (good quality, requires internet)
    print("[STT] Trying Google Speech Recognition...")
    result = transcribe_audio_google(audio_data)
    if result:
        return result
    
    # Method 3: Try PocketSphinx (offline, lower quality)
    print("[STT] Trying PocketSphinx (offline)...")
    result = transcribe_audio_sphinx(audio_data)
    if result:
        return result
    
    print("[STT] All transcription methods failed")
    return None

def call_service(entity_id, service, service_data=None):
    """Send service call to Home Assistant"""
    domain = entity_id.split(".")[0]
    url = f"{HA_URL}/api/services/{domain}/{service}"
    payload = {"entity_id": entity_id}
    if service_data:
        payload.update(service_data)
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        print(f"[HA] Called {domain}.{service} on {entity_id} | Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Failed to call HA service: {e}")
        return False

def speak_response(message, device="unknown"):
    """Send TTS to appropriate speaker based on device location"""
    room = device.replace("_mic", "").replace("_test", "")
    speaker_entity = SPEAKER_MAP.get(device) or SPEAKER_MAP.get(f"{room}_mic") or SPEAKER_ENTITY
    
    url = f"{HA_URL}/api/services/tts/google_translate_say"
    payload = {
        "entity_id": speaker_entity,
        "message": message
    }
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        print(f"[TTS] Sent to {speaker_entity} ({room}): {message} | Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Failed to send TTS: {e}")
        return False

def handle_voice_command(text, device="unknown"):
    """Process voice command using simple keyword matching"""
    print(f"[COMMAND] Processing: '{text}' from {device}")
    
    text_lower = text.lower()
    
    # Define command patterns
    commands = {
        ("turn off", "conservatory"): {
            "entity": "switch.conservatory_lights_switch_1",
            "service": "turn_off",
            "response": "Turning off conservatory lights"
        },
        ("turn on", "conservatory"): {
            "entity": "switch.conservatory_lights_switch_1", 
            "service": "turn_on",
            "response": "Turning on conservatory lights"
        },
        ("turn off", "kitchen"): {
            "entity": "light.kitchen",
            "service": "turn_off", 
            "response": "Turning off kitchen lights"
        },
        ("turn on", "kitchen"): {
            "entity": "light.kitchen",
            "service": "turn_on",
            "response": "Turning on kitchen lights"
        }
    }
    
    # Find matching command
    matched_command = None
    for (action, target), command_data in commands.items():
        if action in text_lower and target in text_lower:
            matched_command = command_data
            break
    
    if not matched_command:
        response_msg = f"Sorry, I don't understand '{text}'. Try commands like 'turn off conservatory lights'."
        speak_response(response_msg, device)
        return {"reply": response_msg}, 200
    
    # Execute the command in Home Assistant
    success = call_service(matched_command["entity"], matched_command["service"])
    
    if success:
        speak_response(matched_command["response"], device)
        return {"reply": matched_command["response"]}, 200
    else:
        error_msg = f"Failed to {matched_command['service']} {matched_command['entity']}"
        speak_response("Sorry, I couldn't control that device", device)
        return {"error": error_msg}, 500

@app.route("/api/audio_upload", methods=["POST"])
def audio_upload():
    """Handle audio upload from M5Stack"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        device = data.get("device", "unknown")
        timestamp = data.get("timestamp", "")
        audio_data_b64 = data.get("audio_data", "")
        
        print(f"[AUDIO] Received from {device} at {timestamp}")
        
        if audio_data_b64 == "placeholder_for_audio_data":
            # This is a test request
            print("[AUDIO] Test request received")
            return jsonify({"message": "Audio endpoint ready", "status": "test_successful"}), 200
        
        if not audio_data_b64:
            return jsonify({"error": "No audio data received"}), 400
        
        # Decode base64 audio data
        try:
            audio_data = base64.b64decode(audio_data_b64)
        except Exception as e:
            print(f"[ERROR] Failed to decode audio data: {e}")
            return jsonify({"error": "Invalid audio data format"}), 400
        
        # Transcribe the audio
        transcribed_text = transcribe_audio(audio_data)
        
        if not transcribed_text:
            return jsonify({"error": "Speech recognition failed"}), 400
        
        print(f"[STT] Transcribed: '{transcribed_text}'")
        
        # Process the command
        result = handle_voice_command(transcribed_text, device)
        
        return jsonify({
            "transcribed_text": transcribed_text,
            "command_result": result[0],
            "status": "success"
        }), result[1]
        
    except Exception as e:
        print(f"[ERROR] Exception in audio_upload: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/voice_trigger", methods=["POST"])
def voice_trigger():
    """Handle text-based voice commands (for testing)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        user_input = data.get("text", "")
        device = data.get("device", "unknown")
        source = data.get("source", "unknown")
        
        print(f"[VOICE] Received from {device} ({source}): '{user_input}'")
        
        if not user_input.strip():
            return jsonify({"error": "Empty command received"}), 400
        
        result = handle_voice_command(user_input, device)
        status_code = result[1] if isinstance(result, tuple) else 200
        result_data = result[0] if isinstance(result, tuple) else result
        
        return jsonify(result_data), status_code
        
    except Exception as e:
        print(f"[ERROR] Exception in voice_trigger: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Audio MAP server is running",
        "ha_url": HA_URL,
        "stt_methods": ["whisper_api", "google", "sphinx"]
    }), 200

@app.route("/", methods=["GET"])
def root():
    """Root endpoint"""
    return jsonify({
        "service": "Audio MAP (Master Assistant Processor)",
        "status": "running",
        "endpoints": ["/api/audio_upload", "/api/voice_trigger", "/api/health"]
    }), 200

if __name__ == "__main__":
    print("🎙️ Audio MAP (Master Assistant Processor) server starting...")
    print(f"Home Assistant URL: {HA_URL}")
    print(f"Default TTS Speaker: {SPEAKER_ENTITY}")
    print("STT Methods: OpenAI Whisper API, Google Speech, PocketSphinx")
    print("Audio MAP server running on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=True)