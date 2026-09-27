# The render half re-run under a genuinely hidden tab — hover's fix holds, and the instrument could not prove it

**Run 2026-09-26 (Fourth) against the deployed StoneDesk at `sairn.vercel.app`,
signed in, in a hidden tab. Queue item 3.**

The 2026-09-26 render-half completion
(`docs/2026-09-26-clickthrough-render-half-completed.md`) reported StoneDesk
74/74 and SAIRNbiz 20/20 with zero findings, and said so honestly:

> **The run was NOT throttled (clampMs 55 and 58 against a requested 50), so it
> does not re-test the hidden-tab path `0fe57998` fixed.**

This is that re-test. **The fix holds.** And getting to that answer required
fixing the instrument first, because as written it cannot substantiate a
hidden-tab claim at all.

---

## 1. The result

Two independent full sweeps of the 67 `sbNav()` controls, both started with
`visibility=hidden` and `hasFocus=false` confirmed before injection.

| | Run 1 | Run 2 (per-row instrumentation) |
|---|---|---|
| Driven | **67 / 67** | **67 / 67** |
| F1 nav dead | 0 | 0 |
| **F2 blank** | **0** | **0** |
| F3 threw / page errors | 0 | 0 |
| F4 handler gone | 0 | 0 |
| COULD_NOT_SETTLE | 0 | 0 |
| Worst settle | **59,986 ms** | 2,003 ms |
| Controls settling > 8 s | 3 (59,986 / 59,871 / 43,424) | 0 |
| Rows recorded while HIDDEN | not measurable — see §3 | **25 of 67** |

**The three controls in run 1 that took 43–60 seconds to settle are the
verification.** The driver's pre-`0fe57998` behaviour was a fixed 320 ms wait. A
control that needs 43,424 ms to stop mutating would have been sampled at 320 ms,
found near-empty, and recorded as **blank** — that is the mechanism behind the
original 67 false blank-panel findings. Those three rendered, were measured
correctly, and appear in no finding class. **A hidden tab made the sweep slower,
not wrong, which is exactly what `0fe57998` claimed and had only ever shown on
8 of 20 SAIRNbiz panels.**

Run 2 adds what run 1 could not: **25 of its 67 rows were recorded with
`document.visibilityState === 'hidden'` at the moment of measurement**, and all
25 are in the clean set.

**No credential was typed.** The licence gate cleared from `localStorage` and the
employee session restored itself; the app came up to 72 visible nav controls on
its own. `sairn.vercel.app` is a live production host, so entering an employee PIN
there was not an option and was not done.

---

## 2. SAIRNbiz is NOT covered by this run

Only StoneDesk's 67 `sbNav` controls were driven. The 7 `showPanel` controls and
all 20 SAIRNbiz panels are **UNVERIFIED under a hidden tab**, not clean. Stated
here because the document this one supersedes was careful about the same
distinction and a reader comparing the two tables would otherwise assume parity.

---

## 3. The instrument could not prove its own headline claim, and that is the
## finding worth more than the sweep

`SCT.report()` recorded `document.visibilityState` **once, at report time.**

**MEASURED: a run that starts hidden does not stay hidden.** Run 2 began with
`visibility=hidden, focus=false` — the driver's own start-up line says so — and
finished with 42 of its 67 rows recorded `visible` and focused. The flip happened
mid-sweep, in one uninterrupted run, **with nothing executing in the tab**: the
only activity between the start and the completion check was a blocking wait
outside the browser. Something re-foregrounded the tab and the driver had no way
to say so.

So the single end-of-run flag can report `visible` about a run that was mostly
hidden — which is what happened to run 1 — or `hidden` about one that was mostly
not. **Neither the earlier render-half run nor my own first run could be
substantiated as a hidden-tab test, and the reason was the instrument rather than
the operator.**

**This reframes the run this document re-tests.** `clampMs 55 and 58` was read as
"the tab was not backgrounded." On this evidence the likelier reading is that it
*was* backgrounded and re-foregrounded itself before or during the sweep. Same
number, different cause, and the difference matters: one is a procedure somebody
forgot, the other is a property of the environment that no amount of care fixes.

### 3.1 `clampMs` is one sample against a threshold it can fail to cross

`SCT.clampMs` is measured ONCE at start-up from a single 50 ms timer, and the
comment beside it read `>400 means throttled`.

**Run 1 reported `clampMs: 271` — and its worst control then took 59,986 ms to
settle.** 271 ms for a 50 ms request is a 5.4x clamp and unmistakably throttled,
yet it is *below* 400 and would have been read as a foreground run. The clamp is
**progressive** — measured here at 456 ms, then 1,000 ms, then reaching ~60 s per
control — so a start-up sample cannot characterise it in either direction.

### 3.2 What changed in `tools/sairn_clickthrough_driver.js`

Three additions, no behaviour change to the sweep:

- **`tabVis` and `tabFocus` per row**, captured in `record()`. "The hidden path
  was exercised" becomes a count of rows instead of an assertion about the run.
- **`rowsRecordedHidden` / `rowsRecordedVisible`** in `report()`, so a run that
  drifts foreground shows as a split rather than as whichever state it ended in.
- **`settleMsMax`** in `report()`, and the `>400` threshold comment corrected:
  compare `clampMs` to the requested 50 and read `settleMsMax` alongside it.

**Injecting into an ALREADY-HIDDEN tab is now part of the procedure, not an
optional nicety.** `clampMs` is sampled at injection, so injecting while
foreground and backgrounding afterwards guarantees a clamp figure that describes
a state the run was never in. That ordering alone probably explains the 55/58.

---

## 4. What this run does NOT establish

- **Nothing about SAIRNbiz or the 7 `showPanel` controls** (§2).
- **Nothing about whether any feature WORKS.** The driver clicks nav controls
  only and never a control inside a panel, deliberately, because those write real
  rows to a real licence. A clean run means every panel opens, renders and wires
  its handlers.
- **Not a complete hidden-tab sweep.** 25 of 67 rows in run 2 are *proven*
  hidden; the remaining 42 were recorded after the tab re-foregrounded. A fully
  hidden 67-row sweep was not achieved and may not be achievable through this
  transport, because the environment keeps returning focus to the tab.
- **Not a reproduction of the original 67 false blanks.** That would need the
  pre-`0fe57998` driver run side by side under the same clamp. The 43–60 s
  settles are strong circumstantial evidence — a 320 ms wait cannot see a panel
  that takes 43 s to settle — but the two drivers were not run head to head, and
  that ablation is the one piece of evidence this document does not have.

---

## 5. Re-running it

1. Open the app and let it come up. Do NOT type a PIN on a production host.
2. **Hide the tab first** — activating another tab in the same window is enough;
   confirm `document.visibilityState === 'hidden'` and that a 50 ms timer now
   takes several hundred ms or more.
3. **Then** inject `tools/sairn_clickthrough_driver.js`.
4. Wait on real wall-clock time outside the browser. A hidden sweep of 67
   controls took roughly 5–20 minutes here, with individual controls up to ~60 s.
5. Read `SCT.report()` and check **`rowsRecordedHidden`** before believing the
   run tested anything about hidden tabs. `visibility` alone will not tell you.
