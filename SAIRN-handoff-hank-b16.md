# Hank handoff — 2026-10-15, batch b16

**Written BEFORE the report, at a point where nothing is half-edited.** All six
dispatched items were worked; four are complete, and the two that are not are
named below with what was done and what was not. Everything is pushed.

---

## Push state — verified, not asserted

    git fetch origin
    git rev-parse --short HEAD        -> 15cf623d
    git rev-parse --short origin/main -> 15cf623d
    git rev-list --left-right --count HEAD...origin/main  -> 0  0

**`15cf623d` IS THE TIP BEFORE THESE ARTEFACTS, and that is not a slip.** The
handoff, report and digest land ON TOP of it, so the tip moves after this line
is written and any sha quoted here is one or two commits behind by the time it
is read. The report's SHA256 seals its own bytes and cannot be restamped to
chase the tip. **Re-derive rather than trusting any sha in these three files:**

    git -C C:/Users/marsh/Documents/SAIRN-hank rev-parse --short origin/main

**NOT forced.** No `--force`, no `--force-with-lease`, no `--amend` on anything
already pushed. **NO OVERRIDE FORM USED** — not `SAIRN_SEED_GATE=off`, not
`SAIRN_GATE_EXEMPT=seed`, not `SAIRN_SKIP`. **Two gate refusals, two satisfied,
zero overridden:** register-feed (five records) and a combined refusal carrying
tier-a (an obligation over seven resources) + derived-docs (MASTER-PLAN and
traceability-matrix regenerated, never hand-merged).

**THE DISPATCH SAID HEAD SHOULD BE `11ffb660` AND IT WAS NOT.** At session start
HEAD was **`253817a4`** — a merge commit of `origin/main` on top of b15's
`11ffb660`, made after b15 closed. `11ffb660` is still reachable and is b15's
real tip. Nothing was done about it; it is reported rather than reconciled.

**The b16 commits on `origin/main`** (shas are post-rebase and were re-derived
after the last one):

    9a70365b  fix(sairnsenior,sd-data): paid periods are FROZEN -- a later approval is paid forward
    883ad0bc  fix(sairnsenior): F2 -- the EVV checks read the SAME effective clock pay uses
    aac69e6a  test(api): three b15-broken fixtures repaired, and the slice(x, x+N) gate
    92cd40b5  docs(hank b16): the Tier A routing to fourth, the H8 record, the evidence
    233753ee  chore(defect register): five records for b16
    3e935a3f  chore(scrutiny): the ledger rows the b16 push gate wrote
    8ba4e744  chore(defect register): re-seat the five b16 shas after the rebase
    85eb71ab  chore(tier-a,derived): the b16 review obligation and the regenerated documents
    8edab1e1  chore(derived): re-seat the derived documents and cited shas after rebase 1
    15cf623d  chore(scrutiny): the ledger rows the SUCCESSFUL b16 push wrote

---

## Item 1 — COMPACTION DIAGNOSIS: DONE, and the premise does not reproduce

Full numbers are under EVIDENCE in the digest. The short form:

**Nothing in hank's history compacts at all.** 38 transcript sessions, **zero**
`compact_boundary` rows and **zero** context drops greater than 30% — and the
drop test is independent of whether this version writes a boundary marker.
Sessions reach **~960,000 tokens** of context and then **end**.

**The winning source is `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=97`**, set in the
`env` block of `C:\Users\marsh\.claude\settings.json`. On a 1M window that is a
threshold of ~970,000 tokens, and sessions top out just under it.

**Verdict: FLOODING, and by MY OWN OUTPUT rather than by tool results.** b15's
session: 807 minutes, context 58,522 → 749,376, growth 856 tok/min. **My own
output tokens: 593,659. All tool results together: 1,279,597 chars ≈ 319,899
tokens.** So my output is roughly **1.9× the entire tool-result volume** and is
the dominant consumer. **The two figures are NOT a percentage split of the
690,854 token growth and are not presented as one** — they sum to more than it,
because cached prefixes and re-sent content make per-source attribution
approximate. What the ratio supports is which of the two is bigger, and that is
the only claim made. The five largest tool results were 65KB, 27KB, 26KB, 24KB
and 23KB — not the problem.

**Capped in this batch**, and it partly worked: test output went to logs, greps
carried head limits, no long chat prose, and the report and digest were written
to files rather than printed. **The five largest tool results dropped from 65KB
to 21KB.** My own output did not drop as a rate — this session ran 3,957
tok/min against b15's 735 — because the work was denser, not because the cap
failed; the session is at **38.7%** of the window after 80 minutes.

Not threshold-too-low (97% is nearly the ceiling) and not
window-smaller-than-assumed (the window really is 1M and sessions reach 96% of
it).

## Item 2 — PAID PERIODS ARE FROZEN, and F2: DONE

**The freeze.** `api/_lib/sen-evv-clock.js` gained
`effectiveClockAsOf(row, field, asOfISO)`; `effectiveClock` is now that
function with `asOf = null`, so every existing caller is unchanged.
`api/_lib/sen-payroll.js` gained an optional `closed_periods` input. A closed
period recomputes to its **as-paid basis**; an open period posts an
**adjustment line** for any visit in a closed period whose approval landed
after `paid_at`, **in the period containing the approval** — which is what stops
it posting forever. `api/sd-data.js` reads the list from `sen_settings`
(`payroll_closed_periods`) and **never from the payload**: a caller who could
declare a period open could restate a wage already paid.

**Three states, not two.** An approval with no readable `approved_at_server`
**cannot be dated**: it applies on the as-paid basis AND is counted in
`undatable_corrections`. A closed period whose `paid_at` itself cannot be read
**REFUSES the run** (`UNDATED_CLOSED_PERIOD`).

`api/b16-paid-period-freeze.test.js` — **RED 3 passed / 6 failed / 1 unproven**
(`docs/hank-evidence/b16/red_freeze.log`) → **GREEN 17/0/0**. F8/F16 are the
controls green both ways. F10 is the ablation. F17 answers one of fourth's three
questions with 15 hostile row shapes rather than forwarding it.

**F2.** `api/_lib/sen-evv-readiness.js` element 6 and `sairnsenior.html`'s new
`senEvvException()` now read the same effective clock pay uses. **GPS
deliberately did not move** and arm E5 asserts both directions.
`api/b16-evv-pay-agreement.test.js` — **RED 2/6/1 → GREEN 9/0/0**.

**The one-person-agency self-approval exception is NOT BUILT**, per Michael, and
is recorded for **H8** in `docs/2026-10-15-hank-b16-h8-self-approval.md` with
the dead end stated exactly and two constraints any future design must satisfy.

## Item 3 — the tenancy question and the three api/ suites: DONE

**The tenancy question is REFUTED and the assertion is added.** cody's
`docs/2026-10-15-cody-b16-app-id-tenancy.md` was driven, not trusted.
`api/b16-app-id-tenancy.test.js` — **8/0/0, and 8/0/0 at the pre-change tree
too, because the code was already correct.** The red evidence is the
**ablation**: T6 simplifies `api/sd-data.js:2137` to a fixed app and the same
request returns **200 with `app_id: 'sairnvet'`** — the cross-app write cody
predicted. T7 is a NEGATIVE ablation kept rather than dropped: the pre-gate at
`:2016` has **no behavioural arm**, so T5's structural check is its only guard.

**Of cody's three failing suites, two were already green** —
`sd-data-leg-session-gate` 20/0 and `sd-data-memory-app-scope` 0 failures — and
that is reported rather than claimed as fixed.

**The third had a different failure than the one routed.** The routed line,
`active-credential re-check DID NOT RUN`, is a **console warning**, not the
failure; the real failure was a **stale paralegal expectation** written in
2026-09-16 and answered the other way by `api/_lib/law-roles.js:87` on
2026-10-12 (paralegal `''`, hard-locked). Corrected to assert the DENY, paired
with a control that the same paralegal token CAN read `law_optx`, plus an arm
requiring the table and the endpoint to agree. **And the log that caused the
misread was fixed**: it claimed "the request was allowed on the token alone" on
requests the branch gate then refuses 403. **12/13 RED → 13/13 GREEN.**

## Item 4 — the id-shadow pick and the slice check: DONE

**PICKED: the read stops letting the blob win.** `Object.assign({}, x.data,
{ id: x[cfg.idCol] })` on both SD_LINEAGE and SD_HR, so the server's identifier
**column** wins. The other two options were **rejected by measurement, not
argument** — the full reasoning is in `api/b16-id-shadow.test.js`'s header, and
arm I6 measures all four id mints in `stonedesk.html`/`stonedesk-hr.html` as
strings, which is why no `===` had to change. **RED 2/3/1 → GREEN 6/0/0.**

**The slice gate is built.** `api/b16-slice-window-check.test.js` flags
`.slice(V, V + N)` where the same expression appears on both sides and N ≥ 2,
and deliberately does **not** flag structure-bounded windows. Failing-first
**driven**: a planted window made it exit 1 on S1, "32 found, 31 in the
baseline". **IT DOES NOT FIX THE 31 THAT EXIST** and arm S6 asserts that it
says so.

## Item 5 — the Tier A routing: DONE

`docs/2026-10-15-hank-b16-to-fourth-tier-a.md`. Two of the three questions are
now **BUILT rather than asked**, so the review is **wider** than it was: five
named things to attack on the freeze, three on the EVV change, the throw
question **answered** with arm F17, and the purity question still open and now
in **two** files.

**The gate opened a new obligation covering SEVEN resources** — `law_optx`,
`law_trusttx`, `sd_hr_certs`, `sd_hr_employees`, `sen_pay_rates`,
`sen_settings`, `sen_visits` — and it was right to: b15's obligation named two,
and an obligation covers the resources it names. **Assigned to fourth.**

## Item 6 — push, live verification, artefacts: DONE

Push state above. **LIVE VERIFICATION RAN THIS TIME** (b15 had none):
`docs/hank-evidence/b16_live_gate_probe.py` → **6 verified, 0 failed, 6 could
not run**, `docs/hank-evidence/b16/live_probe.log`. The six verified legs are
the client half of F2 on the real deployed page, including that the OLD
duplicated condition is **absent**. **The six could-not-run legs include the
freeze**, which is the largest change in the batch and has **no live
verification at all**.

---

## Tests — the whole api/ tree, not a selection

`docs/hank-evidence/b16/all_api_suites.log` — **275 suites run individually,
272 exit 0.** The sweep found **7** reds; four were fixed in this batch and
**3 remain**: `sd-data-customer-soft-delete`, `sd-data-family-contacts`,
`sd-data-scp-licence-only` — all three registered in
`docs/known-red-suites.json`, all three red **before** b16, and **none
root-caused here**.

Guardian: **Check 0a** `python tools/checkblocks.py sairnsenior.html` → 3
blocks, 0 failed, plus `node --check` on all 14 changed JS files. **Check 31**
both tools clean. `docs/hank-evidence/b16/guardian_checks.log`.

---

## Open, with the exact next step

1. **THE 31 FIXED-WIDTH SOURCE WINDOWS ARE TOLERATED, NOT FIXED.** The gate
   stops new ones; every one of the 31 can still produce b14's false red.
   **Next step: convert them to structure-bounded windows, 12 files, and
   delete the matching BASELINE entry as each one goes — arm S2 fails if a
   baseline entry no longer exists, which is the good direction.**

2. **THERE IS NO CHECK THAT A FUNCTION LIFTED FROM `sairnsenior.html` HAS ITS
   CALLEES LIFTED WITH IT.** This batch found three suites dead since b15 for
   exactly that reason (191 arms), fixed them by hand, and **added
   `senEvvException`, which depends on `senEffClock`** — so the same break is
   available to the next suite that lifts it. Recorded in the defect register
   as `action_status: planned`, not done. **Next step: a check in `api/` that
   parses each `fn('<name>')` lift list and fails when a lifted function calls
   a page-level function not in the list.**

3. **THE TIER A OBLIGATION IS OPEN**, seven resources, **assigned to fourth**.
   **Next step: fourth discharges**, using
   `docs/2026-10-15-hank-b16-to-fourth-tier-a.md`. The item I most want
   attacked: **the three-state handling of an approval with no
   `approved_at_server`** — it applies on the as-paid basis, and my reasoning
   for that direction is a counterfactual about pre-2026-10-14 history. If it is
   wrong the same entry can be double-counted.

4. **THE FREEZE HAS NEVER RUN AGAINST REAL DATA.** No agency has a
   `payroll_closed_periods` row in `sen_settings`, so there are no closed
   periods anywhere and the mechanism is inert in production. **Next step:
   Michael decides whether an agency should be able to CLOSE a period from the
   UI at all — there is no write path for `payroll_closed_periods` and I did
   not build one, because "who may freeze a pay period" is a permissions
   decision, not a handler detail.**

5. **THE ADJUSTMENT IS A FLOOR, NOT A TOTAL**, and **a period never run never
   pays its adjustments.** Both are in `not_computed` in the output, neither is
   computed. **Next step: the overtime half needs fourth's answer on whether a
   floor is acceptable; the unposted-adjustment half needs a sweep that nothing
   currently has.**

6. **ONE EVV/PAY DISAGREEMENT REMAINS, DELIBERATELY** — a frozen period pays as
   at `paid_at` while an EVV export reads now. Arm E8 pins it and requires
   `period_closed` to name the instant. **Next step: fourth decides whether a
   deliberate disagreement is acceptable when the export is federally
   mandated.**

7. **A CORRECTED CLOCK-OUT WITH NO GPS NOW SURFACES AS A GPS EXCEPTION** rather
   than a time-span one. A visible change to what a surveyor is shown. I believe
   it is correct — the visit really has no clock-out coordinate — and **nobody
   else has reviewed it.** **Next step: it is in the fourth routing doc as EVV
   question 1.**

8. **THE ONE-PERSON-AGENCY SELF-APPROVAL EXCEPTION IS STILL HELD FOR MICHAEL**
   and was not built. **Next step: Michael, via H8. If granted it must be a
   licence-level setting with an audit trail AND must carry an
   `approved_at_server`**, or the freeze is unverifiable for exactly the
   agencies using it.

9. **THE CENSUS ROW IS STILL LEGACY.** `legacy_rows = 1` on `sc_credentials`.
   **`SD_AUTH_SECRET_PREVIOUS` WAS NOT CLEARED AND MUST NOT BE** — instructed
   this batch and obeyed; nothing touched it. **Next step: Michael runs the step
   in `SAIRN-backfill-stedi-step.txt`, then census PART 1.**

10. **THREE api/ SUITES ARE STILL RED** and none was root-caused here:
    `sd-data-customer-soft-delete`, `sd-data-family-contacts`,
    `sd-data-scp-licence-only`. All three are in `docs/known-red-suites.json`.
    **Next step: read each one's failing arm; b16's four repairs were all stale
    expectations or broken fixtures, so these three are worth the same look
    before assuming they are real defects.**

11. **FMEA DRAFTS ARE OWED**, and the register's own loop said so during this
    batch: `NO DRAFT` for `api/b16-id-shadow.test.js`,
    `api/b16-paid-period-freeze.test.js`,
    `api/sd-data-law-trusttx-session.test.js`,
    `api/_lib/sen-evv-readiness.js` and `api/b16-evv-pay-agreement.test.js`, and
    **`MISSED` for `sairnsenior.html`** — one draft predates it and none cites
    rule 1.1. `tools/fmea_draft.py` is **cc's**.

12. **api/ SUITES ARE OWED GATE-DRIVER WIRING, AND THE COUNT IS NOT WRITTEN
    HERE ON PURPOSE** — b15's handoff said ten and b16 adds five
    (`b16-paid-period-freeze`, `b16-evv-pay-agreement`, `b16-app-id-tenancy`,
    `b16-id-shadow`, `b16-slice-window-check`), and a number in a handoff is
    the thing that goes stale. **Derive it** rather than quoting it. Measured
    now: `grep -rlE "b1[2-6]-(payroll|client|corrections|clock|paid-period|evv-pay|app-id|id-shadow|slice)" tools/`
    returns **nothing**, so no gate driver references any of them. (A bare
    `grep -rl "b1[2-6]-"` hits `tools/citation_anchor_rot_check.py`, which
    matches the pattern and is not a driver — the narrower grep is the one to
    use.) **`tools/` is cc's.**

13. **THE EXTRA-SCRUTINY LEDGER FLAGGED ONE WEAKENING SHAPE AND IT IS A FALSE
    POSITIVE**: `const sk = (out.adjustments_skipped || [])[0];` in
    `api/b16-paid-period-freeze.test.js`. `adjustments_skipped` is the output
    field that reports an adjustment which could NOT be computed, and arm F12
    exists to require a reason there rather than a 0-cent line. **Recorded in
    `docs/scrutiny-flags.json` under three commits so a reviewer can
    disagree.** **Next step: nothing from me; a reviewer's call.**

14. **THE SEAM CHECK SAID COULD-NOT-TELL** for at least one endpoint/engine
    pair during both pushes. The push is allowed and nothing was verified about
    that seam. **Next step: `python tools/sairn_seam_check.py`, which I did not
    run.**

---

## Claims held

**`hank`**, claimed as the **first action** of this batch with a declared file
set, and **STILL HELD** — I did not release it, because open items 1, 2 and 10
are unstarted work inside the same claim and releasing would advertise them as
free. **A SECOND `hank` CLAIM FROM b15 IS ALSO STILL ACTIVE** and the tool said
so at claim time; I did not release it either, because `release hank` would
have dropped one of the two and the tool does not say which. **Next session:
run `python tools/sairn_claim.py list` and release BOTH explicitly.**

    python tools/sairn_claim.py release hank

**Conflicts respected:**

* **`tests/` is cody's.** `tests/sairnlegacy_fault_probe.py` was **not touched
  at all** — the tenancy assertion went into `api/`, which is mine.
  `tests/sen_evv_payroll_wiring_probe.py` was **run, never edited**.
* **`tools/` is cc's** — every tool was **run**, none edited.
* **`docs/` triage and routing docs are cody's and fourth's** —
  `docs/2026-10-15-cody-b16-app-id-tenancy.md` and
  `docs/2026-10-15-cody-b15-fulltree-triage.md` were **read, not edited**.
* **No auditor clone was entered.**

Files written outside `api/` and the app HTML: the `docs/` files **the push gate
itself requires** (`defect-density-register.json`, `MASTER-PLAN.md`,
`traceability-matrix.md`, `tier-a-reviews.json`, `scrutiny-flags.json`), my own
two `docs/2026-10-15-hank-b16-*.md`, `docs/hank-evidence/b16/` and
`docs/hank-evidence/b16_live_gate_probe.py`.

---

## Stashes and settings — checked, not assumed

    git stash list
    stash@{0}  On main: b10-settings-park
    stash@{1}  On main: my 3 register records, re-addable from scratchpad/reg_add.py

**Neither was popped, dropped or inspected beyond `git stash list`.** No `git
stash` command of any kind was run. `.claude/settings.json` was **never
committed**; `.claude/settings.json.bak` and `.claude/settings.json.hooks.bak`
remain untracked and were left alone. **No hook was restored or added.**

---

## Transcript

    C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-hank\85b41c8d-a1a9-4e89-95ec-0ac9acb8b11a\

Scratch artefacts there, not committed. Worth keeping:
`scratchpad/reg_b16.py` (the five register records) and
`scratchpad/pushloop.sh` (the fetch/rebase/push loop — it re-derives only the
two generated documents plus the sha re-seats, and **bails on any other dirty
path** rather than resolving a conflict in a loop).

**The detached worktree the pre-change counterfactuals were captured in is
REMOVED:** `wt-b16` deleted with `git worktree remove --force`, and
`git worktree list` shows **none** under this session's scratchpad. Fifteen
other detached worktrees under `AppData\Local\Temp` belong to other tools and
were left alone.
