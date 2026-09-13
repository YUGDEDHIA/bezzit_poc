# Bezzit — Multi-Channel Document Escalation & AI Voice Agent

**Design spec — v1**
**Author:** Yug Dedhia | **Date:** August 19, 2026

## 1. What this system does

A customer (typically a buyer, seller, tenant, or lead in a real estate transaction) needs to submit a document to Bezzit. Bezzit doesn't want to leave this to chance, and doesn't want a human staring at a dashboard deciding who to nudge next. Instead, the system automatically escalates through channels until the customer either responds or the attempt budget is exhausted, and every attempt is logged whether or not the customer ever replies.

The last rung of that ladder is a phone call — but not a human agent reading a script. It's an AI voice agent that has full context on the customer and the specific document(s) required for their deal, and can hold something close to a real conversation: explain what's needed, answer basic questions, and capture the customer's response (confirmation, a verbal answer to a data field, or a reason they can't comply) as structured data.

## 2. Escalation flow

Each outreach "campaign" is tied to one outstanding requirement (e.g., "upload your PAN card" or "confirm co-owner details for Flat 4B"). The system steps through channels on a fixed cadence unless the customer responds or completes the action.

1. **SMS** — automated text with a short message and a tokenized upload link. Wait window: e.g. 24 hours.
2. **Email #1** — automated, same ask, more detail, same link. Wait window: e.g. 24–48 hours.
3. **Email #2** — automated reminder, slightly more urgent tone. Wait window: e.g. 24–48 hours.
4. **AI voice call** — outbound call placed by the voice agent, which has the customer's name, deal context, and exactly what document/data point is outstanding.

If the call also goes unanswered or unresolved, the campaign is marked **exhausted** — not "customer lost," just "we made every reasonable attempt through three channels, roughly six to seven touches, and logged it." That log is the deliverable of a failed campaign: it's what protects Bezzit if the deal later stalls and someone asks "did we even try to get this from the customer?"

Every step — sent, delivered, opened/clicked (where trackable), responded, failed — gets written to a `contact_attempts` table keyed to the customer and the requirement, regardless of outcome. This log, not the document itself, is often the most important artifact for compliance and dispute resolution in a real estate deal.

### 2.1 Trigger logic (who gets escalated, and when)

- Escalation is driven by a scheduler (cron-style job, e.g. every 15–30 min) that scans open requirements and checks: has the wait window elapsed since the last touch, with no response? If yes, fire the next channel.
- A response on *any* channel (document uploaded, link clicked and form completed, "STOP" reply, inbound call) halts the ladder immediately for that requirement.
- The system decides which channel to use next — this isn't manually configured per customer. It's a straight state machine per requirement: `not_started → sms_sent → email1_sent → email2_sent → call_placed → exhausted`, with `responded` as the escape state from any node.

## 3. The AI voice agent

### 3.1 What "context" means here

The agent needs, before it dials:

- Customer identity: name, preferred language, phone number, relationship to the deal (buyer/seller/tenant/landlord/co-owner).
- Deal context: property, transaction stage, deadline if any.
- The specific outstanding item: which document, or which data points (e.g., "PAN number," "co-owner's Aadhaar-linked mobile," "bank account for refund").
- History: what was already sent by SMS/email, whether they opened those, and how many prior attempts have happened, so the agent doesn't repeat itself robotically or contradict what was already said.
- What a "successful" call looks like: verbal confirmation + willingness to upload, or capturing specific verbal data (with a disclosure that this is being recorded and used to prefill their file).

This means the voice agent cannot be a static script. It needs to be handed a **per-call context payload** (assembled by Bezzit's backend, not hardcoded) and reason over it during the conversation — which is why an LLM-orchestrated conversational agent is the right tool, not an IVR tree.

### 3.2 Recommended architecture

```
Bezzit backend (source of truth)
   │  builds per-call context JSON: customer, deal, document requirement, history
   ▼
Voice agent platform (Retell AI or Bland AI) ── places the call via its telephony
   │  runs STT → LLM (with the context injected as system prompt / dynamic variables) → TTS
   │  mid-call: can hit Bezzit webhook to pull/push data (e.g. "check if doc already uploaded")
   ▼
Post-call webhook → Bezzit backend
   │  transcript, structured extraction (confirmed / data captured / refused / no answer),
   │  recording, next action (mark requirement complete, flag for human follow-up, log exhausted)
   ▼
contact_attempts + customer record updated
```

**Platform recommendation:** don't build the phone/speech stack from scratch (raw Twilio + separate STT/LLM/TTS pipeline). It works, but it's materially more engineering effort for latency tuning, interruption handling, and voicemail detection than a managed voice-agent platform, for a startup that wants to ship this fast.

Two reasonable options as of August 2026, based on current comparisons:

- **Retell AI** — pay-as-you-go (~$0.07–0.15/min all-in), ~600ms latency (the rough threshold where callers stop noticing it's AI), strong support for dynamic per-call variables and conditional branching, full API for custom LLM plug-in. Good default choice if you want lower cost at moderate volume and don't mind assembling a bit more yourself.
- **Bland AI** — owns its full stack (model + telephony + infra), which makes it fast to deploy and gives the most predictable single-vendor billing at high call volume; strong voicemail-vs-pickup detection. Trade-off: you're on Bland's hosted models, less flexibility if you later want to swap in your own LLM.

Either is a reasonable pick for a v1; Vapi is a viable third option if you want maximum flexibility to swap STT/LLM/TTS providers independently, at the cost of more integration work and higher realistic per-minute cost.

Whichever platform, the actual "intelligence" — knowing what document is missing, what to ask, what counts as success — lives in the context payload and post-call webhook logic your team controls, not in the platform itself. That's what keeps this specific to Bezzit's real estate use case rather than a generic call bot.

### 3.3 Conversation design (real estate specific)

- **Opening:** identify Bezzit, the deal/property in plain terms, and disclose it's an automated assistant calling on Bezzit's behalf (required — see compliance below).
- **The ask:** state exactly what's missing (e.g., "we still need your PAN card for the sale deed" or "can you confirm your co-owner's mobile number so we can send them the NOC form").
- **Handling responses:**
  - Customer agrees to upload → re-send the link via SMS during/after the call, confirm they received it.
  - Customer gives the data verbally (where the requirement is a data point, not a file) → agent repeats it back for confirmation, captures it as structured output.
  - Customer objects, asks a question, or says "not now" → agent should have a small set of FAQ answers grounded in the deal context (e.g., "why do you need this," "is this safe to share on a call") and, for anything outside that, offer a human callback rather than improvising on legal/financial specifics.
  - No answer / voicemail → leave a short voicemail with a callback number and let SMS/email history stand; don't loop endlessly.
- **Structured output required after every call:** outcome (`confirmed_will_upload`, `data_captured`, `refused`, `no_answer`, `wrong_number`, `escalate_to_human`), any captured field values, and the transcript/recording reference.

### 3.4 Compliance — this is the part most likely to bite you

Since Bezzit is India-based (adjust if not), TRAI rules matter here, and this is genuinely different from a US TCPA-style calling program:

- **This call is a transactional/service follow-up on an existing relationship** (the customer already engaged with Bezzit and has an open document requirement) — that generally falls under implied-consent, 160-series service calling rather than 140-series promotional calling, and does **not** require DND-registry scrubbing the way a cold marketing call would. Still worth a quick legal sign-off before launch, since "transactional" has a specific regulatory meaning and you don't want to accidentally look like telemarketing.
- **DLT registration**: if any part of the flow (the SMS in step 1, or SMS during/after the call) uses templated messaging, the entity, telemarketer, and templates need DLT registration regardless of the voice step.
- **AI disclosure**: the agent should state up front that it's an automated assistant. This is best practice generally and increasingly an explicit expectation in guidance on AI calling in India.
- **Calling window**: stick to reasonable hours (commonly cited good-response windows are ~11am–1pm and 5–8pm IST) even though transactional calls have looser hour restrictions than promotional ones.
- **Recording consent**: if the call is recorded (it should be, to produce a transcript/data capture), say so at the start of the call.
- **Data handling**: if the agent captures sensitive data verbally (PAN, Aadhaar-linked numbers, bank details), that recording/transcript needs the same data-protection handling as any other PII in Bezzit's systems — encryption at rest, access controls, retention limits.

## 4. Data model sketch

- `requirements`: id, customer_id, deal_id, type (document/data_point), description, status, deadline
- `contact_attempts`: id, requirement_id, channel (sms/email/call), sent_at, status (sent/delivered/opened/responded/failed), response_payload
- `voice_calls`: id, contact_attempt_id, provider_call_id, outcome, transcript_url, recording_url, captured_data (JSON), duration
- Escalation state machine lives either as a `current_stage` field on `requirements` or as a derived value from the latest `contact_attempts` row.

## 5. Build order (suggested)

1. Nail the escalation state machine and logging first (SMS → email → email) — this is the lower-risk, higher-certainty part and gives you the `contact_attempts` infrastructure the voice step will also write to.
2. Pick Retell AI or Bland AI, build a single hardcoded test agent and place a real call to yourself with a fake context payload — validate latency, voice quality, and interruption handling before investing in the context-injection pipeline.
3. Build the context-assembly step (backend → per-call JSON) and the post-call webhook (results → backend).
4. Add the FAQ/objection-handling layer and the human-escalation path.
5. Legal/compliance review of the call script and consent language before any customer sees this in production.
6. Pilot on a small, low-stakes requirement type (e.g., "confirm mailing address") before rolling it out to sensitive documents like PAN/Aadhaar/bank details.

## 6. Open questions for you

- Confirm Bezzit's regulatory footing (India-only, or other markets too) — this changes the compliance section materially.
- Do you want the voice agent to attempt to complete the *entire* requirement on the call (e.g., capture PAN number verbally), or only to get a commitment + re-send the link, with actual document upload always happening via the link? The second is lower-risk and easier to build first.
- Volume: how many calls/month roughly? This changes which platform's pricing model wins.