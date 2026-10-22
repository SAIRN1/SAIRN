# HANDOFF — fourth / ted, batch b55, 2026-10-22

**READ THIS FILE ONLY.** It is the whole state.

**Summary:**
- The stub fields are labelled.
- The NVDA re-run on the fixed build is clean (0 refused). It found one real defect, the doc-scan upload zone, which is now fixed.
- target-size and emoji-in-headings are both verified real and filed.
- Landed and live. No force, no gate skip.

Wrapped at **~27% real context**.

**Transcript:**
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210.jsonl`

**Scratchpad:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fd66c7b5-98f7-4e46-ac2a-b0383cde9210\scratchpad\`
- Scripts: `nvda_dental.py`, `a11y_dental.py`, `ts55.py` (target-size measurement), `ds55.py` (doc-scan Tab trace).
- Results: `nvda_sd55.json`, `a11y_sd55_local.json`, `a11y_sd55_live.json`.
- **`nvda_sd55.log` holds speech from other windows. Do not share or upload it.**

## 1. STATE

| item | sha (origin) | state |
|---|---|---|
| 1 stub labels | `a7c848c83` | live; bytes = origin at 14:53Z |
| 2 NVDA re-run, fixed build | scratchpad | 201 steps captured, 0 refused; found the doc-scan defect, fixed in `a7c848c83` |
| 3 target-size x5 | — | **verified real**: five inputs at 173x19 px, under 24 px. Filed, not fixed. |
| 4 emoji in headings | — | **verified**: NVDA speaks each emoji by name. Filed, not fixed. |
| register / scrutiny | `c7f32c14c`, `5bb90f6db`, `09c05ab69` | landed; HEAD = origin/main |

## 2. DETAIL

### Stub labels

**Concept:** a field's label is the name its own reading code gives the value, tied with `for=`, at #666 (contrast passes).

Of the 43 `missing-dom-fix` containers:
- **17 are text fields** whose visible label was the raw element id. They are now labelled.
- **26 are output containers** (lists, KPI rows, modals, chips). They have no label to give.
- `ts-search` and `rf-source-chart` are read by no code. They are labelled as decided, and filed.

### NVDA re-run

Run on the local tree served at the live URL, with writes blocked.
- All 7 panels that had no heading in b54 now speak "<name>, heading, level 2".
- On doc-scan, Tab from the heading **left the page**: the upload zone was not focusable. NVDA then spoke nothing for the last 4 panels (emailsecurity, itadmin, admin, integrations).
- A Windows widget utterance ("AlphaSignal") appeared once, even with toasts off.

### Doc-scan defect

The b53 rule skipped any card containing a control. Here the only control is a `display:none` file input.

**Fix:** reachability is now judged by `display:none` / `[hidden]` between the control and the zone.
- It is NOT judged by `offsetParent`, which is null for everything at load.
- My first attempt used `offsetParent`. axe flagged `nested-interactive` x4 on the integrations cards before commit, and I corrected it.

**Results** (local, then confirmed live):
- color-contrast 13 → **0**
- mouse-only 6 → **4** (integrations cards; their inner "+ Connect" button is reachable, so they are skipped on purpose)
- select-name 0, label 0, panels with no heading 0
- target-size x5 unchanged

**Suite:** `tests/stonedesk_a11y_pass.js` has 25 arms; all 4 new mutants were killed.

### Emoji in headings

The NVDA log records text before symbol processing. NVDA's `locale/en/cldr.dic` maps each heading emoji (🤖 robot, 📝 memo, 🎯 bullseye, 📷 camera …) at level `none`, which is always spoken. The CLDR setting is at its default (on), since `nvda.ini` does not set it. So NVDA says "robot StoneDesk AI Assistant, heading, level 2".

This is verified from NVDA's own data and config, not by listening.

## 3. OPEN — exact next step for each

1. **Emoji in headings.**
   - Next step: wrap the leading emoji of each heading in `aria-hidden` (in `sdA11yPass`, as sairndental's sidebar icons were in b52). This needs a go-ahead; it is not done.
2. **target-size x5:** `#fq-client`, `#nest-slab-w`, `#nest-slab-h`, `#nest-cut-w`, `#nest-cut-h`.
   - Next step: give them `min-height:24px`. Waiting on a go-ahead.
3. **NVDA has not heard the doc-scan fix.** axe and the keyboard trace confirm the zone is now reached by Tab.
   - Next step: `python nvda_dental.py sd56 - stonedesk`, and Michael clicks the window once.
4. **`npm ci` (from b54) is still not run**: the permission prompt denied it.
   - Next step: Michael runs `! npm ci --ignore-scripts --no-audit --no-fund`.
5. **`ts-search` and `rf-source-chart`** are labelled, but no code reads them.
6. **Not mine:** `tests/stonedesk_exec_msgs_gate.js` is red, the same as at HEAD.
7. **Tier A obligation (b54)** is assigned to hank.

## 4. CLAIMS

`fourth`: released at wrap. No SQL.
