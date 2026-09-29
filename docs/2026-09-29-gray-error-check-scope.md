# Silent gray errors — one concrete check, scoped

**2026-09-29 (Hank).** Item 14 of queue23. **SCOPE ONLY — nothing built.**

A **gray error** here means: code that passes its own tests and does not do what
the dispatched instruction asked. Green suite, correct-looking diff, wrong work.

---

## The real instance, from this platform's history

I looked for one rather than inventing one, and there is a clean example **from
this session**, which makes it better evidence than an old one because the record
is complete.

**Dispatched (queue22, item 6):** *"sv_financials, dnt_vendor_orders, leg_insurance
and msb_food_waste are likely Tier A on the money limb."*

**What I did with `msb_food_waste`:** read it, found the routed claim **not
supported**, and left it at B with the re-read recorded.

**That is the correct outcome.** And notice what a test could have said about it:
nothing. `criticality_tier_check.py` exits 0 whether that row is A or B — it
checks that the table is internally consistent, not that a judgement is right.
**Every mechanical check on this platform was green for both the right answer and
the wrong one.**

The instruction said *"likely Tier A"*. A session in a hurry promotes it; the
checker is happy; the rollup is happy; the probe is green. **The only thing
standing between the dispatch and a wrong Tier A was a session choosing to read
`computeMsbFoodCostPct()` and report back that the premise was false.**

**And the same paste contains the opposite case.** `msb_sale_hours` was dispatched
as *"B to A on integrity"* and that one WAS right — but the cell asserting
otherwise had been written on 2026-09-23 by a session that read the resource's two
write sites, concluded "display only", and was wrong for seven weeks. **Green
everything, again.**

**So the instance is not one event, it is a matched pair**: a dispatch that was
wrong and was caught by reading, and a dispatch that was right about a cell that
was wrong and had survived a previous read. Tests were silent in both directions.

---

## The check

**`tools/dispatch_interpretation_gate.py` — a PRE-WORK restatement, compared to
the item text, by a session that is not the one doing the work.**

### How it runs

1. **At dispatch**, the paste is split into numbered items and stored verbatim —
   `docs/dispatch/<date>-<queue>.json`. Verbatim is load-bearing: the whole check
   is a comparison against what was *actually asked*, and a paraphrased copy makes
   it a comparison against a paraphrase.

2. **Before touching any file for item N**, the working session writes a
   **restatement**: what it believes the item asks, what it will change, and
   **what it expects to find** — in its own words, at most a few sentences.
   Stored beside the item.

3. **The gate compares the two** and emits a **DIVERGENCE REPORT**, not a verdict:
   claims in the item with no counterpart in the restatement, and claims in the
   restatement with no counterpart in the item. It does not decide who is right.

4. **A second session reads the divergence report.** Not the code — the two
   statements. That is a minute of reading against an hour of building.

### What it catches that tests do not

| | |
|---|---|
| **A premise in the dispatch that is false** | `msb_food_waste` was *"likely Tier A"* and was not. A restatement saying *"promote it"* diverges from a restatement saying *"check whether the cost reaches a computation, then decide"* — and the divergence is visible **before** the row moves. No test distinguishes these. |
| **Scope that quietly narrowed** | The item names four resources; the restatement names three. Mechanically detectable, invisible to every test, and the commonest way a dispatched item gets half-done. |
| **Scope that quietly widened** | The restatement names a file the item does not. This is how an unrelated refactor rides along inside a claimed change. |
| **A judgement presented as a fact** | The item says *"likely"*, *"possible"*, *"probably"*; the restatement says *"promote"*, *"fix"*, *"correct"*. **The hedge is the most information-dense word in a dispatch and it is the first thing lost in restatement.** Flagging a hedge that disappears is the single highest-value rule in the whole check. |
| **The wrong subject entirely** | The item says `sv_mobilevet`; the restatement says `sv_farmcalls`. Rare, catastrophic, trivially detectable. |

**And what it does NOT catch, stated because the boundary is the design:**
the restatement can be *accurate and still wrong*. A session that misreads the
item and restates the misreading faithfully produces a low-divergence report. **It
catches a mismatch between the ask and the plan, never an error inside the plan.**
That is the whole limit and it is why a human reads the report.

### Per-paste cost, estimated honestly

| Step | Cost |
|---|---|
| Storing the paste verbatim | one command at dispatch, seconds |
| Restating, per item | **2–4 minutes of the working session** |
| Running the gate | seconds |
| A second session reading the report | **~1 minute per item** |
| **Per 8-item paste** | **~25–35 minutes across two sessions** |

Against that: this session has produced **three findings whose whole content was
"the stated reason is wrong"** — cc's B1, the `msb_sale_hours` cell, and
`msb_food_waste` — and one of them had survived seven weeks. A single avoided
wrong Tier A on an alcohol-sale control is worth a day of restatements.

**The cost is real and it lands on the wrong side of the ledger**, which is the
honest problem with the whole proposal: the session that pays is the one doing the
work, and the session that benefits is the next one.

### How it could false-pass — four ways, and the fourth is fatal

1. **Restating from the code instead of the item.** Write the item's restatement
   *after* reading the file and it converges on what the code says. **Mitigation:**
   the restatement must be written before the first file read of that item, and
   the gate timestamps it. Weak — nothing enforces reading order.

2. **Vacuous restatements.** *"Do item 6."* Zero divergence, zero information.
   **Mitigation:** a minimum-content rule (must name a file, a resource, and an
   expected finding). Mechanical and easy to satisfy hollowly.

3. **Divergence fatigue.** Every restatement diverges somewhere; the report becomes
   noise; the second session stops reading. **This is the failure mode this
   platform records most often about report-only tools**, and I have no mitigation
   beyond keeping the rule set tiny — hedge-loss, subject-swap, scope-narrowing,
   and nothing else.

4. **THE FATAL ONE: the same session writes the restatement and does the work.**
   Then the restatement is not an independent statement of intent, it is a
   *prediction of what the session was going to do anyway*, and the gate compares
   the session's plan to its own plan. **A detector blessing its own subject —
   item 8 one step later, and exactly the shape the twelve disciplines name under
   human-gated auto-remediation.** It is only a check if a *different* session
   reads the report, and nothing in a queue-driven workflow guarantees one is
   available.

---

## Recommendation: **DO NOT BUILD IT YET. Build one rule of it.**

**Not the gate. The hedge-loss rule, alone, as twenty lines.**

The argument is failure mode 4. A restatement-versus-item comparison needs a
second session to mean anything, and this platform's sessions are queue-driven and
frequently the only one awake. Building the full gate produces a tool that is
either ignored (nobody reads the report) or self-blessing (the author reads their
own). Both outcomes are worse than nothing, because both *look like* coverage.

**What survives that objection is one narrow rule that needs no second reader:**

> **Extract every hedge from the dispatched item — *likely*, *possible*, *may*,
> *probably*, *appears*, *I think* — and require the working session's commit
> message to either carry the hedge forward or state the finding that removed it.**

That is checkable **against the commit message**, which already exists, is already
written by the working session, and is already read by the push gate. No
restatement step, no second session, no new artifact, no new cost.

It would have fired on `msb_food_waste` — the item said *"likely Tier A"*, and a
commit promoting it without a sentence saying *what made it certain* is exactly
the thing to stop. And it would have passed the work I actually did, because that
commit says in terms: *"the routed finding said LIKELY TIER A. IT IS NOT, and the
re-read is recorded rather than the finding quietly dropped."*

**One rule, one artifact that already exists, no second session required. Build
that; leave the gate on the shelf with this document as its design.**
