# Devpost Project Description — draft

Status: **draft content filled in**, deployed and working as of this writing — still
needs a final pass once the demo video and live screenshots exist (Day 9/10 per
`master-workout/PLAN.md`). Structure below maps directly to what Devpost asks for.

---

## Inspiration / Problem

In 2022, at 50°C across Punjab province — home to roughly 120 million people — **zero**
heat-related deaths were officially recorded. Fewer than 5% of all deaths in Pakistan are
registered in any way, and heat-related deaths are especially likely to be filed under an
unrelated cause such as cardiac arrest (Amnesty International, "Uncounted," May 2025 —
full citation list in [`../sources.md`](../sources.md)).

Lahore-specific ground truth exists only as scattered news snapshots: 72 people were
admitted for heatstroke across five named Lahore public hospitals in a single 24-hour
window in late May 2024 — a real, sourced number that vanished from public view the next
day. There is no continuous, neighbourhood-level, publicly visible signal.

*(Expand with the "why it matters" framing from the master doc §2.2 once drafting for
submission — who's most exposed, why current data misses them.)*

## What it does

- **WhatsApp incident reporting** — no separate app to install, no login, works on any
  phone that already has WhatsApp: send a message, drop a location pin, done.
- **Live community heat-risk map** — reports aggregated by neighbourhood, overlaid on
  real current/forecast heat-index data.
- **Official-vs-Reported Gap View** — the signature feature: a running, honest comparison
  between ground-reported signal and whatever official figures exist for the same period.
- **Preventive alerts** — the same channel in reverse: plain-language WhatsApp warnings to
  registered at-risk households/workers when a zone's heat index crosses a threshold.
- **Anonymous by design** — no names, no exact addresses, ever.

## How we built it

A Python FastAPI backend with server-rendered Jinja2 templates, Leaflet.js for the map,
and Tailwind for styling — deliberately no frontend build step. Reports arrive through
Meta's WhatsApp Cloud API webhook, get geo-tagged via a shared location pin (or a typed
neighbourhood as fallback), and are deduplicated automatically when a matching report
lands in the same zone within a short time window, before landing in Firebase Firestore.
A GitHub Actions cron job checks live Open-Meteo heat-index data against registered
zones and sends preventive WhatsApp warnings when a threshold is crossed. The whole
stack runs on genuinely free tiers, deployed on Vercel. See `architecture.md` for the
full component breakdown.

## Challenges we ran into

Two real infrastructure pivots, both forced by regional/platform constraints rather than
a design change: Twilio's WhatsApp Sandbox trial isn't offered for accounts signing up
from Pakistan, so the entire messaging layer — webhook signature verification, message
parsing, outbound sends — was rebuilt against Meta's WhatsApp Cloud API directly.
Separately, Render's free tier turned out to require credit card verification for both
its Blueprint and plain Web Service deploy flows despite advertising a card-free tier,
so deployment moved to Vercel instead, which needed the app restructured for a
serverless execution model rather than a long-running process.

## Accomplishments we're proud of

The Gap Dashboard leading with a direct, single-glance comparison: zero heat deaths
officially recorded in Punjab during 2022's 50°C heatwave, next to Chhaon's own live
count, sourced and cited rather than asserted. Also: real duplicate-detection working
end-to-end (not just designed) — two reports from the same neighbourhood within a short
window merge into one record instead of double-counting — and keeping every demo/seed
data point honestly distinguishable from real WhatsApp reports everywhere it's shown,
rather than quietly blending the two to make the map look busier.

## What we learned

How much of "making a data gap visible" is a data-honesty problem before it's a
data-visualization problem — the hardest design decisions here weren't chart choices,
they were about what *not* to claim (never presenting the official-figures panel as a
live feed, never blending seeded demo reports into the real WhatsApp count, being
explicit that this is a community-reported signal and not a medical or legal record).

## What's next

An **SMS/voice alert channel** for outdoor workers and households without smartphones or
a data plan — the WhatsApp alert layer covers connected users today, but reaching the
least-connected residents (Problem Statement 5's explicit focus) means a channel that
doesn't require a smartphone app at all. Also: hospital-partner integration, and a
verified official data feed if one becomes available. The same architecture needs no
Lahore-specific assumption — it runs for any Pakistani city with basic hospital/community
reporting, because the underlying data gap (Amnesty's report covers Sindh and Punjab
both) is documented as national, not local.

## Built with

FastAPI, Jinja2, Leaflet.js, Tailwind CDN, Firebase Firestore, Meta WhatsApp Cloud API,
Open-Meteo API, GitHub Actions, Vercel.

## Submission category

**City Intelligence** — directly synthesizes **Problem Statement 3, "Turning Citizens
Into Verified Sensors"** (the WhatsApp reporting layer: geo-tagged via shared location
pin, timestamped, aggregated into a verifiable public record). Problem Statement 5,
"Making City Intelligence Reach Everyone," is named as the explicit next step — an
SMS/voice channel for residents without smartphones — rather than claimed as already
solved by the current WhatsApp build, since PS5's own premise is that an app-based
channel alone doesn't reach that audience. Public Preparedness relevance stated as
secondary.

## AI-assisted development

Built with AI-assisted development tools as part of the solo build process. All product,
design, and data decisions are the author's own.
