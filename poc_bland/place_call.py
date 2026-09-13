"""
POC: place one outbound test call via Bland AI using a hardcoded, fake
per-call context payload.

This is step 2 of the spec's build order -- validate latency, voice quality,
and interruption handling on a real call before building the real
context-injection pipeline.

Usage:
    python place_call.py +15551234567
"""

import os
import sys

import requests
from dotenv import load_dotenv

from context_payload import CONTEXT, TASK_TEMPLATE

load_dotenv()

BLAND_API_KEY = os.environ["BLAND_API_KEY"]
BLAND_BASE_URL = os.environ.get("BLAND_BASE_URL", "https://us.api.bland.ai")
WEBHOOK_URL = os.environ.get("BLAND_WEBHOOK_URL")  # optional, for the post-call POC


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python place_call.py <phone_number_in_E.164, e.g. +15551234567>")
        sys.exit(1)

    phone_number = sys.argv[1]

    payload = {
        "phone_number": phone_number,
        "task": TASK_TEMPLATE,
        "request_data": CONTEXT,
        "voice": "june",
        "record": True,
        "wait_for_greeting": True,
        "max_duration": 8,  # minutes; keep short for a test call
        "voicemail": {
            "action": "leave_message",
            "message": (
                f"Hi {CONTEXT['customer_name']}, this is an automated call from "
                f"Bezzit about {CONTEXT['property']}. We still need "
                f"{CONTEXT['outstanding_item_description']}. Please call us back "
                f"at {CONTEXT['callback_number']}."
            ),
        },
        "metadata": {"poc": "bland", "requirement_type": CONTEXT["outstanding_item_type"]},
    }

    if WEBHOOK_URL:
        payload["webhook"] = WEBHOOK_URL

    resp = requests.post(
        f"{BLAND_BASE_URL}/v1/calls",
        headers={
            "Authorization": BLAND_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    print(resp.json())


if __name__ == "__main__":
    main()
