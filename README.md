# Jarvis Voice Home

A voice-driven GPT-based assistant that integrates with Home Assistant to control your smart home naturally.

## Features
- Wake word activated voice input (e.g. Atom Echo)
- Sends transcribed text to Flask server
- Uses GPT to detect intents (e.g. "turn on kitchen light")
- Calls Home Assistant REST API to control devices
- Returns spoken response via TTS

## Setup

### 1. Clone the Repo
```bash
git clone https://github.com/YOUR_USERNAME/jarvis-voice-home.git
cd jarvis-voice-home
```

### 2. Install Requirements
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Add Secrets
Create a file called `.env` based on `.env_example` and fill in:
```
OPENAI_API_KEY=...
HA_TOKEN=...
HA_URL=http://homeassistant.local:8123
```

### 4. Run the Server
```bash
python main.py
```

## Voice Input Format
Your ESP device should POST to:
```http
POST http://<your_pi_ip>:5000/api/voice_trigger
Content-Type: application/json
{
  "device": "living_room_mic",
  "text": "Turn on the hallway light"
}
```

## License
MIT
