# System Architecture

## Data flow

```
WhatsApp incident report          Web report form (browser Geolocation API)
        │ (Meta webhook)                  │ (POST /api/report)
        ▼                                 ▼
        └──────────────┬──────────────────┘
                        ▼
        FastAPI intake — writes anonymous, aggregate-only record:
        zone, incident type, timestamp, source channel
                        │
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
        ┌───────────────┴───────────────┐
        ▼                                ▼
Outbound WhatsApp alert          Outbound Web Push notification
(Meta Cloud API)                 (VAPID, browser-native)
to WhatsApp-registered users     to browser-subscribed users
in affected zones                in affected zones
```

Two independent, symmetric pipelines rather than one: WhatsApp in/out, and a plain web
form + browser Web Push in/out. Neither depends on the other being available — a citizen
can report and a resident can get alerted through either channel, and the map/dashboard
show data from both, honestly labeled by which one it came through.

**Messaging provider note:** built against Meta's own WhatsApp Cloud API, not a reseller
like Twilio — Twilio's trial credit (needed for its WhatsApp Sandbox) isn't offered in
Pakistan, which only surfaces at signup time. Meta's Cloud API has no such regional
restriction and offers a free test number with 250 conversations/24h even without
business verification.

**Secondary channel note:** the web form + Web Push channel exists because WhatsApp
delivery depends on Meta's test-number recipient allowlist being set up correctly on
their side — a real dependency outside this project's control. The web channel needs
nothing from Meta at all: Web Push (RFC 8292, VAPID) authenticates directly against
each browser's own push service using a self-generated keypair, no external account,
no signup, no card — see `scripts/generate_vapid_keys.py`.

## Components

| Component | Role |
|---|---|
| **Report intake (WhatsApp)** | Python FastAPI endpoint receiving WhatsApp messages via Meta's inbound webhook, protected by webhook-signature verification and a per-phone-number rate limit (see Security below). A reporter shares a WhatsApp location pin (preferred — gives a real geo-tag) or types a neighbourhood name (fallback); the handler writes an anonymous, aggregate-only record (zone, coordinates if shared, incident type, timestamp, source channel) to Firestore, with coarse duplicate-detection so repeat reports of the same incident don't inflate counts. No names, no exact addresses, no phone numbers persisted. |
| **Report intake (web form)** | `/report` — a plain HTML form using the browser's Geolocation API to auto-detect the reporter's position (same zone-name fallback as WhatsApp), POSTing to the same `add_or_increment` storage path, tagged with a distinct source so it's honestly distinguishable from WhatsApp reports everywhere the map/dashboard disclose real-vs-demo data. Rate-limited per submitting IP address rather than per phone number, since a web form has less inherent friction than needing a WhatsApp account. |
| **Temperature correlation** | Pulls current + forecast temperature/heat-index data from Open-Meteo (free, keyless) for Lahore, joined against report density by zone and time window. |
| **API backend** | FastAPI service exposing map data and gap-view data. `firebase-admin` (Python) on top of Firestore for storage. |
| **Alert registration (WhatsApp)** | Reachable only through the same WhatsApp channel (reply `ALERT ON`, then a zone) — deliberately not an open web form, since a form accepting an arbitrary phone number would let anyone sign up someone else for unwanted messages. A registration always means the phone that sent it opted itself in. `STOP` unsubscribes. |
| **Alert registration (Web Push)** | A "Get a browser alert for your area" widget on the map page, using the standard `PushManager.subscribe()` browser API. Genuinely safe as an open endpoint (unlike a phone-number form): a push subscription's endpoint/keys are issued by the browser's own push service only to whoever is looking at the page — there's no way to register a stranger's browser through it. |
| **Alert dispatcher** | Python script (`ingestion/alert_check.py`), triggered on a schedule by a free GitHub Actions workflow, checking the current heat-index against a threshold for every zone that has at least one registration on *either* channel, and sending a warning via Meta's Cloud API and/or Web Push (VAPID) to whichever channel(s) that zone's registrants opted into — one shared per-zone cooldown across both channels, so a threshold that stays crossed doesn't cause repeat alerts every run. |
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
- **One channel, two jobs — twice over.** Both the WhatsApp pipeline and the web/Web
  Push pipeline take reports in and push alerts out through the same infrastructure
  each, rather than separate systems per direction. The *two channels* are
  deliberately redundant with each other, though: WhatsApp delivery depends on Meta's
  side being correctly configured (an external dependency outside this project's
  control), while the web channel depends on nothing but this app being reachable.
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
- **Rate limiting.** A per-phone-number sliding-window limit on the WhatsApp intake
  webhook, and a separate per-IP-address limit on the web report form, block a single
  compromised or malicious sender/connection from flooding the pipeline.
- **Alert registration is opt-in by construction, not by validation.** The WhatsApp
  side only exists inside the WhatsApp flow, tied to the number Meta verified as the
  actual sender — there is no form anywhere that accepts an arbitrary phone number,
  which closes off the entire class of "register someone else without their consent"
  abuse. The Web Push side is an open endpoint by design, and that's safe here for a
  different reason: a push subscription's endpoint/keys are issued by the browser's
  own push service only to the page that called `PushManager.subscribe()` — there's
  no equivalent "register a stranger" abuse vector to guard against, since you
  fundamentally cannot subscribe on behalf of someone else's browser.
- **Firestore is never reachable from a client.** All reads/writes go through the
  backend's service-account credentials; `firestore.rules` denies all direct client
  access, closing off Firestore's default open "test mode."
- **Secrets never committed.** `.env` is gitignored; CI secrets (Meta, Firebase) are
  injected via GitHub Actions secrets, never written to the repo.
- **No PII beyond what's operationally necessary.** Reports are anonymous by schema.
  Alert-registration phone numbers are the one exception (required to send the alert),
  stored in a separate collection from report data, never exposed via any API, and
  masked in any diagnostic output (e.g. CI logs).
