# Verified Statistics & Sources

Every number below was checked against a live source before being included. Use these,
cited, in the pitch, README, and UI. **Do not reuse the two figures flagged at the
bottom** — they could not be independently verified.

| Statistic | Source |
|---|---|
| In 2022, at 50°C across Punjab province (population ~120 million), **zero** heat-related deaths were officially recorded; fewer than 5% of all deaths in Pakistan are registered in any way. | Amnesty International, *"Uncounted: Invisible deaths of older people and children during climate disasters in Pakistan,"* May 2025. |
| Karachi officially attributed 427 deaths to the 2024 heatwave; Amnesty found over 95% of fatalities in that crisis were catalogued under other diagnoses. | Amnesty International 2025 report, as reported by Inside Climate News, June 2025. |
| The 2024 Pakistan heat wave produced 568+ recorded deaths and 5,300+ (some tallies: 7,900+) hospital admissions nationally, concentrated in Sindh. | 2024 Pakistan heat wave event reporting (AP/BBC-sourced aggregation). |
| In a single 24-hour window in late May 2024, 72 people were admitted for heatstroke across five named Lahore public hospitals (Services, General, Mayo, Jinnah, Sir Ganga Ram). | Dawn, *"Dozens in hospital with heatstroke as country sizzles,"* 29 May 2024. |
| Lahore's air-quality index exceeded 1,000 in early November 2024, with a reading of 1,900 reported near the Pakistan–India border by the provincial government and IQAir — described as unprecedented, prompting a week-long primary school closure. | Reuters / NBC News / Al Jazeera, 3–4 November 2024. |

## Do not use — unverified

- A specific **"AQI 1,165, world record"** figure. The verified figure is that Lahore's
  AQI exceeded 1,000, with a 1,900 reading reported near the border — a different, and
  already dramatic, number. Use the table above instead.
- A **"2,300+ heatstroke cases in May 2024 vs. 890 the year before"** figure. No source
  turned this up. Use the verified 72-admissions-in-24-hours figure above, or find a
  direct primary source before citing a larger number.

## Why this matters for the product

The gap dashboard's entire credibility rests on the "official" side of the comparison
being real, sourced, and honestly labeled as manually curated (there is no live official
API for heat-mortality data — see [`architecture.md`](architecture.md)). Any number that
enters the dashboard's official-figures side must come from this table.
