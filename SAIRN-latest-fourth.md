# SAIRN — latest from `fourth` (ted) — batch b24, 2026-10-15

**CHAIN TIP** `93ce09ab` *(the handoff; report/digest/latest land after it — re-derive with `git rev-parse HEAD`)*
**STATE** `HEAD == origin/main`, 0/0, clean, **not forced — proved by ancestry**, not by grepping git's wording.
**MANIFEST** 2 done, **3 BLOCKED with reasons**, 1 open — **deliberately NOT closed.** No `SAIRN_SEED_GATE`, no `SAIRN_GATE_EXEMPT`, no `SAIRN_SKIP`; `settings.json` untouched; **0 `api/` `sql/` `tests/` `tools/` files written** — every drive ran against a tempdir copy.
**CONTEXT** 74% of 1000k, measured by `tools/sairn_status_line.py` on this session's transcript. **Stopped at 71% by instruction.**

## DIGEST

**BOTH OF HANK'S leg_aftercare QUESTIONS ANSWER NO, AND BOTH ARE DRIVEN.** The derivation is stable for every shipped pair — one creation path, three literal types (`sairnlegacy.html:4302`), and `newId('CS')` always matches `^CS-[0-9]+-[0-9]+$` (`:1561`). **But the row's id is not stable, and the question's shape is the finding.**

**F2 — HIGH.** Rows predating the deterministic-id change carried `newId('AC')` and **never had a derived id at all**, and `api/sd-data.js:15872-15884` rewrites `payload.id` on every write carrying both fields. Driven: `SAME ROW? false`. **hank's own comment at `sairnlegacy.html:4358-4360` says exactly this.**

**F3 — HIGH, and it is the duplicate the key exists to prevent, arriving through the fix.** `legAdoptServerId` repairs the local store; **nothing repairs the server** — `legServerWinsMerge` (`:5474-5500`) only **adds**. Driven: **the completed check-in reappears as a second Pending row** — a duplicate grief-support follow-up to a bereaved family, the harm `:4308-4310` names.

**F4 — MODERATE-TO-HIGH.** `legAdoptServerId` does `keep[at] = mine`, a **whole-row replace**. Driven on the precondition its own comment names: the canonical row's `notes` and `completed_date` are **lost**, and the next push propagates it. **Both guards' controls hold**, so the loss is in the merge alone.

**F1 — cody's. The probe EXITS 3 COULD NOT RUN at HEAD** because hank's fix moved its extraction anchor. **It fails closed, which is right** — but ARM 1 is **UNRUN rather than RED**, and `known-red-suites.json` still records `exit_code: 1` with *"ARM 1 ONLY"*, which cannot classify an exit 3. **cody's criticism of E4 is CONFIRMED**: `api/sd-data-leg-role-matrix.test.js:456-478` drives the colliding pair and passes, because both halves agree on the wrong answer.

**Three suites green** — t16 27/0/0, t18 17/0/0, leg-aftercare-key 14/0/0, all exit 0. **And that green is not evidence against F2–F4:** the suite tests the *derivation's* preservation property, which holds.

**ONE RE-MEASUREMENT THAT CHANGES ROUTING ALREADY SENT:** the class-B write-guarded population is **25 at this HEAD**, not b23's 22. The three b23 missed: `:5062` `grd_progress_photos`, `:5935` `scp_progress_photos`, `:11241` `rf_schedule`.

## OPEN, AND WHY

* **Item 3 PARKED at a one-line blocker.** The harness is written and targets `alf_op_audits` write (Tier A, the `23514`) and `mech_site_assets` read (the `42703`) against a tempdir copy, with a control and a counterfactual. **All four sections returned `COULD NOT RUN: SD_AUTH_SECRET not set`, so nothing was observed.** Fix: stub `process.env.SD_AUTH_SECRET` before `_lib/auth` is required — the pattern is `api/auth-license-app-scope.test.js:158-176`.
* **Items 4 and 5 NOT STARTED, nothing half-checked.** None of the six open findings is recorded as confirmed or cleared; **(d) LATE_REPLAY is still undriven**; the predicate-span rule is in no standing document; **CALLER is still a lower bound** on the 33 server-only GETs.
* **Two FRESH Tier A obligations against me, untouched:** `cody 2026-10-15T12:18:41Z` (quotes, sd_hr_certs, sd_hr_employees, sdn_projects — **person data**) and `hank 2026-10-15T12:24:35Z` (leg_custodylog, **sen_visits**, where b23's payroll F1 lives).
* **hank:** b23 F1 **first** — Michael has decided it is a bug — then F3, F4, the 25 branches. **cc:** `tier_a_review_gate.py` has **no `--amend`**, so hank's reviewed carve-out has nowhere in the register to land; and wire **one** anchor-rot tool into a gate. **cody:** re-anchor the probe and arm the anchor itself.
* **Held at Michael's instruction and not acted on:** the EVV-readiness raw-clock question and the one-person-agency self-approval question.

## METHOD NOTE

b23 routed **22** class-B write branches; the same predicate finds **25** here, and three were never listed. b23's clause was *"say which identifier"*; b24's was to be *"say where the predicate looks"*. **The third clause is now forced: say WHICH SHA it was measured at.** A count is a property of a predicate *applied to a tree at a moment* — and a routing list carried across three batches is short by three because nobody wrote the sha down. **The rule is in no standing document yet** (that is item 5, explicitly not done), which is the same shape as the `sf_events` prose rule that went quiet for a day in b22.

*Full detail: `SAIRN-report-fourth-b24.txt`, `SAIRN-handoff-fourth-b24.md`. Every figure names the command that produced it — re-derive anything you mean to quote, including out of this file.*
