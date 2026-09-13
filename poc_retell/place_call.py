"""
POC: place one outbound test call via Retell AI, using the agent created by
setup_agent.py and a hardcoded, fake per-call context payload injected as
dynamic variables.

Usage:
    python place_call.py +15551234567
"""

import os
import sys

import requests
from dotenv import load_dotenv

from context_payload import CONTEXT

load_dotenv()

RETELL_API_KEY = os.environ["RETELL_API_KEY"]
FROM_NUMBER = os.environ["RETELL_FROM_NUMBER"]  # must be a number bought/imported in Retell
AGENT_ID = os.environ["RETELL_AGENT_ID"]  # from setup_agent.py output
BASE_URL = "https://api.retellai.com"


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python place_call.py <phone_number_in_E.164, e.g. +15551234567>")
        sys.exit(1)

    to_number = sys.argv[1]

    resp = requests.post(
        f"{BASE_URL}/v2/create-phone-call",
        headers={
            "Authorization": f"Bearer {RETELL_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from_number": FROM_NUMBER,
            "to_number": to_number,
            "override_agent_id": AGENT_ID,
            "retell_llm_dynamic_variables": CONTEXT,
            "metadata": {"poc": "retell", "requirement_type": CONTEXT["outstanding_item_type"]},
        },
        timeout=30,
    )
    resp.raise_for_status()
    print(resp.json())


if __name__ == "__main__":
    main()
