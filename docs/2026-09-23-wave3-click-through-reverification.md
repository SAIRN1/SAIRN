# Wave 3 click-through re-verification — StoneDesk, SAIRNbiz, SAIRNvet

**Run 2026-09-23, signed in, against the deployed apps at `sairn.vercel.app`.**
Driver: `tools/sairn_clickthrough_driver.js`.

This closes a task that had been dispatched "long ago" and, when Fourth went
looking for it on 2026-09-23, **left no trace anywhere** — no commit, no doc,
no index row, no claim. That absence was reported as its own finding rather
than as "not done", because those are different facts and only one was
established. This document is the result of running it rather than searching
for it.

---

## The result

| App | Nav controls | Driven | Dead nav | Blank | Threw | Handler missing |
|---|---|---|---|---|---|---|
| StoneDesk | 67 | 67 | 0 | 0 | 0 | 0 |
| SAIRNbiz | 20 | 20 | 0 | 0 | 0 | 0 |
| SAIRNvet | 62 | 62 | 0 | 0 | 0 | 0 |

**149 of 149 nav controls clean.** StoneDesk's 67 resolve to 64 panels and 3
`.page` modules; SAIRNvet's 62 resolve to 57 distinct targets, because five
panels (`diagnoses`, `drugdb`, `pharmacy`, `soap`, `controlled`) are reachable
from two places each — two routes to one panel, not a defect.

**What a clean run means, and the limit is not a footnote.** It clicks NAV
ONLY. It does not fill a form, submit anything, or click a control inside a
panel — deliberately, because on a live licence those write real rows. So this
says every panel opens, renders and wires its handlers. **It does not say any
feature works.** The static half (syntax, nav/panel reconciliation, div
balance, reachability, dead-button audit) was already clean on all three; this
is the half Guardian's own *Known Scope Limitation* says no code-level pass can
reach.

---

## The detector was wrong four times before the apps were wrong once

Every version of the driver produced confident findings against clean apps.
Recording them because each is a distinct, named class, and a reimplementation
will make them again.

### 1. A wrong model of the page — 3 findings

v1 assumed a nav id resolves to `panel-<id>`, and reported **Field Quote, Doc
Scanner and Check Register as dead nav buttons.** They are `.page` modules with
`page-<id>` ids, shown by a second nav system (`window.showPage`).

`showPanel`'s own comment at `stonedesk.html:13031` says so in plain words:
*"The `.page` modules (Field Quote, Doc Scanner, Check Register) render on top
of a cleared panel area."* Three findings against a working feature, in a file
that had already written down the answer.

`resolve()` now tries `<arg>`, `panel-<arg>` and `page-<arg>`, and takes the
nav ARGUMENT rather than the button id — `svNav()` is passed the full
`panel-x`.

### 2. A method call is not a global — 20 findings

v1 matched `name(` anywhere in a handler attribute and collected
`preventDefault`, `getElementById`, `reduce`, `toFixed`, `click`, then reported
them missing because `window.preventDefault` is of course undefined. Twenty
findings, one mistake. The pattern now refuses a name preceded by a dot.

### 3. Text inside a string literal is not code — 3 findings

Even after (2), `panel-priceintel` reported `Entry`, `Mid` and `Premium`
missing. They are words inside quoted ARGUMENTS — material names like
`'Granite Entry (Lv 1-2)'` — and `Entry (` reads as a call to a regex that
cannot see quotes.

**Measured on the live page rather than reasoned:** 4 hits before stripping
string literals, 0 after. This is PR §1.2, arrived at independently on a
surface that section does not mention.

### 4. A fixed wait cannot measure an async render — and re-checking made it worse

SAIRNvet's `panel-access` ("Sign-in Access") measured **0 controls**.
`svRenderAccess()` writes *"Loading sign-ins…"* and then fills the table from a
real `/api/sv-auth` round trip, which takes longer than the 320ms wait. What
got measured was the placeholder.

**THE TRAP IS THE SECOND PASS.** Re-running the driver reproduced 0 controls
*exactly*. That reads as confirmation and is the opposite: clicking the control
**re-arms** the render, resets the container to the placeholder and refetches.
Two passes agreeing meant only that the same race had been run twice.

`SCT.settle()` is the measurement that races nothing — it clicks nothing, reads
every target after the run, and uses `textContent` because `innerText` returns
`''` for a hidden element. Settled, `panel-access` is **text=302, ctrls=1** —
the Deactivate button is there, exactly as `svRenderAccess()` emits it for an
owner. Zero panels have zero controls when settled.

### And one that was not the detector's fault at all

The first StoneDesk run was driven in a **background tab**. Chrome throttles
`setTimeout` in a hidden tab to roughly nothing, and `sbNav` puts every panel's
render hook inside one — so all 67 panels would have read blank. **Sixty-seven
findings, none of them about StoneDesk.**

The driver now records `document.visibilityState` in its own output, so a
throttled run is visible rather than believed, and the header says the tab must
stay foreground. This one is worth more than the other four combined: the other
three produced findings a human would have checked and dismissed. This one
would have produced a uniform, plausible, catastrophic-looking result.

---

## What had to be true first

**SAIRNvet had no credential at all.** `SV-PINNACLE-2026` was seeded and
`check_license` returned `{ok:true, active:true, app_id:'sairnvet'}`, but
`sv_employee_auth` was empty — nobody could sign in, and the app had therefore
never been click-through verified. A credential was minted through the app's
own `bootstrap` action and recorded in `docs/2026-09-03-demo-credentials.md`
(`1a3e53ca`), including that `SV-PINNACLE-2026` is now closed to `bootstrap`
permanently.

**The trial gate blocked every app, and it is not a licence property.**
`checkTrialGate()` reads `localStorage['sd_trial_start']` — per browser, no
server input, no renewal path. Eight apps in the audit browser were past 30
days (StoneDesk 36, SAIRNbiz 35, SAIRNvet 35, SAIRNdesign 35, SAIRNlaw 35,
SAIRNcode 34, SAIRNlegacy 34, SAIRNcare 31). Server-side `SD-AUDIT-2026` was
never expired: `check_license` and `login` both returned 200 throughout. The
separate server-side gate reads `trial_ends_at`, which is not a column, and
arming it would have activated three dormant handlers platform-wide.

**A finding fell out of checking the credentials, not the apps.** All
seventeen `api/*-auth.js` endpoints accepted a licence issued for a different
app — a StoneDesk key got 200 from `/api/sv-auth`. Fixed and live-verified
separately (`f27a9cd5`): 14/14 foreign combinations now refused, 15/15 own
licences still admitted.

---

## What this does not cover

- **Nav only.** No form filled, nothing submitted, no in-panel control clicked.
- **One role.** Everything was driven as `owner`. `showPanel` carries role
  gates (`executive`, `publiccatalog` refuse a non-owner), and those refusal
  paths were never exercised — a run as a shop-floor user would drive
  different code.
- **One licence per app**, each with near-empty data. A panel that renders
  correctly with two rows may not with two thousand.
- **`panel-access` is the only panel whose content arrives from the server
  after the click** that this run happened to notice. Others may exist and
  would have been measured mid-fetch the same way; `settle()` now covers them
  mechanically, but this run is the first to use it.
