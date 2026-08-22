# Chhaon (چھاؤں — "Shade")

A community heat-injury reporting and preparedness platform for Lahore, built for the
[Smart City Hackathon Lahore 2026](https://smart-city-hackathon-lahore.devpost.com/)
(Track: City Intelligence).

In 2022, at 50°C across Punjab province — home to roughly 120 million people — **zero**
heat-related deaths were officially recorded (Amnesty International, "Uncounted," May
2025; full source list in [`docs/sources.md`](docs/sources.md)). Chhaon gives anyone —
hospital worker, ambulance crew, community volunteer, ordinary citizen — a one-message
WhatsApp channel to log a suspected heat-related illness, no app or login required.
Reports aggregate onto a live map, get correlated against real temperature data, and are
shown next to whatever official figures exist for the same period, making a documented
data gap visible instead of leaving it in expert reports nobody outside the field reads.

## Status

**Live map, Gap Dashboard, WhatsApp report intake (guided flow, geo-tagging via location
pin, duplicate-detection), alert registration/opt-out, and the outbound alert threshold
checker are all built, tested (78 automated tests, including real integration tests
against live Firestore), and wired up against real infrastructure: real Firestore, and
Meta's WhatsApp Cloud API** (not Twilio — Twilio's trial isn't offered in Pakistan, see
`docs/architecture.md`). The Render deployment itself hasn't happened yet.

## Setup & run

```bash
python -m venv venv
venv\Scripts\activate            # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env             # defaults to STORAGE_BACKEND=local, no account needed
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000` for the live map. Simulate an inbound WhatsApp message
without a real Meta webhook by POSTing Meta's payload shape directly, e.g.:

```bash
curl -X POST http://127.0.0.1:8000/webhooks/whatsapp -H "Content-Type: application/json" -d '{
  "object": "whatsapp_business_account",
  "entry": [{"id": "waba", "changes": [{"value": {"messaging_product": "whatsapp",
    "messages": [{"from": "923001234567", "id": "wamid.1", "timestamp": "0", "type": "text", "text": {"body": "hi"}}]}}]}]
}'
```

Run the test suite: `pytest` (Firestore integration tests auto-skip if no Firebase
credentials are configured, so this works with zero setup too).

Register for alerts, or send a report, entirely through the same webhook — reply
`ALERT ON` instead of a location to opt into heat warnings for a zone, or `STOP` to
opt out. Try the threshold checker without sending anything real: `python
ingestion/alert_check.py --dry-run`.

## How it works

- **WhatsApp incident reporting** — no separate app, no login, works on any phone that
  already has WhatsApp.
- **Live community heat-risk map** — reports aggregated by neighbourhood, overlaid on
  real current/forecast heat-index data.
- **Official-vs-Reported Gap View** — the core feature: an honest, running comparison
  between community-reported signal and whatever official figures exist for the same
  period.
- **Preventive alerts** — the same WhatsApp channel in reverse: plain-language warnings
  to registered at-risk households/workers when a zone's heat index crosses a threshold.

See [`docs/architecture.md`](docs/architecture.md) for the full system design, including
its [Security section](docs/architecture.md#security) — webhook signature verification,
rate limiting, opt-in-only alert registration, locked-down Firestore rules, and secret
handling.

## Data & ethics

Chhaon is a **community-reported signal layer, not a verified medical or legal record**.
No names, no exact addresses — only rough zone, incident type, and timestamp are ever
collected. This distinction is shown on the dashboard UI itself, not just documented
here.

## Tech stack

Python (FastAPI + Jinja2), Leaflet.js (CDN) for the map, Tailwind (CDN) for styling,
Firebase Firestore for storage, Meta WhatsApp Cloud API for messaging, Open-Meteo for
temperature/heat-index data, GitHub Actions for scheduled alert checks, hosted on
Render — every layer on a genuinely free tier, no payment card required anywhere in the
stack.

## Deployment

Deploys to [Render](https://render.com)'s free Web Service tier via the included
[`render.yaml`](render.yaml) blueprint:

1. On [dashboard.render.com](https://dashboard.render.com), **New → Blueprint**, connect
   the `bilalhassan-567/chhaon` GitHub repo. Render reads `render.yaml` automatically.
2. It will ask for the env vars marked secret in the blueprint — paste each one from your
   local `.env` (never from this repo): `FIREBASE_CREDENTIALS_JSON` (the service-account
   key as one-line JSON — see below), `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`,
   `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`.
3. `FIREBASE_CREDENTIALS_JSON` needs the *contents* of the service-account key file as a
   single-line JSON string (Render has no persistent disk to point
   `FIREBASE_CREDENTIALS_PATH` at) — minify it, e.g. in PowerShell:
   `Get-Content path\to\key.json -Raw | ConvertFrom-Json | ConvertTo-Json -Compress`.
4. Confirm plan is **Free** (already set in the blueprint) and deploy.
5. Once live, take the Render URL and update it in two places: the Meta App Dashboard's
   WhatsApp → Configuration → Webhook (`https://<your-app>.onrender.com/webhooks/whatsapp`,
   same verify token as `WHATSAPP_VERIFY_TOKEN`), and re-subscribe to the `messages` field.
6. Free-tier services spin down after 15 minutes idle and cold-start on the next request —
   expected, not a bug; worth mentioning in the demo.

## Development notes

Built with AI-assisted development tools as part of the solo build process. All product,
design, and data decisions are the author's own.

## License

TBD.
