# HANDOFF — fourth / ted, batch b53, 2026-10-21

**READ THIS FILE ONLY.** It is the whole state. **StoneDesk a11y fix landed
and live; NVDA summary bug fixed (scratchpad tool). No force, no gate skip.**
Wrapped at a safe point at **~70% real context**.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Scratchpad:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- `nvda_dental.py`: the NVDA run. `--selftest` checks the summary against fixtures.
- `a11y_dental.py`: the axe and keyboard pass. Set `A11Y_APP=stonedesk`.
- `a11y_stonedesk_before.json`, `a11y_stonedesk_after.json`, `a11y_stonedesk_live.json`, `nvda_after.json`, `nvda_after.log`: results.
- The log contains speech from other windows. Do not share it.

## 1. STATE

| item | sha (origin) | state |
|---|---|---|
| 2 NVDA summary bug | scratchpad `nvda_dental.py` | fixed; fixtures PASS |
| 1 StoneDesk a11y | `54a8c8567` | live (bytes = origin, 20:50Z); 12 arms, 9/9 mutants |
| register / override / docs | through `60e2b6ca1` | landed; fourth holds 19 overrides |

## 2. NVDA — WHAT THE REAL LOG SHOWS

This is Michael's re-run, at 16:14 local.

**The bug was mine.** The summary printed every panel that had *any* refused
step as "could-not-run", so it reported all 23 panels. That is false:
- sign-in succeeded;
- on Dashboard, NVDA said "Main navigation, complementary landmark, **Dashboard, button, current page**". There is **no emoji any more**, which confirms the b52 fix.
- On Enter it said "main landmark, **Dashboard, heading, level 2**". J1 is confirmed again.

**Then Windows Quick Settings took the foreground.** The log shows a volume
change at that moment. Every later step (90 of them) was correctly refused.

**Fixed summary.** Each step is now *captured*, *refused* or *not attempted*.
Each panel is now *heard*, *partial*, *refused* or *not attempted*, the first
refusal is named, and the run stops after 30 seconds without the foreground.
Fixtures lock this. Applied to the real run, the summary reads:
- **2 steps captured, 90 refused**;
- Dashboard partial, the other 22 panels refused.

## 3. STONEDESK (67 navigation targets; live demo login; writes blocked)

**Concepts:**
- a visible label names the control that follows it;
- an element wired to one of 10 **allowlisted** button handlers becomes a keyboard button:
  - modal backdrops are never made into tab stops;
  - cards that already contain a control are skipped, to avoid nested-interactive;
  - new targets get a 24px minimum;
- sidebar icons are hidden from the reader;
- `sbNav()` sets `aria-current` and moves focus to the panel's first heading.

`sdA11yPass()` runs at load and again after every navigation.

| | before | after |
|---|---|---|
| mouse-only controls | 53 | 6 (cards with reachable inner controls; skipped on purpose) |
| axe `label` | 86 | 44 |
| axe `select-name` | 101 | 79 |
| aria-current | none | set |
| focus after navigation | sidebar button | a heading, on 60/67 |

**Filed, not fixed (these need wording or design decisions):**
- `color-contrast`, 73 nodes; these are design tokens;
- 79 selects with no visible label to tie. Each needs a written name;
- 44 remaining `label` nodes;
- 7 panels with no heading at all: quote, draw, field-quote, check-register, market, business, doc-scan;
- 5 `target-size` nodes, mostly the existing nesting inputs.

## 4. OPEN

1. **A clean, hands-off NVDA pass** (held on Michael's timing). Quick
   Settings or a volume key will steal the foreground mid-run.
2. **StoneDesk's filed items:** see §3.
3. **Not mine:** `tests/stonedesk_exec_msgs_gate.js` is red, and fails the same way at HEAD.

## 5. CLAIMS

`fourth`: released at wrap. No SQL.
