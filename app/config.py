import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# "local" = JSON-file backed store, no account needed, used until Firestore exists.
# "firestore" = real production backend (Day 2+, needs a Firebase project).
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")

LOCAL_REPORTS_FILE = DATA_DIR / "reports.local.json"
LOCAL_REGISTRATIONS_FILE = DATA_DIR / "registrations.local.json"
LOCAL_ALERT_STATE_FILE = DATA_DIR / "alert_state.local.json"
ZONES_FILE = DATA_DIR / "zones.json"

# Lahore centroid, used for the city-wide current heat-index reading.
LAHORE_LAT = 31.5497
LAHORE_LON = 74.3436

# Dedup window for the report intake pipeline (PS3's "duplicate-detection" ask).
DEDUP_WINDOW_MINUTES = 30
DEDUP_RADIUS_METERS = 200

# Rate limit on the WhatsApp intake webhook, per sender phone number. Generous enough
# for a real multi-message conversation (welcome -> location -> incident type, plus a
# retry or two) while blocking a flood from one number. See RULES.md's Security section.
INTAKE_RATE_LIMIT_MAX_MESSAGES = int(os.getenv("INTAKE_RATE_LIMIT_MAX_MESSAGES", "20"))
INTAKE_RATE_LIMIT_WINDOW_MINUTES = int(os.getenv("INTAKE_RATE_LIMIT_WINDOW_MINUTES", "60"))

# "Dangerous" apparent-temperature threshold that triggers a preventive alert. A
# configurable placeholder, not sourced from a specific medical/meteorological
# guideline — tune with domain input before relying on it for real safety decisions.
ALERT_HEAT_INDEX_THRESHOLD_C = float(os.getenv("ALERT_HEAT_INDEX_THRESHOLD_C", "40"))
# Minimum time between two alerts for the same zone, so a threshold that stays crossed
# across multiple cron runs doesn't flood registered users with repeat warnings.
ALERT_COOLDOWN_HOURS = float(os.getenv("ALERT_COOLDOWN_HOURS", "6"))

# Meta WhatsApp Cloud API (switched from Twilio 22 Aug 2026 — Twilio's trial isn't
# offered in Pakistan; see docs/master-workout/PROGRESS.md for the full reasoning).
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
# HMAC-SHA256 key for verifying the X-Hub-Signature-256 header on inbound webhooks —
# see app/services/whatsapp_api.py.
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")
# Arbitrary string chosen by us, not issued by Meta — must match what's entered in the
# Meta App Dashboard's webhook configuration; checked during the GET verification
# handshake before Meta will send real message webhooks.
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")

FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
# Alternative to FIREBASE_CREDENTIALS_PATH for CI: the full service-account JSON as a
# single-line string secret (GitHub Actions can't easily mount a key file). If set,
# takes precedence over FIREBASE_CREDENTIALS_PATH.
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "")

# Web Push (RFC 8292 VAPID) — a secondary, WhatsApp-independent channel: citizens can
# report via a plain web form (app/routes/report.py) and opt into browser push alerts
# (app/routes/push.py) instead of/alongside WhatsApp. Unlike every other credential in
# this project, these have no external account behind them — generate with
# scripts/generate_vapid_keys.py, a self-contained EC keypair, no signup, no card.
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
# The "mailto:" contact VAPID's spec requires — push services use it to reach you if
# your server misbehaves (e.g. spamming a user). Not a secret.
VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "mailto:example@example.com")

LOCAL_PUSH_SUBSCRIPTIONS_FILE = DATA_DIR / "push_subscriptions.local.json"

# Rate limit on the web report form, per submitting IP address — a WhatsApp message
# has some inherent friction (you need a WhatsApp account); an open web form has less,
# so this needs its own limit rather than assuming WhatsApp's is enough. Same
# per-key sliding-window limiter as the WhatsApp webhook (app/services/rate_limit.py).
WEB_REPORT_RATE_LIMIT_MAX_MESSAGES = int(os.getenv("WEB_REPORT_RATE_LIMIT_MAX_MESSAGES", "20"))
WEB_REPORT_RATE_LIMIT_WINDOW_MINUTES = int(os.getenv("WEB_REPORT_RATE_LIMIT_WINDOW_MINUTES", "60"))
