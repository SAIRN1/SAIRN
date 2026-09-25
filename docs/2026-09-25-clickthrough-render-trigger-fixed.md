# The click-through render trigger, fixed — and proved on real panels in the exact condition that used to lie

**2026-09-25 (Fourth).** Items 1 and 2 of the queue. The render half of the
Wave 3 audit could not run without manufacturing false findings. It can now.
Accuracy is fixed and **demonstrated**; speed in a hidden tab is not, and the
reason is measured rather than argued.

---

## 1. What was actually wrong — a constant racing a render

`tools/sairn_clickthrough_driver.js` waited a fixed **320 ms** after each nav
click, then measured the panel. That number was tuned on a foreground tab.
Chrome clamps `setTimeout` in a hidden or unfocused tab, and **the render
hooks the driver is waiting for are themselves `setTimeout(0)`** — so under
throttling the wait and the thing it waits for are clamped together and the
wait loses. Result on the driver's first run: **67 uniform, plausible,
entirely false blank-panel findings.** The response at the time was a rule —
*keep the tab foreground* — which made a detector depend on a human
remembering something.

**A fixed wait cannot be right.** Too short and a slow panel reads blank; too
long and a 67-panel sweep costs minutes for nothing. Neither number is
knowable in advance: it depends on focus state, machine, and whether the panel
fetches.

## 2. Two fixes, and the first one was wrong — measured, not reasoned

**Attempt 1 — quiescence polling.** Replace the constant with a measurement:
sample `(chars, ctrls)` until identical three reads running, ceiling 6 s. Run
against SAIRNbiz hidden:

```
settleMs = 51996        ceiling = 6000
```

**The ceiling was blown 8.7×, and the reason is the same defect one level up:**
the ceiling is only *checked* when a poll fires, and the poll is itself a
`setTimeout`. A 6 s ceiling enforced by a clamped timer is not a 6 s ceiling.
I had replaced a constant that raced a render with a ceiling that raced the
same clock.

**Attempt 2 — MutationObserver.** `MutationObserver` fires on DOM mutation
**regardless of visibility**: the panel tells us when it changed instead of us
asking on a clock we do not control. One clamped timer is still needed for
"nothing has happened for a while" — there is no unthrottled way to observe an
*absence* — but one is affordable where three-plus polls were not, and the
wall-clock ceiling is checked **on the mutation callback** as well, so a panel
that mutates for ever still terminates.

## 3. THE PROOF — 8 SAIRNbiz panels driven in a hidden tab

Signed in through the app's own `sbDoLogin()` (not by faking session state),
`visibilityState: "hidden"`, `hasFocus: false` — the exact condition that
produced 67 false blanks:

| Panel | chars / controls | settle |
|---|---|---|
| dashboard | 1451 / 2 | 848 ms |
| ai | 275 / 13 | 994 ms |
| employees | 1075 / 12 | 1001 ms |
| hiring | 504 / 5 | 989 ms |
| timesheet | 672 / 12 | 1000 ms |
| payroll | 2092 / 2 | 997 ms |
| benefits | 1511 / 9 | 5996 ms |
| performance | 584 / 7 | 59973 ms |

```
F1_nav_dead: []   F2_blank: []   F3_threw: []   F4_handler_gone: []   errors: 0
```

**Every panel rendered real content. The old driver would have called all
eight blank.** That is the false-finding class closed, shown rather than
claimed.

## 4. What is NOT fixed, and it is a platform property not a bug

The `settleMs` column is the residual, and it shows Chrome's **progressive**
hidden-tab throttling with unusual clarity: 848 ms → ~1000 ms → 5996 →
**59973**. After sustained hiding the clamp reaches roughly one timer per
minute. Since the quiet window *must* be a timer, a deeply-hidden tab costs
up to ~60 s per control.

**So: correctness no longer depends on the tab being foreground; throughput
still does.** 20 SAIRNbiz controls would take ~10 minutes hidden and seconds
foregrounded; StoneDesk's 67 would take roughly an hour. The run above was
stopped at 8 of 20 for that reason and is reported as **partial**, not as a
sweep.

**Why the sweep was not completed, stated plainly:** the automation tab
available to this session cannot be brought to the foreground from here. The
honest outcome is 8 real measurements and a driver that can no longer lie,
rather than 20 numbers produced by waiting an hour or 67 produced by guessing.

## 5. What a future run should do

- Run it foregrounded if a human is present — it is seconds, not minutes.
- Read `timerClampMs` in the report. Near 50 means foreground; hundreds or
  more means throttled and slow, **not** wrong.
- Read `COULD_NOT_SETTLE` before `F2_blank`. A panel that hit the ceiling is
  *"still changing when I gave up"*, which is a different fact from
  *"renders nothing"* — folding those two together is precisely how this
  detector lied the first time.
