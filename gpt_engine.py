import os
import json
import traceback
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def ask_gpt(text, entities):
    entity_names = [e["entity_id"] for e in entities]
    prompt = (
        f"You are a smart home assistant. The user said: '{text}'. "
        f"Available devices: {', '.join(entity_names)}.\n\n"
        f"Respond with a JSON object like this:\n"
        f'{{"entity": "light.kitchen", "intent": "turn_on", "response": "Turning on the kitchen light."}}\n\n'
        f"Only include known entities."
    )

    try:
        chat_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You help interpret smart home voice commands."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        reply = chat_response.choices[0].message.content
        return json.loads(reply)
    except Exception as e:
        return {
            "response": f"Failed to understand the command: {str(e)}",
            "debug_prompt": prompt,
            "traceback": traceback.format_exc()
        }