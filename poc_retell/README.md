# Bezzit POC — Retell AI voice agent

Validates spec step 2 (section 5): place a real outbound call, driven by a
single hardcoded agent + fake context payload, and check latency, voice
quality, and interruption handling. Retell requires pre-creating an LLM +
agent object (unlike Bland's per-call prompt), so this POC is two scripts.

## Setup

1. Sign up at https://dashboard.retellai.com and grab an API key.
2. In the dashboard's Phone Numbers tab, buy or SIP-import a number — this becomes `RETELL_FROM_NUMBER`. (Retell telephony currently only supports calling US `to_number`s.)
3. `cp .env.example .env` and fill in `RETELL_API_KEY` and `RETELL_FROM_NUMBER`.
4. `pip install -r requirements.txt`
5. `python setup_agent.py` — creates one hardcoded LLM + agent from `context_payload.py`'s `GENERAL_PROMPT`. Copy the printed `RETELL_LLM_ID` / `RETELL_AGENT_ID` into `.env`.

## Run

```
python place_call.py +15551234567
```

Call yourself first. The agent will:
- Open by identifying itself as an automated Bezzit assistant, confirm it's talking to the right person, and disclose recording.
- Ask for the fake outstanding item defined in `context_payload.py` (currently: a PAN card scan for a fictional buyer, Rohan Mehta), injected via `retell_llm_dynamic_variables` at call time.
- Handle a few response paths (agrees to upload / gives data verbally / objects) per spec section 3.3, then end the call via the `end_call` tool.

Edit `CONTEXT` in `context_payload.py` to change the customer/deal/document details — that's the stand-in for the per-call JSON the real Bezzit backend would assemble (spec section 3.2). If you change `GENERAL_PROMPT`, re-run `setup_agent.py` (or use Retell's update-retell-llm endpoint) to push the change.

## What this validates

- Call latency / voice quality / interruption handling on a real call.
- That `{{variable}}` templating from `retell_llm_dynamic_variables` into `general_prompt` works as expected.
- The two-step agent-creation model (LLM object → agent object → call), which is the piece Bland doesn't require.

## What this deliberately skips (not part of this POC)

- The real context-assembly step from Bezzit's backend.
- The post-call webhook → `contact_attempts` write-back (Retell agents can be configured with a `webhook_url`; not wired up here).
- Voicemail detection config, FAQ/objection-handling depth, human-escalation routing, compliance sign-off — see spec section 3.4 before any real customer sees this.
