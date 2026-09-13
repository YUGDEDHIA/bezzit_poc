"""
POC: one-time setup that creates a single hardcoded Retell LLM + agent to
test against. Run this once, then put the printed agent_id into your .env
and use place_call.py to actually dial.

Usage:
    python setup_agent.py
"""

import os

import requests
from dotenv import load_dotenv

from context_payload import BEGIN_MESSAGE, GENERAL_PROMPT

load_dotenv()

RETELL_API_KEY = os.environ["RETELL_API_KEY"]
BASE_URL = "https://api.retellai.com"
HEADERS = {
    "Authorization": f"Bearer {RETELL_API_KEY}",
    "Content-Type": "application/json",
}

# Pick a real voice_id for your account: GET https://api.retellai.com/list-voices
VOICE_ID = os.environ.get("RETELL_VOICE_ID", "11labs-Adrian")


def main() -> None:
    llm_resp = requests.post(
        f"{BASE_URL}/create-retell-llm",
        headers=HEADERS,
        json={
            "general_prompt": GENERAL_PROMPT,
            "begin_message": BEGIN_MESSAGE,
            "model": "gpt-4.1",
            "general_tools": [
                {
                    "type": "end_call",
                    "name": "end_call",
                    "description": "End the call once the ask has been made and next steps are stated, or if it's voicemail.",
                }
            ],
        },
        timeout=30,
    )
    llm_resp.raise_for_status()
    llm = llm_resp.json()
    print("Created Retell LLM:", llm["llm_id"])

    agent_resp = requests.post(
        f"{BASE_URL}/create-agent",
        headers=HEADERS,
        json={
            "response_engine": {"type": "retell-llm", "llm_id": llm["llm_id"]},
            "voice_id": VOICE_ID,
            "agent_name": "Bezzit document escalation POC",
            "language": "en-US",
        },
        timeout=30,
    )
    agent_resp.raise_for_status()
    agent = agent_resp.json()
    print("Created Retell agent:", agent["agent_id"])

    print("\nAdd these to your .env:")
    print(f"RETELL_LLM_ID={llm['llm_id']}")
    print(f"RETELL_AGENT_ID={agent['agent_id']}")


if __name__ == "__main__":
    main()
