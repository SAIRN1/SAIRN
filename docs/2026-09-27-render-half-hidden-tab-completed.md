# The render half under a hidden tab, both halves — and the tab flips seven times

**Run 2026-09-27 (Fourth) against the deployed apps at `sairn.vercel.app`, signed
in, in a hidden tab. Queue items 3 and 7.**

`docs/2026-09-26-render-half-hidden-tab-rerun.md` closed with two things
outstanding, and it named them rather than implying coverage:

> **SAIRNbiz and the 7 `showPanel` controls are UNVERIFIED under a hidden tab, not
> clean.** … A fully hidden 67-row sweep was NOT achieved; 25 of 67 rows are
> *proven* hidden and the other 42 were recorded after the tab re-foregrounded.

Both are now measured, and the instrument that could not substantiate the claim
was fixed first.

---

## 1. The result

| | SAIRNbiz (`nav`) | StoneDesk (`showPanel`) |
|---|---|---|
| Driven | **20 / 20** | **7 / 7** |
| F1 nav dead | 0 | 0 |
| **F2 blank** | **0** | **0** |
| F3 threw / page errors | 0 | 0 |
| F4 handler gone | 0 | 0 |
| COULD_NOT_SETTLE | 0 | 0 |
| clampMs at injection | 424 | **1001** |
| Worst settle | 5,819 ms | **59,989 ms** |
| Controls settling > 8 s | 0 | **3** (59,989 / 41,994 / 32,552) |
| **Controls FULLY hidden** | **3** | **5** |
| Controls spanning a transition | 1 | 1 |

**The three StoneDesk controls that took 32–60 seconds to settle are the
verification.** The driver's pre-`0fe57998` behaviour was a fixed 320 ms wait, so a
panel needing 59,989 ms to stop mutating would have been sampled at 320 ms, found
near-empty, and recorded **blank** — the mechanism behind the original 67 false
blank-panel findings. All three rendered and appear in no finding class.

**No credential was typed.** Both apps restored their employee session from
`localStorage` asynchronously — SAIRNbiz took roughly 12 seconds and showed its PIN
screen first, which is worth knowing because a run injected too early sees 0
controls and reports a clean sweep of nothing. `sairn.vercel.app` is a live
production host, so entering a PIN was not an option and was not done.

---

## 2. The instrument was still sampling, and the sample was wrong

Yesterday's fix added `tabVis` **per row**. That is still a SAMPLE — one read at
the instant each row is written — and it answers "was the tab hidden when this row
was recorded", not "was it hidden for this control".

**The gap between those is the entire settle wait, which is where the 60-second
clamps live.** A control can start hidden, be foregrounded three seconds in, and be
recorded `visible` with no trace that 57 of its 60 seconds were clamped — or the
reverse, which is worse, because the row then *claims* hidden about a control that
mostly ran foreground.

### 2.1 Measured on the first live run, with a number

The SAIRNbiz run recorded:

```
rowsRecordedHidden  3   rowsRecordedVisible 17      <- the SAMPLE
controlsFullyHidden 3   controlsFullyVisible 16
controlsSpannedTransition 1                          <- the SPAN
```

**The sample says 17 visible. The span says 16 fully visible plus one that
straddled a transition.** One control was partly hidden and the sample filed it as
wholly visible. That is the defect, caught on the first run that could see it.

### 2.2 And the tab flips far more than anyone assumed

```
SAIRNbiz   : hidden@+0s visible@+11s hidden@+22s visible@+27s
             hidden@+100s visible@+107s hidden@+133s visible@+136s   -- 7 transitions / 136s
StoneDesk  : hidden@+0s visible@+260s hidden@+279s visible@+310s
             hidden@+312s visible@+365s hidden@+367s                 -- 6 transitions / 367s
```

Nothing was executing in the tab between the injection and the completion check —
the only activity was a blocking wait outside the browser. **Yesterday's "25 of 67
hidden, 42 visible" was read as one flip. It was not; it was many.** A sample can
report that a split happened. It cannot say when, how many times, or whether any
single control straddled one, and those are the facts that decide whether a run
tested anything.

### 2.3 What changed in `tools/sairn_clickthrough_driver.js`

- **`SCT.visLog`** — a `visibilitychange` listener appends `{at, state, focus}`.
  An **event**, so it costs nothing and cannot be missed the way a poll can, and it
  is not itself throttled, unlike every timer in the file.
- **`SCT.visBetween(t0, t1)`** — every state the tab held between two stamps.
- **`row.tabVisSpan` / `row.tabVisSpanned`** — stamped from **before the click** to
  after the settle, so the span covers the window whose visibility actually
  matters. `['hidden']` means the control ran wholly clamped; two entries mean it
  straddled a transition, which is a **third state** a sample reports as one of the
  other two.
- **`controlsFullyHidden` / `controlsFullyVisible` / `controlsSpannedTransition`,
  `visibilityTransitions`, `visibilityLog`** in `report()`, derived from the log
  rather than re-sampled, so they cannot disagree with it.

The listener writes to `window.SCT` rather than a captured reference, because there
is no teardown hook: a second run replaces `SCT` and the old listener would
otherwise keep appending to a dead object.

`visBetween` was unit-checked against a synthetic log across five cases before it
ran live — wholly inside each state, both straddle directions, and the whole run.

---

## 3. What this does NOT establish

- **Not a fully hidden sweep of StoneDesk's 67 `sbNav` controls.** Yesterday's run
  covered those (67/67, zero findings) with 25 proven hidden; this run covers the
  7 `showPanel` controls and SAIRNbiz's 20. Nobody has driven all 94 in one wholly
  hidden pass, and on this evidence nobody will — **the environment returns focus
  to the tab every few minutes on its own.**
- **Not a reproduction of the original 67 false blanks.** That needs the
  pre-`0fe57998` driver run head to head under the same clamp. The 32–60 second
  settles are strong circumstantial evidence — a 320 ms wait cannot see a panel
  that takes 42 seconds — but the two drivers were not run side by side, and that
  ablation remains the one piece of evidence this line of work does not have.
- **Nothing about whether any feature WORKS.** The driver clicks nav controls only,
  never a control inside a panel, because those write real rows to a real licence.
- **Nothing about SAIRNvet**, which is still recorded UNVERIFIED rather than clean.

---

## 4. Re-running it

1. Open the app and **wait for the session to restore** — SAIRNbiz shows its PIN
   screen for roughly 12 seconds first. Injecting before the controls exist gives a
   clean sweep of nothing. Do NOT type a PIN on a production host.
2. **Hide the tab, then check it.** Activating another tab in the same window is
   enough; confirm `document.visibilityState === 'hidden'` and that a 50 ms timer
   takes several hundred ms or more.
3. **Then** inject the driver. `clampMs` is sampled at injection, so injecting
   foreground and backgrounding afterwards yields a clamp figure describing a state
   the run was never in.
4. Wait on real wall-clock time **outside** the browser.
5. Read `SCT.report()` and check **`controlsFullyHidden`** — not `visibility`, and
   not `rowsRecordedHidden`. The first is the state at report time, the second is a
   sample, and only the third is a count of controls that actually ran clamped.
