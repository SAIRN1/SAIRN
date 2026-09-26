# The click-through RENDER half, run to completion for the first time — 2026-09-26

**Driven 2026-09-26 (Fourth) against the LIVE deployed apps**, `tools/sairn_clickthrough_driver.js`
at HEAD. **Zero findings across 94 driven controls and 87 distinct panel targets.**

This is the half that had never completed. The record of why, in order:

| Date | What happened to the render half |
|---|---|
| 2026-09-23 | Run hidden. **67 uniform false blank-panel findings** — every panel's render hook sits in a `setTimeout` and Chrome clamps those in a background tab |
| 2026-09-25 | **Deliberately NOT run.** The clamp was re-measured (a 50 ms timer taking 517 ms) and running it would have reproduced the 09-23 incident and reported it as fact. Could-not-run was not folded into a pass |
| 2026-09-25 (later) | `0fe57998` replaced the fixed 320 ms wait with a **MutationObserver**, so a clamped tab makes the sweep slower rather than wrong. A partial run reached **8 of 20** SAIRNbiz panels before stopping |
| **2026-09-26** | **Complete. StoneDesk 74/74, SAIRNbiz 20/20, zero findings.** |

---

## 1. The result

| App | Nav fn | Controls driven | Distinct targets | F1 dead nav | F2 blank | F3 threw | F4 handler gone | Errors | COULD_NOT_SETTLE |
|---|---|---|---|---|---|---|---|---|---|
| StoneDesk | `sbNav` | 67 | 67 | 0 | 0 | 0 | 0 | 0 | 0 |
| StoneDesk | `showPanel` | 7 | 7 (all ⊂ the 67) | 0 | 0 | 0 | 0 | 0 | 0 |
| SAIRNbiz | `nav` | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total** | | **94** | **87** | **0** | **0** | **0** | **0** | **0** | **0** |

`settle()` — the second measurement that clicks nothing and reads every target
after the run — agrees: **zero panels have zero controls when settled**, on either
app. The thinnest StoneDesk panel is `doc-scan` at 263 characters and 5 controls;
the thinnest SAIRNbiz panel is `ai` at 275 characters and 13 controls. Nothing is
near the 40-character blank threshold.

Three panels were measured **mid-fetch**, which the driver reports separately and
which are explicitly **not findings**: StoneDesk `subcontractor` (20 controls
during the run → 27 settled) and `publiccatalog` (12 → 30), SAIRNbiz `settings`
(4 → 8). That is the async-render race the 09-25 fix exists to handle, behaving
exactly as designed — the control count grew after the click and the panel was
never reported blank.

---

## 2. THIS RUN WAS NOT THROTTLED, SO IT DOES NOT RE-TEST THE FIX THAT UNBLOCKED IT

**The most important limit, stated before the good news is read as more than it
is.** `timerClampMs` measures a requested 50 ms timer on every run:

* StoneDesk: **55 ms**
* SAIRNbiz: **58 ms**

Both are essentially unclamped — a foreground-quality run. Chrome had not
throttled this tab, so **this run does not exercise the hidden-tab path that
`0fe57998` was written for.** The MutationObserver fix is still verified only by
the partial 8-of-20 run of 2026-09-25, plus the fact that it is now the
mechanism and no fixed wait remains to race.

Both apps reported `visibility: "visible"` and `hasFocus: false`. The prior
session recorded the clamp "pushing settle time toward ~60s per control"; here
the whole StoneDesk sweep finished inside 25 seconds and SAIRNbiz inside 20. **Do
not read that as the fix being faster — read it as the clamp not being engaged.**
The two facts are separable and conflating them would credit the fix with a
result the environment produced.

---

## 3. HOW THE APPS WERE REACHED, because it matters that no credential was typed

Both apps came up **already past their gate** in a fresh tab. The licence keys
live in `localStorage`, which a new tab on the same origin inherits:
`stonedesk_license_key` and `sb_lic` were both present from Michael's own
session. StoneDesk has no `#gate` element at all; SAIRNbiz's `#gate` computed to
`display: none`.

`sessionStorage` is per-tab, so `sd_session_token` was **ABSENT** — and it made no
difference to this audit. Every panel rendered, because reads on these resources
carry the licence. **Nothing here re-verifies the employee-session gate**; that is
a different question and this run says nothing about it.

**SAIRNvet was SKIPPED and that is recorded rather than folded in.** It has no
working credential at all — `docs/2026-09-03-demo-credentials.md` records the
working set as StoneDesk `SD-AUDIT-2026` and SAIRNbiz `SB-TEST-2026`, and
SAIRNvet as **NONE**, recoverable only by a direct database write. One third of
the intended population is therefore **UNVERIFIED, not clean.**

---

## 4. THE POPULATION WAS ENUMERATED BEFORE IT WAS TRUSTED, AND ONE NEAR-FINDING DIED THAT WAY

The 2026-09-25 document records this method almost faking itself: its first sweep
returned **0 controls and 0 findings** — clean over no data — because SAIRNbiz
uses `.sb` where StoneDesk uses `.sidebar-btn`. So before either run, every
`[onclick]` attribute on the page was read and its callees tallied, rather than a
class or a function name being assumed:

* **StoneDesk** — `sbNav` 67, then `vendorCompare` 25, `cartAdd` 25, `adj` 14,
  `showPanel` 7. Two nav systems, which is the driver's own lesson 1.
* **SAIRNbiz** — `nav` 20, then `csv` 16, `askAI` 8, `genReport` 6. One nav
  system, and 20 controls against exactly 20 `panel-*` elements.

**AND THE TWO-NAV-SYSTEM CONCERN TURNED OUT NOT TO BE ONE.** A single-pass run
auto-detects one nav function, so on StoneDesk it drives `sbNav` and ignores
`showPanel` — which looks like covering 67 of 74 controls and reporting clean
over the other 9%. Checked against source rather than assumed: **all seven
`showPanel` args are also reachable via `sbNav`** (`aiquote`, `careguide`,
`client`, `quote`, `seamai`, `stonehub`, `veinmatch`), so the union of distinct
targets is 67 and not 74. The second pass drove those seven a second time through
the other entry point and found the same clean result. `showPanel` is an
additional route into panels already covered, not a hidden 10% — recorded as
checked-and-clear so the next reader does not re-raise it.

---

## 5. What a clean run here does NOT mean

* **It clicks NAV ONLY.** It fills no form, submits nothing and clicks no control
  inside a panel — deliberately, because those write real rows to a real licence.
  "Every panel opens, renders and wires its handlers" is the claim. **No feature
  is verified to work.**
* **F4 is a RUNTIME check of handler existence**, not of handler correctness. A
  control whose function exists and does the wrong thing passes.
* **One third of the population is missing** (SAIRNvet) and is unverified rather
  than clean.
* **The unthrottled path is what was measured** (§2).
* **No source was read for this result and no file was changed.** The verdicts are
  properties of the deployed pages as they behaved.

---

## 6. Full target census

**SAIRNbiz — 20/20, every panel with real content and controls:**

`dashboard` 1507/2 · `ai` 278/13 · `employees` 1187/12 · `hiring` 546/5 ·
`timesheet` 779/12 · `payroll` 2198/2 · `benefits` 1602/9 · `performance` 636/7 ·
`training` 1598/9 · `pl` 702/2 · `invoices` 1122/10 · `expenses` 997/2 ·
`ap` 1245/14 · `ar` 567/2 · `budget` 1030/2 · `tax` 3043/2 · `company` 502/23 ·
`vendors` 741/2 · `reports` 306/9 · `settings` 811/4   *(chars/controls)*

**StoneDesk — 67/67 via `sbNav`, plus the same 7 again via `showPanel`:**
`aiquote` 1656/19 · `seamai` 854/18 · `veinmatch` 876/10 · `careguide` 1143/10 ·
`stonehub` 8092/44 · `client` 774/7 · `quote` 2681/50. The other 60 reported no
finding on any of the four classes and no zero-control target when settled;
thinnest four were `doc-scan` 263/5, `template` 504/6, `nesting` 706/15,
`client` 769/7.
