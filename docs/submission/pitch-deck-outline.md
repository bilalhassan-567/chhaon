# Presentation Deck — content

Status: full slide-by-slide content drafted (Aug 24 2026). Portable — paste directly
into PowerPoint/Google Slides/Keynote. A visual HTML version exists too (see the
artifact built alongside this). Screenshots referenced below now exist (map, Gap
Dashboard, report form) — insert the real ones, not placeholders, before presenting.

Every number on every slide traces to [`../sources.md`](../sources.md). Nothing here
should ever be rounded up, extrapolated, or restated more dramatically than the source.

---

## 1. Title

**Chhaon** (چھاؤں — "Shade")
Community heat-injury reporting and preparedness for Lahore

Smart City Hackathon Lahore 2026 · Track: City Intelligence
Live: chhaon-six.vercel.app

*Speaker note: say the name once, in Urdu and English, before anything else — it's the whole metaphor for the product (community-provided shade/relief where official coverage doesn't reach).*

---

## 2. The problem, in one verified number

**In 2022, at 50°C across Punjab — home to ~120 million people — zero heat-related deaths were officially recorded.**

Fewer than 5% of all deaths in Pakistan are registered in any way.
— Amnesty International, *"Uncounted,"* May 2025

*Speaker note: let this land in silence for a beat before moving on. It's the entire pitch in one sentence — don't undercut it by rushing to the next slide.*

---

## 3. This isn't a one-off — it's a pattern

- **Karachi, 2024 heatwave**: 427 deaths officially attributed — Amnesty's investigation found **over 95%** of that crisis's actual fatalities were catalogued under other diagnoses.
- **Lahore, late May 2024**: 72 people admitted for heatstroke in five public hospitals in a single 24-hour window — a real, sourced number that **vanished from public view the next day**. No running tally exists.
- **Nationally, 2024**: 568+ recorded deaths, 5,300+ hospital admissions — figures the reporting itself flags as understating the true toll.

*Speaker note: the point isn't "more deaths than reported" as a vague claim — it's that verifiable snapshots exist and then disappear. There's no continuous public signal, even when the underlying data briefly surfaces.*

---

## 4. Who this misses

Outdoor labourers, street vendors, elderly residents in poorly ventilated housing, informal-settlement dwellers — the people most exposed to heat are also the least likely to appear in hospital-admission records at all, let alone a national mortality count.

*Speaker note: connects the abstract undercount stat to specific, real people — sets up why a zero-friction reporting channel (no app, no account, no clinic visit) matters specifically for this population.*

---

## 5. Chhaon, in one sentence

**A WhatsApp message — or a plain web form — turns anyone into a verified sensor for their own neighbourhood, with zero app to install and zero account to create.**

Report a suspected heat-related incident → it's geo-tagged, timestamped, and on a live public map in seconds → correlated against real heat-index data for that moment → compared honestly against whatever official figures exist for the same period.

---

## 6. The Gap Dashboard — the actual innovation

Not the reporting form. **The dashboard that makes the undercount visible, live, with citations.**

> **0** officially recorded (Punjab, 2022, 50°C)
> **[live count]** reported to Chhaon right now

Deliberately *not* framed as a same-period comparison — the left side is dated, cited historical fact; the right side is today's live signal. The point isn't "we caught more than the government" — it's **making a documented, real gap visible instead of leaving it buried in a report nobody outside the field reads.**

*Speaker note: this is the slide to slow down on. Show the actual live dashboard here if presenting from a laptop — the real number changing in front of judges is more persuasive than any static slide.*

---

## 7. It's real, not a mockup — live product

*(Insert real screenshots: live map with report markers, Gap Dashboard with the punchline banner, the web report form, a WhatsApp conversation screenshot if the allowlist issue resolves in time.)*

Every screenshot in this deck is the actual deployed product at chhaon-six.vercel.app — not a Figma file.

---

## 8. Built for resilience — two independent channels

WhatsApp intake and alerts depend on Meta's infrastructure being correctly configured. So Chhaon also has a **second, fully independent path that depends on nothing but the app itself being online**:

- A plain **web report form** (auto-detects location via the browser) — same anonymous storage, same dedup logic, same map.
- **Web Push browser alerts** — self-generated cryptographic keys (VAPID), no external account, no third-party push provider, no card.

If one channel has a bad day, the system doesn't go dark. This is the same instinct as building the Gap Dashboard's official-figures side as manually curated rather than pretending a live feed exists: **be honest about what depends on what, and don't let a single external dependency be a single point of failure.**

---

## 9. Anonymous by design — not by policy

No names. No exact addresses. No phone numbers stored with a report, on either channel. Only zone, incident type, and timestamp are ever collected.

The dashboard itself states, visibly: **"Community-reported signal — not a verified medical or legal record."** This isn't a disclaimer buried in terms of service — it's on the page a judge is looking at right now.

---

## 10. Real infrastructure, genuinely zero cost

FastAPI · Firebase Firestore · Meta WhatsApp Cloud API · Web Push (VAPID) · Open-Meteo · GitHub Actions · Vercel

Every layer runs on a real free tier — **no payment card entered anywhere, at any point**, including when that meant switching hosting providers mid-build after one demanded card verification despite advertising a free tier.

---

## 11. Impact & scalability

The underlying data gap Amnesty documented covers **Sindh and Punjab both** — this is a national pattern, not a Lahore-only one. The same architecture runs for any Pakistani city with basic hospital/community reporting; nothing about the design is Lahore-specific except the current zone list.

---

## 12. What's next

- **SMS/voice alert channel** for outdoor workers and households without a smartphone or data plan — named honestly as a roadmap item (Problem Statement 5's explicit ask), not claimed as already solved by the WhatsApp/web build.
- Hospital-partner integration for a verified secondary data source.
- A real official data feed, if one is ever made available to integrate against.

---

## 13. Thank you

**Chhaon** — چھاؤں
chhaon-six.vercel.app · github.com/bilalhassan-567/chhaon

Built solo for the Smart City Hackathon Lahore 2026, City Intelligence track.
