# Devpost Project Description — draft

Status: **skeleton**, to be filled in as the build progresses (Day 9 per
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

*(Fill in once the build is further along — see `architecture.md` for the current
component breakdown and stack.)*

## Challenges we ran into

*(Fill in during/after build.)*

## Accomplishments we're proud of

*(Fill in — likely candidates: the gap dashboard framing, zero-cost stack discipline,
solo build under a hard deadline.)*

## What we learned

*(Fill in.)*

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

FastAPI, Jinja2, Leaflet.js, Tailwind CDN, Firebase Firestore, Twilio WhatsApp API,
Open-Meteo API, GitHub Actions, Render.

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
