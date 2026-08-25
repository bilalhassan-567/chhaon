# Chhaon (چھاؤں — "Shade")

[![Live on Vercel](https://img.shields.io/badge/live-chhaon--six.vercel.app-0d9488?style=flat-square)](https://chhaon-six.vercel.app)
[![License: MIT](https://img.shields.io/badge/license-MIT-slategray?style=flat-square)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)](.python-version)

A community heat-injury reporting and preparedness platform for Lahore, built for the
[Smart City Hackathon Lahore 2026](https://smart-city-hackathon-lahore.devpost.com/)
(Track: City Intelligence).

**Live at [chhaon-six.vercel.app](https://chhaon-six.vercel.app)** — the map and Gap
Dashboard are real and running, not mockups.

In 2022, at 50°C across Punjab province — home to roughly 120 million people — **zero**
heat-related deaths were officially recorded (Amnesty International, "Uncounted," May
2025; full source list in [`docs/sources.md`](docs/sources.md)). Chhaon gives anyone —
hospital worker, ambulance crew, community volunteer, ordinary citizen — a one-message
WhatsApp channel to log a suspected heat-related illness, no app or login required, plus
a plain [web form](https://chhaon-six.vercel.app/report) as a second, independent way in
if WhatsApp isn't available. Reports aggregate onto a live map, get correlated against
real temperature data, and are shown next to whatever official figures exist for the
same period, making a documented data gap visible instead of leaving it in expert
reports nobody outside the field reads.

## Status

**Live map, Gap Dashboard, WhatsApp report intake (guided flow, geo-tagging via location
pin, duplicate-detection), a WhatsApp-independent web report form and Web Push alert
channel, alert registration/opt-out on both channels, and the outbound alert threshold
checker are all built, tested (103 automated tests, including real integration tests
against live Firestore), deployed, and wired up against real infrastructure: real
Firestore, and Meta's WhatsApp Cloud API** (not Twilio — Twilio's trial isn't offered in
Pakistan, see `docs/architecture.md`). Deployed on Vercel — see
[Deployment](#deployment) below for why, not Render.

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

Try the WhatsApp-independent path instead: visit `/report` for the web form, or
generate a real VAPID keypair (`python scripts/generate_vapid_keys.py --write-env` —
self-generated, no external account needed) and use the "Get a browser alert for your
area" widget on the map page to subscribe to Web Push alerts.

## How it works

- **WhatsApp incident reporting** — no separate app, no login, works on any phone that
  already has WhatsApp.
- **Web report form** — the same anonymous intake, reachable without WhatsApp at all;
  auto-detects location via the browser, same zone-name fallback as the WhatsApp flow.
- **Live community heat-risk map** — reports aggregated by neighbourhood, overlaid on
  real current/forecast heat-index data.
- **Official-vs-Reported Gap View** — the core feature: an honest, running comparison
  between community-reported signal and whatever official figures exist for the same
  period.
- **Preventive alerts, two independent channels** — plain-language warnings to
  registered at-risk households/workers when a zone's heat index crosses a threshold,
  sent over WhatsApp *and* Web Push (browser notifications) — whichever a resident
  opted into. Neither channel depends on the other being available.

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
Vercel — every layer on a genuinely free tier, no payment card required anywhere in the
stack.

## Deployment

Deploys to [Vercel](https://vercel.com)'s free Hobby plan (genuinely no card required —
Render's Blueprint *and* plain Web Service flows both demanded card verification even on
free services, which conflicts with this project's zero-cost rule, so Vercel is the
actual deploy target). `vercel.json` and `.python-version` are already in the repo;
Vercel auto-detects `app/main.py`'s `FastAPI` instance with zero restructuring needed.

1. On [vercel.com/new](https://vercel.com/new), import the `bilalhassan-567/chhaon`
   GitHub repo.
2. Framework preset: Vercel should auto-detect **Other** / Python from
   `requirements.txt`. Leave build/output settings at their defaults.
3. Add environment variables (**Project Settings → Environment Variables**), values from
   your local `.env`, never from this repo: `STORAGE_BACKEND=firestore`,
   `FIREBASE_CREDENTIALS_JSON` (the service-account key's contents as one-line JSON — no
   persistent disk on Vercel either, so this is the only option, same as Render would
   have needed; minify it in PowerShell:
   `Get-Content path\to\key.json -Raw | ConvertFrom-Json | ConvertTo-Json -Compress`),
   `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`,
   `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_API_VERSION=v21.0`, `ALERT_HEAT_INDEX_THRESHOLD_C=40`,
   `ALERT_COOLDOWN_HOURS=6`, `INTAKE_RATE_LIMIT_MAX_MESSAGES=20`,
   `INTAKE_RATE_LIMIT_WINDOW_MINUTES=60`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
   `VAPID_CLAIMS_EMAIL` (from `python scripts/generate_vapid_keys.py` — no external
   account, just copy the generated values).
4. Deploy. Vercel gives a `*.vercel.app` URL immediately.
5. Update the Meta App Dashboard's WhatsApp → Configuration → Webhook to
   `https://<your-app>.vercel.app/webhooks/whatsapp`, same verify token as
   `WHATSAPP_VERIFY_TOKEN`, then re-subscribe to the `messages` field.
6. Vercel Functions use Fluid compute (kept warm under active traffic, not a hard sleep
   like Render's free tier) but each deploy is still a fresh process — the guided
   WhatsApp conversation's in-memory per-phone state and the intake rate limiter both
   reset on a cold start, same known limitation this project already had on any
   single-instance free host; not a regression introduced by this move.

## WhatsApp test-mode limitation

Meta's WhatsApp Cloud API restricts an app in Development mode to exchanging messages
with only up to 5 phone numbers that have been manually added and OTP-verified in the
App Dashboard's recipient list — and the restriction is **bidirectional**: a message
from an unlisted number never reaches our webhook at all, silently, on Meta's side.
Opening WhatsApp intake to the general public requires Meta Business Verification and
App Review for Advanced Access, neither of which is achievable inside a hackathon
timeline. This is exactly why the [web report form](https://chhaon-six.vercel.app/report)
and Web Push alert channel exist as a first-class second path rather than a fallback
bolted on afterward — anyone can use them today, with zero Meta gating.

## Development notes

Built with AI-assisted development tools as part of the solo build process. All product,
design, and data decisions are the author's own.

## License

[MIT](LICENSE) &mdash; see the LICENSE file.
