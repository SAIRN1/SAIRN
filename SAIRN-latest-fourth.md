# SAIRN — latest from `fourth` (ted) — batch b23, 2026-10-15

**CHAIN TIP** `80d86329` *(the handoff; report/digest/latest land after it — re-derive with `git rev-parse HEAD`)*
**STATE** `HEAD == origin/main`, 0/0, clean, **not forced on either push — proved by ancestry**, not by grepping git's wording.
**MANIFEST** 6 of 6 done. No `SAIRN_SEED_GATE`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SKIP`; `settings.json` untouched; **0 `api/` `sql/` `tests/` `tools/` files written** — all read-only here by claim.
**CONTEXT** 61% of 1000k, measured by `tools/sairn_status_line.py` on this session's transcript.

## DIGEST

**PAYROLL IGNORES AN APPROVED CLOCK CORRECTION — 60 minutes and $20.00 unpaid on one visit, DRIVEN.** hank b13 asked whether an *unapproved* time could reach payroll. It cannot: a pending correction leaves payroll at 240 minutes, identical to no correction. **The mirror image is the defect, and it is money on a federally mandated EVV record** — 240 min / 8000¢ as shipped against 300 min / 10000¢ with `effectiveClock` applied. `api/_lib/sen-payroll.js:200-201` reads `row.clock_in_at` raw and never requires `sen-evv-clock.js`, while that module's own comment at `:342-344` says the rule is *"implemented HERE, in the function payroll reads"*. **The function payroll reads is `instant(row.clock_in_at)`.** Two more consumers read raw: the federal EVV readiness summary (defensible, **undeclared**) and `sairnsenior.html`, which has **zero** references to `effective_clock` — so the corrected value is reachable by nobody.

**`alf_staff` T18: right direction, one branch short.** No consumer coerces `null` to `false`. But `applies_to` is a `=== true` **whitelist**, so an *undecided* requirement lands in the same bucket as a decided `false` and its hours vanish from `required_annual_hours` — and the disclosure fires **only when nothing matched**. A partially-undecided audience, which is T18's own case, gives a surveyor a confident lower figure with no caveat.

**THE 69 AND 151, CLASSIFIED — a count of a SHAPE is not a count of DEFECTS.** 332 guards; classified by the guarded fetch's **method** and what its URL **interpolates**. **22 REAL HIGH** (write-guarded, so a `23514` from the 64 KB cap answers *"run the migration"*), **13 REAL MODERATE** (GETs interpolating a caller value), 33 not caller-reachable and **untested**, **2 unclassified and reported as such**. **And my own b22 severity on the 151 is withdrawn as to reachability**: none guards a write, none interpolates a caller value. What remains there is **deploy-reachable** — a dropped column answers `42703` as 400 and renders `ok:true, data:[]` on 150 read paths.

**5 of 5 of cody's mutants caught**, including the four b22 left uncorroborated, by running a *copy* of the probe whose `ROOT` is a tempdir. M1 returns **exit 2** printing *405 passed, 14 failed* — b22's figure from a second route, and the refusal is correct.

**My anchor check ablated both ways.** Fix removed → arm fails; restored → arm passes. Every one of four layers load-bearing per arm. **L5 is a finding about my own tool:** the fail-closed guard lives in `main()` and not `check()`, **so no fixture arm can see it** — driven directly instead, exit 2 in both absent directions.

**The 373 bare citations is an actual 371.** 571 occurrences classified: 198 qualified, 323 bare single lines, **48 bare RANGES**, one OAC chapter number, one ISO timestamp. b22 was high by exactly two, both named. **cc's 323 is the single-line form only — the 48 ranges are the difference, and no tool here can assess them**, because a range cannot be checked by any single-line lookup.

## THE STATE CHANGE THAT MATTERS

**MICHAEL'S `leg_aftercare` CONDITION IS NOW MET.** Measured: 2 active claims (mine and cody's b16), **hank has none**, cody's b16 does not name it and says *"NO api/ FILE (hank)"*, and hank's key fix **is on `origin/main`**. **It is unblocked and still mine. I did not start it and did not hand it to anyone** — the batch was six items and the handoff is the stopping point.

## DECISIONS WAITING — nothing blocking

1. **F2** — should the state aggregator receive the device clock or the approved correction? Either is arguable; **the silence is not**.
2. **hank's (c)** — a marked `self_approved` on an EVV record. My view: **yes, with the marking**, if the flag survives into the submission.

## OPEN, BY OWNER

* **hank** — **F1 first** (apply `effectiveClock` in the payroll action's map), then the 22, then the 13, then read `:13503` and `:17127` by hand, then decide the read-case fifth answer before touching the 151. Plus F2, F3, F4 and the status-less-entry write guard.
* **cc** — **wire ONE anchor-rot tool into a gate.** Both are **UNWIRED**, and cc's A7b **cannot fail on a real rot** by design — so the chain has no live link, which is rule 1.1 one level out. Then delete mine. Also: R3 should count the 48 ranges.
* **cody** — a failing-first arm driving a `23514` through one of the 22 and a `42703` through one of the 151. **Nothing in the repo drives either today.**
* **fourth** — the `leg_aftercare` Tier A, and an arm for L5.

## METHOD NOTE

**Two of my own predicates failed inside this batch, and both failures were POSITIONAL rather than lexical** — a `select=` test matching the trailing paren of every URL, and a body-read detector matching `code: 'NOT_PROVISIONED'` *inside the answer*. b22's clause was *"when a predicate names an identifier, say which identifier"*. **This batch adds the sibling: SAY WHERE THE PREDICATE LOOKS.** A predicate has a **span** as well as a pattern, and the span is the half nobody writes down. **And the third correction was a SEVERITY, not a count** — a shape count reads as a defect count unless the report says which it is.

*Full detail: `SAIRN-report-fourth-b23.txt`, `SAIRN-handoff-fourth-b23.md`. Every figure names the command that produced it — re-derive anything you mean to quote, including out of this file.*
