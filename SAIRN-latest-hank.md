# hank — latest (b16, 2026-10-15)

**LANDED.** HEAD == origin/main `15cf623d` at the moment of the check, 0/0,
**NOT forced**, **no override form used** — not `SAIRN_SEED_GATE=off`, not
`SAIRN_GATE_EXEMPT=seed`, not `SAIRN_SKIP`. Two gate refusals (register-feed,
then tier-a + derived-docs together), **two satisfied, zero overridden**.
**275 api/ suites run individually, 272 exit 0** — the 3 remaining are
registered known-reds that were red before this batch. Live probe:
**verified=6 fail=0 could-not-run=6**, the six named *and counted*.

**HEAD was `253817a4` at session start, not the `11ffb660` the dispatch
expected** — a merge of `origin/main` on top of b15's tip, made after b15
closed. Reported, not reconciled.

## What changed

* **PAID PERIODS ARE FROZEN** (Michael's decision). A clock correction
  approved after a pay run no longer rewrites a closed total; it posts as an
  **adjustment line** in the period containing the approval. The time lives in
  `api/_lib/sen-evv-clock.js`'s new `effectiveClockAsOf(row, field, asOfISO)` —
  one function decides what "approved" means — and `api/_lib/sen-payroll.js`
  takes an optional `closed_periods`. **Three states, not two:** an approval
  with no readable `approved_at_server` applies on the as-paid basis AND is
  counted in `undatable_corrections`; a closed period whose `paid_at` cannot be
  read **refuses the run**. `gross_cents` keeps its meaning;
  `adjustment_cents` and `total_payable_cents` are new and separate, because
  folding the adjustment in would recompute overtime on a frozen week.
* **The closed-period list comes from `sen_settings` and NEVER from the
  caller.** A caller who could declare a period open could restate a wage
  already paid. A **failed** read is `503 CLOSED_PERIODS_UNREADABLE`; a
  404/400 is an honest empty.
* **F2 — an EVV export and a pay run now read ONE clock.**
  `api/_lib/sen-evv-readiness.js` element 6 and the client's new
  `senEvvException()` both read the effective clock. **GPS deliberately did not
  move**, and the arm asserts both directions: 4 raw coordinate reads, 0 raw
  time reads. A correction supplies a time and never a location.
* **The `app_id` tenancy report was REFUTED and the assertion added.** cody's
  doc was driven, not trusted: the probe label was a *mutation* label. The
  suite is 8/0/0 both ways and the red evidence is the **ablation** — simplify
  `api/sd-data.js:2137` to a fixed app and the same request writes `app_id:
  'sairnvet'`. A **negative** ablation is kept too: the pre-gate at `:2016` has
  no behavioural arm and the structural check is its only guard.
* **The SD_LINEAGE/SD_HR id-shadow pick, mine to make, made:** the identifier
  **column** wins over a blob `id`. The other two options were rejected **by
  measurement** — all four id mints for those five resources already produce
  strings, so no `===` had to change.
* **The `slice(x, x + N)` gate b14 asked for.** Flags same-expression
  fixed-width source windows, deliberately not structure-bounded ones. It
  **does not fix the 31 that exist** and an arm asserts that it says so.
* **Three suites were DEAD, not failing, since b15** — `senEffClock` added to
  the page and not to their lift lists, so 191 arms died at ReferenceError and
  none of the three was in `known-red-suites.json`. Now 76/76, 83/83, 32/32.
  Two more **stale expectations** fixed on the module I changed.
* **One honesty fix in a log:** the `NO_ACTIVE_CHECK` warning claimed "the
  request was allowed on the token alone" on requests the gate then refuses
  403. cody's triage read that sentence as a live suite failure and routed it
  as one.

## What is open

* **The freeze is INERT.** There is no write path for
  `sen_settings.payroll_closed_periods` and I did not build one — "who may
  freeze a pay period" is a permissions decision. **Michael's call.**
* **The Tier A obligation covers SEVEN resources and is fourth's.**
  `docs/2026-10-15-hank-b16-to-fourth-tier-a.md`. The item I most want
  attacked: the undatable-approval direction, which is a counterfactual about
  pre-2026-10-14 history and could double-count if wrong.
* **H8, the one-person-agency self-approval exception, is still NOT built** and
  b16 makes the dead end sharper — pay and the EVV check now agree the visit is
  stranded. `docs/2026-10-15-hank-b16-h8-self-approval.md`.
* **`SD_AUTH_SECRET_PREVIOUS` was not cleared and must not be.** The census row
  is still legacy.
* Full list, with the exact next step for each: `SAIRN-handoff-hank-b16.md`.

## Compaction, since it was asked

**The premise does not reproduce: hank has never compacted.** 38 sessions, zero
boundary rows and **zero context drops >30%** — the drop test being the one
that does not depend on the marker existing. Sessions climb to ~960,000 tokens
and **end**. The winning source is `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=97` in the
user settings `env` block; nothing else is set anywhere, and the launch command
carries no flags. **Verdict: flooding, by my own output** — ~1.9× the entire
tool-result volume — not by tool results. Numbers under EVIDENCE in
`SAIRN-digest-hank-b16.txt`.
