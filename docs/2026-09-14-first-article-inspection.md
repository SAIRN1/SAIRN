# Item 47 — First Article Inspection on the two checkers shipped tonight

**2026-09-14 (Hank).** Report only, never gated, per the item's own terms.

**Subjects:** `api/audit-checkpoint.js` (item 35) and `api/cron-watchdog.js`
(item 54), both by Fourth, both shipped tonight.

---

## What FAI asks, and why it is not the review that already happened

CC ran an **adversarial** review of both a few hours ago (`86370678` →
`5b433b19`) and it found a real defect — `bc9a650b`, *"the checkpoint pager's
completeness guard vanished when its input did."* That review asked *"can a
hostile reader find a bug."*

**FAI asks a different question: is every STATED requirement verified,
exhaustively.** A thing can survive a hostile reader and still have a claim in
its own header that nothing checks. The two are not substitutes, and running FAI
after an adversarial pass is not duplication.

**Where the requirements come from.** On this platform a new artefact's
requirements are the claims its own header makes about itself — *"fails closed"*,
*"refuses when X"*, *"never Y"*. That is the spec it will be read against.

**The two lists are not matched automatically, and must not be.** Pairing a
prose claim to a prose arm label is word-overlap scoring, which on this platform
returned 38% with five false positives out of five. The worksheet prints both
lists; a human maps them.

## Result: both pass, and that is the finding

| | claims in the header | arms in the suite | unverified claims |
|---|---|---|---|
| `api/audit-checkpoint.js` | 8 | 38 | **0** |
| `api/cron-watchdog.js` | 6 | 55 | **0** |

Every stated claim has an arm. Spot-checking the ones most likely to be
decorative:

- *"every page is fetched explicitly AND the total from Content-Range is
  compared against what was actually read"* → **A31** (an incomplete window read
  refuses) and **A32** (a window whose row count is not stated refuses too),
  with **A33** as the control that an exact count still writes — so the guard is
  not simply always shut.
- *"it does NOT catch an insertion into the current, not-yet-closed window"* →
  **A14** (today is not checkpointed) and **A23** (a row added after the last
  checkpointed window is not a finding).
- *"a job that never beat has no row, so a table scan alone cannot see it"* →
  **A12**, with **A13** distinguishing `NEVER_BEAT` from `LATE`, and **A3**
  asserting the declared list is non-empty so A1 and A2 cannot pass vacuously.

**Reporting a clean FAI is the point, not a disappointment.** The question was
whether a new checker gets verified against every requirement or only
spot-checked. On these two the answer is every requirement — and now it is
recorded, so nobody has to re-derive it.

## The one thing FAI surfaced that the adversarial review did not

`api/cron-watchdog.js` states a limit no arm can cover, correctly:

> *"This watchdog runs on the SAME Vercel cron scheduler as the jobs it watches.
> If that scheduler stops, the watchdog stops with it and reports nothing — two
> units sharing a failure mode … a second copy is not a second opinion."*

**That is not a missing test. It is an accepted risk**, and Fourth handled it
well: they named it, **built the out-of-band half** (`tools/cron_liveness_check.py`,
which runs outside Vercel and survives a total scheduler outage), and escalated
the residual as *"a decision about spend and vendors, not something to invent
quietly in a file."*

**What was missing is the same thing that was missing from `portal.js` this
afternoon: it lived in a file header and nowhere central.** Now `AR-4` in
`docs/ACCEPTED-RISKS.md`.

So FAI's real yield here was not a defect — it was **a requirement-level
distinction the arm-by-arm view cannot make**: telling a claim that *should*
have a test from one that *cannot*, and routing the second somewhere a future
reader will find it.

## What this inspection does NOT claim

- **Two artefacts, chosen because they shipped tonight.** Nothing here says
  anything about the other 109 tools.
- **Claims were extracted from header comments by regex** and the box-drawing
  rules in those headers mangled several into fragments; the mapping above was
  done by reading the files, not from the extractor's output. **A tool for this
  was not built** — the extractor is a worksheet in the scratchpad, and
  promoting it would mean shipping a claim-counter whose count is not
  trustworthy.
- **An arm existing is not an arm being right.** FAI checks coverage, not
  correctness. Correctness on these two is what CC's adversarial pass covered,
  and it found something.
