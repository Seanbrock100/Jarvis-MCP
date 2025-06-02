import openai
import re
import json

openai.api_key = "sk-your-openai-key"  # Replace with your real key or use env var

def summarize_entities(entities):
    summary = []
    for e in entities:
        name = e["attributes"].get("friendly_name", e["entity_id"])
        summary.append(f"{name} ({e['entity_id']})")
    return "\n".join(summary[:50])

def ask_gpt(user_input, entities):
    entity_summary = summarize_entities(entities)

    prompt = f"""
You are Jarvis, a smart home assistant. Here are the user's current Home Assistant devices:
{entity_summary}

The user said: \"{user_input}\"

Respond in JSON like this:
{{
  \"intent\": \"turn_on\",
  \"entity\": \"light.kitchen_ceiling\",
  \"data\": {{ }},
  \"response\": \"Turning on the kitchen light.\"
}}

If unsure, only reply with:
{{ \"response\": \"I'm not sure how to help with that.\" }}
"""

    res = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful smart home assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    content = res.choices[0].message["content"]

    try:
        match = re.search(r"{.*}", content, re.DOTALL)
        parsed = json.loads(match.group()) if match else {"response": content.strip()}
        return parsed
    except Exception as e:
        return {"response": f"Parsing error: {e}"}
