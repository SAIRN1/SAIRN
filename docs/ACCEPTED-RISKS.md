# Accepted Risks — decisions to live with something, in one place

**What this is.** A risk somebody weighed and deliberately chose to accept,
with who accepted it, why, what bounds it, and **the trigger that means
re-read this**.

**Why it exists, and it is one day old.** On 2026-09-14
`api/sairncash/portal.js` was read as an unrecognised security gap — twice in
one afternoon, by me, after I had read the paragraph that says otherwise. The
file's own header carries a careful, correct acceptance and ends *"recorded here
rather than left to be discovered."* **That was true of the file and false of
the platform.** It reached neither the open-work index nor the SOUP register, so
it was invisible to anyone not reading that one file.

> **An accepted risk that only one file knows about is indistinguishable from an
> unnoticed one.** The cost is not that it gets missed — it is that it gets
> *re-found*, argued about, and written up again by somebody who thinks they
> discovered it.

Same shape as the information-leakage problem one level up: the knowledge
existed and no register owned it.

---

## The rule this register is built on

**Every entry names a trigger, and a trigger nobody watches is not a trigger.**

`docs/SOUP-REGISTER.md` recorded *"`STRIPE_SECRET_KEY` is not currently
configured … Re-read this entry at that moment."* The moment came, nothing
watched for it, and the register stayed wrong for days — while the only visible
signal, `checkout.js` answering *"Stripe not configured"*, went on saying the
same thing **for a different reason**.

So a trigger here must be one of:

- **mechanical** — a checker that already runs, named by tool;
- **an event with an owner** — a named person, at a named moment;
- **honestly none** — say so, in those words. A blank is a lie; *"nothing will
  tell us"* is a fact somebody can act on.

## Not the same as the other registers

| Register | Holds |
|---|---|
| `docs/defect-density-register.json` | defects that were **found** |
| `docs/SOUP-REGISTER.md` | third-party components and why each is trusted |
| `docs/CRITICALITY-TIERS.md` | what each resource is worth |
| **this file** | **things known to be wrong and deliberately left** |

A defect record answers *"what happened."* This answers *"what did we decide to
live with, and when should that be revisited."*

---

## The entries

### AR-1 — a leaked Stripe subscription id is a working key to that customer's billing

- **Where:** `api/sairncash/portal.js`
- **Accepted by:** the file's author, recorded in its header
- **The risk, stated at the consequence rather than the mechanism:** possession
  of a `sub_…` id gets anyone a Stripe Billing Portal session for that customer
  — card on file, invoice history, the power to cancel. No licence key, no
  session, no proof of ownership.
- **Why accepted:** it is materially better than the alternative it replaced
  (accepting a `cus_…` id), it matches what the client already holds, and
  tightening it needs a server-side session that SAIRNcash does not have.
- **What bounds it:** the id lives in the customer's own `localStorage`, so it
  is not public. **That is a bound, not a control.** And what actually stops
  exploitation *today* is unrelated to any of the above: production's
  `STRIPE_SECRET_KEY` is an **expired `sk_test_` key**, so every call dies at
  Stripe. Nobody chose that.
- **Trigger — MECHANICAL for the producer, NOT WATCHED for the event. CORRECTED 2026-09-15, and the correction is the useful part.**
  This entry said **MECHANICAL** and named `api/_lib/stripe-config.js`, which
  returns a `warnings` entry for a test key in a production deployment. That was
  true about the module and **false about the platform**:
  `tools/weakness_combination.py` found that **nothing on this platform consumes
  that signal** — not `report_only_checks`, not the push gate, not
  `run_all_tests`, not a hook, not a workflow. It reaches a log and stops. **The
  signal was PRODUCED and never CONSUMED**, and this register's own rule is that
  a trigger nobody watches is not a trigger.

  It is also **log-only by design and must stay that way** — the client message
  deliberately names no variable, so there is nothing for a checker in this repo
  to read. That is correct behaviour, not a gap to close.

  So the trigger is now stated as the two halves it really has:

  - **GUARDED, MECHANICAL:** `api/_lib/stripe-config.test.js` — a new suite,
    and it is in `GUARD_TESTS`, so it can block a push. **The module had NO
    SUITE AT ALL** until 2026-09-15, which meant the branch producing this
    entry's trigger could have been edited away with the only consequence being
    that an accepted risk's trigger quietly stopped existing. Its four-cell
    control is the load-bearing one: of (test key, live key) × (production,
    preview) **exactly one must warn**, because AR-1's trigger reads the
    ABSENCE of that warning and a banner that fires everywhere has no absence.
  - **NOT WATCHED, and said plainly rather than left implied:** whether a
    working live key has actually been installed in production. **Nothing here
    will announce that.** It needs a live environment read, which is a decision
    about how this platform observes production and not something to invent in
    a file.

- **Open with:** Michael (auth mechanism), 2026-09-14. **The live-key question
  is also Michael's** — either a live environment read, or the acceptance that
  this entry's real trigger is a person noticing, 2026-09-15.

### AR-2 — "current" means two different things in two live apps

- **Where:** `api/_lib/credential-expiry.js`
- **Accepted by:** the file's author, recorded in its header
- **The risk:** a genuine platform inconsistency — two shipped apps use the same
  word for different conditions, so a reader comparing them draws a wrong
  conclusion. Only the arithmetic underneath is shared.
- **Why accepted:** *"reconciling it changes what two shipped UIs display, which
  is a product decision, not a refactor."* Correct, and the reason it was not
  resolved by fiat.
- **What bounds it:** each app keeps its own wrapper and its own vocabulary, so
  neither app is internally wrong — the inconsistency is only visible across
  them.
- **Trigger — an EVENT WITH AN OWNER:** the next time a third app adopts this
  module, or either app's credential UI is reworked. **Nothing mechanical will
  announce it**, said plainly rather than left blank.
- **Open with:** unassigned.

### AR-3 — EVV readiness warns where the rule was never verified

- **Where:** `api/_lib/sen-evv-readiness.js`
- **Accepted by:** the file's author — *"Warned, not failed, with the ambiguity
  named."*
- **The risk:** whether a partial location capture (clock-out but no clock-in,
  or the reverse) satisfies Electronic Visit Verification **depends on the state
  and the aggregator, and has not been verified against either.** The module
  emits a warning rather than a failure. **EVV is a Medicaid billing
  requirement**, so a visit that reads as ready and is not is a rejected claim
  or worse.
- **Why accepted:** guessing a per-state rule would be inventing a compliance
  fact, which is worse than declaring the ambiguity. The refusal to guess is
  correct.
- **What bounds it:** the warning is surfaced with the ambiguity named, so
  nobody is told the visit is fine. **Nothing bounds the downstream
  consequence** if a user treats a warning as a pass.
- **Trigger — an EVENT WITH AN OWNER:** the first time a real state or
  aggregator is named for SAIRNsenior. At that moment the ambiguity is
  resolvable against a primary source and this stops being a judgement call.
- **Open with:** unassigned.

### AR-4 — the cron watchdog shares a failure mode with the jobs it watches

- **Where:** `api/cron-watchdog.js`
- **Accepted by:** the file's author (Fourth), recorded in its header
- **The risk:** the watchdog runs on the **same Vercel cron scheduler** as the
  jobs it watches. *"If that scheduler stops, the watchdog stops with it and
  reports nothing — two units sharing a failure mode, which is convention 7's
  exact lesson: a second copy is not a second opinion."* It is a watchdog for
  **one job failing**, not for the platform failing.
- **Why accepted:** closing it completely needs a hosted uptime check pinging
  from a third party — *"a decision about spend and vendors, not something to
  invent quietly in a file."* Correct, and the right call to escalate rather
  than assume.
- **What bounds it, and this is the strong part:** `tools/cron_liveness_check.py`
  runs **outside Vercel**, reads the same heartbeats, and is the only thing that
  survives a total scheduler outage. The mitigation was built, not just named.
- **Trigger — an EVENT WITH AN OWNER:** Michael, on the spend-and-vendor
  decision. **Nothing mechanical closes this**, and nothing should pretend to:
  any checker that could detect a total scheduler outage would have to run
  outside the scheduler, which is the out-of-band tool that already exists.
- **Open with:** Michael (third-party uptime check), 2026-09-14.
- **Found by:** the item 47 First Article Inspection, not by a defect.

---

## What this register does NOT claim

- **It is not complete, and it starts today.** `tools/accepted_risk_scan.py`
  located these; it is a **locator, not a detector**, and it reads language, not
  intent. Of six weight-3 candidates in the first run, **two were real** —
  the others were the phrase *"is accepted"* inside a test assertion and inside
  a comment about a licence-key prefix. **Roughly one in three**, which is why
  the output is a read-list and its count is not a score.
- **It is not backfilled.** Same rule as the defect register: every entry here
  was read by somebody who could attest to it. Reaching further back would mean
  classifying comments nobody present can vouch for.
- **Being listed here is not approval.** It records that a decision was made and
  by whom. AR-1's residual risk is open with Michael.
- **The scan cannot see an acceptance written in plain prose** with none of the
  phrases it knows, and it cannot see one made in a commit message, a handoff or
  a conversation and never written into the code at all. Those are invisible to
  everything, which is the argument for writing them here.
