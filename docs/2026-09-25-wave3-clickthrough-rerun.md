# Wave 3 click-through re-run, 2026-09-25 — the nav-resolution half ran and is clean; the render half COULD NOT RUN, measured

**Run 2026-09-25 (Fourth) against the deployed apps at `sairn.vercel.app`.**
Supersedes nothing: `docs/2026-09-23-wave3-click-through-reverification.md`
stands as the last full run. This is a re-run because all three apps' code has
moved since then, and it reports **one half clean and one half unrun** rather
than a number.

---

## 0. Why a re-run at all — the 2026-09-23 result was stale, not wrong

The prior run closed 149/149 on 2026-09-23. StoneDesk and SAIRNvet have both
shipped since. Deployment was verified before testing rather than assumed —
markers unique to this week's commits were fetched from the live URLs:

| App | Marker probed | Live |
|---|---|---|
| StoneDesk | `.btn.bsm{` (the 2026-09-24 CSS fix) | PRESENT |
| StoneDesk | `sdCommissionForPure` (the item-92 pure core) | PRESENT |
| StoneDesk | the network-intelligence fold | PRESENT |
| SAIRNvet | `identify a role, not a named person` (the notice fix) | PRESENT |

So the deployed code is current and the prior clean result no longer describes
it.

---

## 1. THE RENDER HALF COULD NOT RUN, AND THE CONDITION WAS MEASURED

`tools/sairn_clickthrough_driver.js`'s own header states the rule in plain
words: the tab must stay FOREGROUND, because Chrome throttles `setTimeout` in
a hidden tab and StoneDesk's nav puts every panel's render hook inside one.
Its first run was done hidden and produced **67 uniform, plausible, entirely
false blank-panel findings**.

The automation tab available to this session is hidden and unfocused, and the
throttling was **measured rather than assumed**:

```
document.visibilityState : "hidden"
document.hasFocus()      : false
setTimeout(…, 0)  actual : 0 ms
setTimeout(…, 50) actual : 517 ms      <- clamped, ~10x
```

A 50 ms timer taking 517 ms is the exact condition the driver records
`visibilityState` in order to detect. **Running the driver here would have
reproduced the 2026-09-23 false-findings incident and reported it as fact, so
it was not run.** "Could not run" is a third state and is not folded into a
pass.

---

## 2. THE HALF THAT IS IMMUNE TO THROTTLING DID RUN, AND IS CLEAN

Nav-target resolution reads the DOM directly and never waits on a
timer-scheduled render, so a clamped tab cannot fake it. Driven live in all
three apps: for every nav control, take the nav ARGUMENT (not the button id —
the 2026-09-23 detector-defect #1), resolve it against `<arg>`,
`panel-<arg>` and `page-<arg>`, and separately check that the handler's
leading global exists, refusing any name preceded by a dot (detector-defect
#2).

| App | Nav class | Controls | Distinct targets | Dead nav | Missing global |
|---|---|---|---|---|---|
| StoneDesk | `.sidebar-btn`, `.sb-btn` | 68 | 67 | **0** | **0** |
| SAIRNbiz | `.sb` | 20 | 20 | **0** | **0** |
| SAIRNvet | `.sidebar-btn` | 57 | 57 | **0** | **0** |

**145 controls, 144 distinct targets, zero dead, zero missing globals.**

**The selector had to be found, not assumed, and that is a finding about the
method.** SAIRNbiz uses `.sb`; the first sweep used StoneDesk's `.sidebar-btn`
and returned **0 controls and 0 findings** — a clean-looking result over no
data, the vacuous-green shape. It was caught by refusing to report a zero
without first enumerating every `[onclick]` element and its classes. A
re-implementation will make this mistake; the table above names the class each
app actually uses.

---

## 3. SAIRNvet CANNOT BE SIGNED INTO — the documented credential is dead

The one genuine regression this run found, and it blocks the render half for
SAIRNvet independently of the throttling.

`docs/2026-09-03-demo-credentials.md` lists `SV-PINNACLE-2026` /
`sairn-demo-owner` / PIN `38471260`, minted 2026-09-23 through the app's own
bootstrap. Driven live today:

```
POST /api/sv-auth  login  documented PIN   -> 401 INVALID_CREDENTIALS
POST /api/sv-auth  login  deliberate wrong -> 401 INVALID_CREDENTIALS   (control)
POST /api/sv-auth  login  unknown employee -> 401 INVALID_CREDENTIALS   (control)
POST /api/sv-auth  bootstrap               -> 409 ALREADY_PROVISIONED
```

**The two controls are the point.** The endpoint answers identically for a
wrong PIN and an unknown employee — correct design, no user enumeration — so
from outside it is NOT possible to tell whether the PIN changed or the account
is gone. What IS certain: the documented credential does not work, and
`SV-PINNACLE-2026` is closed to `bootstrap`, so there is no self-serve way
back in. **SAIRNvet is unenterable with what is written down**, which is the
same blocker the 2026-09-23 run had to clear before it could run at all.

**SAIRNbiz's primary listed credential is also dead:** `SB-PINNACLE-2026` /
PIN `60417293` answers 401. The second row, `SB-TEST-2026` / PIN `84350271`,
works — so SAIRNbiz is reachable and the doc is half stale.

**StoneDesk's `SD-AUDIT-2026` / `31840627` works** (200, role `owner`).

Two of the three Wave 3 rows in the credentials document are stale. That is
the expired-fixture class this week keeps finding, now in the document a
session reaches for when it needs to get in.

---

## 4. One thing confirmed live, because it was worth confirming

The SAIRNvet notice fixed on 2026-09-24 is deployed and correct:
`identify a role, not a named person` renders; the old claim
`SAIRNvet has no per-employee sign-in` survives **once** in the source and is
**not visible to a user** — it is inside the HTML comment that supersedes it
in place (`sairnvet.html:550`), which is the house convention working as
intended. Checked against `document.body.innerText`, not the markup, because
the markup cannot tell a claim from its own history.

---

## 5. What this run does NOT say

- **No panel body was rendered or read.** Every statement above is about
  reachability and wiring, never about what a panel displays.
- **No form was filled, nothing submitted, no in-panel control clicked.**
- **SAIRNvet was never signed into**, so even its nav-resolution result is
  from the pre-auth DOM. All 57 panels exist in markup at load; whether
  `showPanel`'s role gates admit an owner was not exercised.
- **One role, one licence per app, near-empty data**, same limits the
  2026-09-23 document states.
