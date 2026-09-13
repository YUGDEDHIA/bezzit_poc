# Bezzit POC — Bland AI voice agent

Validates spec step 2 (section 5): place a real outbound call, driven by a
single hardcoded task prompt + fake context payload, and check latency,
voice quality, and interruption handling. No agent object to pre-create —
Bland calls are just a `task` prompt sent per-call.

## Setup

1. Sign up at https://app.bland.ai and grab an API key from the dashboard.
2. `cp .env.example .env` and paste in `BLAND_API_KEY`.
3. `pip install -r requirements.txt`

## Run

```
python place_call.py +15551234567
```

Call yourself first. The agent will:
- Open by identifying itself as an automated Bezzit assistant and disclose recording.
- Ask for the fake outstanding item defined in `context_payload.py` (currently: a PAN card scan for a fictional buyer, Rohan Mehta).
- Handle a few response paths (agrees to upload / gives data verbally / objects / voicemail) per spec section 3.3.

Edit `CONTEXT` in `context_payload.py` to change the customer/deal/document details — that's the stand-in for the per-call JSON the real Bezzit backend would assemble (spec section 3.2).

## What this validates

- Call latency / voice quality / interruption handling on a real call.
- That `{{variable}}` templating from `request_data` into `task` works as expected.
- Voicemail detection + leave-message behavior.

## What this deliberately skips (not part of this POC)

- The real context-assembly step from Bezzit's backend.
- The post-call webhook → `contact_attempts` write-back (set `BLAND_WEBHOOK_URL` if you want to see the raw payload land somewhere, e.g. via an ngrok tunnel to a local listener).
- FAQ/objection-handling depth, human-escalation routing, compliance sign-off — see spec section 3.4 before any real customer sees this.
