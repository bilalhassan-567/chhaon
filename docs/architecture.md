# System Architecture

## Data flow

```
WhatsApp incident report
        │  (Meta WhatsApp Cloud API webhook)
        ▼
FastAPI intake endpoint
        │  (writes anonymous, aggregate-only record: zone, incident type, timestamp)
        ▼
Firestore (Spark / free tier)
        │
        ▼
Aggregation job ── cross-references ── Open-Meteo temperature / heat-index data (Lahore)
        │
        ▼
Live map  +  Gap dashboard  (FastAPI + Jinja2, Leaflet.js for the map)
        │
        ▼
GitHub Actions scheduled workflow ── checks zone heat-index thresholds
        │
        ▼
Outbound WhatsApp alert (Meta Cloud API) ── to registered at-risk users in affected zones
```

One pipeline, two directions: citizens report incidents in through the same channel that
carries preventive alerts back out. No separate infrastructure for each direction.

**Messaging provider note:** built against Meta's own WhatsApp Cloud API, not a reseller
like Twilio — Twilio's trial credit (needed for its WhatsApp Sandbox) isn't offered in
Pakistan, which only surfaces at signup time. Meta's Cloud API has no such regional
restriction and offers a free test number with 250 conversations/24h even without
business verification.

## Components

| Component | Role |
|---|---|
| **Report intake** | Python FastAPI endpoint receiving WhatsApp messages via Meta's inbound webhook, protected by webhook-signature verification and a per-phone-number rate limit (see Security below). A reporter shares a WhatsApp location pin (preferred — gives a real geo-tag) or types a neighbourhood name (fallback); the handler writes an anonymous, aggregate-only record (zone, coordinates if shared, incident type, timestamp) to Firestore, with coarse duplicate-detection so repeat reports of the same incident don't inflate counts. No names, no exact addresses, no phone numbers persisted. |
| **Temperature correlation** | Pulls current + forecast temperature/heat-index data from Open-Meteo (free, keyless) for Lahore, joined against report density by zone and time window. |
| **API backend** | FastAPI service exposing map data and gap-view data. `firebase-admin` (Python) on top of Firestore for storage. |
| **Alert registration** | Reachable only through the same WhatsApp channel (reply `ALERT ON`, then a zone) — deliberately not an open web form, since a form accepting an arbitrary phone number would let anyone sign up someone else for unwanted messages. A registration always means the phone that sent it opted itself in. `STOP` unsubscribes. |
| **Alert dispatcher** | Python script (`ingestion/alert_check.py`), triggered on a schedule by a free GitHub Actions workflow, checking the current heat-index against a threshold for every zone that has at least one registration, and sending a WhatsApp warning via Meta's Cloud API to registered numbers in that zone — with a cooldown so a threshold that stays crossed doesn't cause repeat alerts every run. |
| **Web app** | FastAPI + Jinja2 server-rendered HTML. Leaflet.js (CDN) for the interactive map — plain JavaScript, no framework, no build step. Tailwind (CDN) for styling. |
| **Gap dashboard** | A second view in the same web app: community-reported count next to whatever official figures are published for the same window, manually curated from the sources in [`sources.md`](sources.md). There is no live official API for this comparison — the UI says so explicitly, it isn't implied to be live. |

## Why this shape

- **Correlated, not raw.** Report counts are always shown against real heat-index data for
  the same period — a spike during a verified heat spell reads differently from a spike
  with no weather context attached.
- **The gap view is the actual product.** Everything upstream of it (intake, correlation)
  exists to feed a dashboard that visualizes the distance between what's reported on the
  ground and what's officially counted — that framing, not the reporting form itself, is
  the innovation being pitched.
- **One channel, two jobs.** The WhatsApp pipeline that takes reports in is the same one
  that pushes alerts out, so one piece of infrastructure does double duty instead of two
  systems being built and maintained separately.
- **Anonymous by construction.** The schema never has a name or exact-address field to
  begin with — this isn't data being stripped later, it was never collected.

Every service above runs on a genuinely free tier with no payment card required — no
paid infrastructure backs this project.

## Security

- **Webhook signature verification.** Every request to the WhatsApp intake endpoint is
  validated against Meta's HMAC-SHA256 request signature (`X-Hub-Signature-256`,
  computed over the raw request body using the app secret) once real credentials are
  configured, so the endpoint can't be used to inject fake reports or drive the alert
  flow from outside WhatsApp.
- **Rate limiting.** A per-phone-number sliding-window limit on the intake webhook
  blocks a single compromised or malicious sender from flooding the pipeline.
- **Alert registration is opt-in by construction, not by validation.** It only exists
  inside the WhatsApp flow, tied to the number Meta verified as the actual sender —
  there is no form anywhere that accepts an arbitrary phone number, which closes off
  the entire class of "register someone else without their consent" abuse.
- **Firestore is never reachable from a client.** All reads/writes go through the
  backend's service-account credentials; `firestore.rules` denies all direct client
  access, closing off Firestore's default open "test mode."
- **Secrets never committed.** `.env` is gitignored; CI secrets (Meta, Firebase) are
  injected via GitHub Actions secrets, never written to the repo.
- **No PII beyond what's operationally necessary.** Reports are anonymous by schema.
  Alert-registration phone numbers are the one exception (required to send the alert),
  stored in a separate collection from report data, never exposed via any API, and
  masked in any diagnostic output (e.g. CI logs).
