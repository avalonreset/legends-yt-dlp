# Perfect Video Formula and Pre-Recording Idea Radar

Before recording or scripting a video, use the **Perfect Video Score** formula and the **Goldilocks Timing Rule** to evaluate whether a topic deserves production time.

> *"I have been making the video first and doing SEO after. That is backwards."*

---

## 1. The Perfect Video Score Equation

Each numerator dimension is scored from `1` to `10` (normalized to `0.1` to `1.0` or multiplied on a 10-point scale), and divided by the sum of friction factors (`1` to `10` each):

$$
\text{Perfect Video Score} = \frac{\text{Trend Timing} \times \text{Search Surface} \times \text{Audience Pain} \times \text{Channel DNA Fit} \times \text{Proof Advantage} \times \text{Packaging Strength}}{\text{Production Drag} + \text{Platform Risk} + \text{Hype Saturation}}
$$

### Numerator Multipliers (Why the Video Wins)
1. **Trend Timing (`1-10`):** Is the topic rising with fresh catalyst momentum right now?
2. **Search Surface (`1-10`):** Is there a clear, high-intent searchable phrase (or an underserved exact tool/model query paired with a broad category term)?
3. **Audience Pain (`1-10`):** Does it solve a real, frustrating operator problem rather than pure novelty?
4. **Channel DNA Fit (`1-10`):** Does it match the channel's core authority (e.g., building and demonstrating real systems)?
5. **Proof Advantage (`1-10`):** Can you show a working build, live terminal/screen proof, or contrarian benchmark that generic commentary channels cannot fake?
6. **Packaging Strength (`1-10`):** Can the promise be stated in a clean title plus a 2-to-5-word high-contrast thumbnail hook?

### Denominator Drag Factors (Why the Video Fails or Stalls)
1. **Production Drag (`1-10`):** How heavy is the setup, rendering, or multi-day engineering required before recording?
2. **Platform Risk (`1-10`):** Does the topic rely on brittle scraping, ToS grey zones, or policy strikes?
3. **Hype Saturation (`1-10`):** Have 50 larger channels already covered the exact same surface angle this week?

---

## 2. The Goldilocks Timing Rule

A technical or creator-workflow topic is strongest when it is neither too early nor too stale:

| Stage | Days Since Release / Catalyst | Signal | Recommended Action |
|---|---|---|---|
| **Too Early** | `Day 0 - 3` | Release is fresh, but documentation is sparse, search surface has not formed, and real user pain is unknown | Watchlist only, unless you have an immediate working demo on Day 1. |
| **Goldilocks (Prime)** | `Day 4 - 30` | Fresh catalyst, enough public evidence, weak practical coverage, and clear operator pain | **Produce immediately.** |
| **Workflow Evergreen** | `Day 31 - 180` | Search demand exists, but hands-on workflow tutorials and honest benchmarks are still weak | **Produce with a deep system/workflow angle.** |
| **Saturated / Mature** | `180+ Days` | Top videos already answer basic questions | Only produce if you have a major new update, contrarian proof, or a superior system. |

---

## 3. The 9-Point Fit Filter

A candidate topic must answer **YES** to at least **5 of these 9 questions** before greenlighting production:

1. Can you show a real build, working demo, or live workflow?
2. Does it compound your broader production or engineering ecosystem?
3. Is there a concrete pain point rather than passing novelty?
4. Can you be skeptical, honest, and useful instead of promotional?
5. Can the recording yield both a flagship long-form video and multiple Shorts angles?
6. Does it visibly improve a core workflow (captions, thumbnails, recording, automation, SEO, deployment)?
7. Is the title immediately understandable to someone searching for a solution?
8. Is there a distinct visual proof frame for the thumbnail?
9. Can it be demonstrated safely without unsafe account access or policy risk?

---

## 4. CLI Usage

```bash
legends-youtube score-idea \
  --title "I Built an Agentic System to Score YouTube Ideas Before Recording" \
  --days-since-catalyst 14 \
  --trend-timing 8 \
  --search-surface 8 \
  --audience-pain 9 \
  --channel-dna-fit 10 \
  --proof-advantage 9 \
  --packaging-strength 8 \
  --production-drag 3 \
  --platform-risk 1 \
  --hype-saturation 2 \
  --fit-checks 8
```
