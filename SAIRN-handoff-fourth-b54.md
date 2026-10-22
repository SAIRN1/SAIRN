# HANDOFF — fourth / ted, batch b54, 2026-10-22

**READ THIS FILE ONLY.** It is the whole state. **A clean, hands-off NVDA pass
on StoneDesk: 67/67 panels heard, none refused. The StoneDesk backlog is fixed,
landed and live. `npm ci` was NOT run: the permission prompt denied it.** No
force, no gate skip. Wrapped at **~22% real context**.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Scratchpad:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- `nvda_dental.py <label> - stonedesk` runs NVDA. New in b54:
  - it switches Windows toasts off for the run (`HKCU ...\Notifications\Settings` `NOC_GLOBAL_SETTING_TOASTS_ENABLED`) and restores the original value in `finally`;
  - it blocks every non-read `/api/` POST.
- `a11y_dental.py` with `A11Y_APP=stonedesk A11Y_FULL=1` keeps every select-name, label and contrast node.
- Results: `nvda_sd54.json`, `a11y_sd54_full.json` (before), `a11y_sd54_final.json` (local after), `a11y_sd54_live.json` (live after).
- **`nvda_sd54.log` holds speech from other windows. Do not share or upload it.**

## 1. STATE

| item | sha (origin) | state |
|---|---|---|
| 1 NVDA pass, StoneDesk | scratchpad | **clean**: 67/67 heard, 201 steps captured, 0 refused |
| 2 names, headings, contrast | `847e89943` | live; bytes = origin at 14:11Z; the live re-pass matches the local one |
| register / Tier A / scrutiny | `b7dd2541d`, `4d0b8c7c4`, `cc41f73a9` | landed; HEAD = origin/main = `cc41f73a9` |
| 3 `npm ci --ignore-scripts --no-audit --no-fund` | — | **NOT RUN**: permission denied, twice |

## 2. NVDA — WHAT IT ACTUALLY SAID (the live build BEFORE the item 2 fix)

- Sign-in worked. Every sidebar item said "current page" on Enter, so `aria-current` works.
- On Enter, NVDA spoke "<panel title>, heading, level 2" on **59 of 67** panels. Of the other 8:
  - **7 had no heading** (quote, draw, field-quote, check-register, market, business, doc-scan). Focus stayed on the sidebar.
  - **1 (sms) spoke a Command Prompt title from another window**, although focus was on the H2. That is a cross-window utterance, not a page defect.
- Emoji inside headings are read aloud, e.g. "🤖 StoneDesk AI Assistant". **Filed.**
- The run blocked 8 writes.

## 3. STONEDESK FIXES (`847e89943`)

**Concepts:**
- **A control with no visible label still says what it chooses.**
  - `SD_A11Y_NAMES` holds a written name per control id.
  - A name is applied only where the control has none, so a real `<label>` wins.
  - Dynamic rows name themselves: edge rows, vendor quantities, seam runs, and the backtest CSV picker.
- **Every panel has a heading.**
  - A page's `.ptitle` becomes a level-2 heading.
  - A panel with no heading gets a clipped `h2` carrying its sidebar name.
- **Each failing text colour moves to the next darker shade of its own hue that reaches 4.5:1** on the background it sits on.
  - `--brand2` goes from `#0F8742` to `#0B7A3B`.
  - The AI style chips were dark-theme colours on a white page.

| live, 67 targets | before | after |
|---|---|---|
| select-name | 79 | **0** |
| label | 44 | **0** |
| color-contrast | 73 | **13** (all stub labels, see §4) |
| panels with no heading | 7 | **0** |
| focus on a heading after nav | 60/67 | **67/67** |

`tests/stonedesk_a11y_pass.js` now has 22 arms; all 8 new mutants were killed.
Of 25 `tests/stonedesk*.js` suites, only `stonedesk_exec_msgs_gate` is red, the same as at HEAD.

## 4. OPEN — exact next step for each

1. **`npm ci`: not run, denied by the permission prompt.**
   - Next step: Michael runs `! npm ci --ignore-scripts --no-audit --no-fund` in this clone, or allows the command.
   - Until then, an SDK-touching push from fourth may be denied by CHECK 5f.
   - This batch touched no SDK, and the push passed.
2. **43 "missing-dom-fix" stub fields** (from `36315fb99`) show the raw element id as their visible label, e.g. "rm-filter-status". All 13 remaining contrast nodes are these labels.
   - They are deliberately **not** recoloured: each field needs a product decision (real label, or remove the stub).
   - Next step: Michael decides; then route the work to the app owner.
3. **NVDA has not yet heard the fixed build.** axe and the keyboard pass verify it.
   - Next step: run `python nvda_dental.py sd55 - stonedesk` and have Michael click the window once.
4. **target-size x5** (field-quote, nesting) and **emoji read inside headings**: filed.
5. **Tier A obligation** (customers, slabs, invoices, quotes) is assigned to **hank**: confirm `sdA11yPass` touches only attributes and styles.
6. **Not mine:** `tests/stonedesk_exec_msgs_gate.js` is red at HEAD.

## 5. CLAIMS

`fourth`: released at wrap. No SQL.
