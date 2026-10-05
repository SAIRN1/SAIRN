# CC batch, 2026-10-05 — status of the last queue, the revoked-licence ablation, and the inventory

**Pulled to `c0e97678` at the start; every verdict below is a thing driven, run,
or read at HEAD today. Where something is a quote from an earlier document it
says so and says the document was not re-derived.**

Methodology note for this whole batch: **every screen reports its blind-spot
count on its own last line.** A verification with no stated blind spots is
claiming completeness it has not earned, and that claim is the thing this
platform keeps paying for.

---

## 1. The last queue, item by item

| Item | State | Evidence |
|---|---|---|
| SAIRNbiz preview check — load state + full click-through | **LANDED before today**, `25814d55` (second pass) over the base doc | `docs/2026-09-29-sairnbiz-preview-check.md`, 646 lines. NOT re-run today and not claimed re-run |
| …its credential half | **WRONG AND NOW FIXED**, `8e205448` | See §2 — the doc blamed the licence; the dead thing was the PIN |
| Revoked-licence AI cutoff | **LANDED** `453193f3`, closed as DECIDED in `0bf0a376` | Re-confirmed and ablated today — see §3 |
| `mech_docs` gate (write reachable on a licence key alone) | **LANDED and LIVE-VERIFIED 403** | `api/sd-data.js:1186` carries `mech_docs: ['write']`; `docs/2026-09-29-mech-docs-gate-live-verification.md` |
| `mech_docs` register cell | **LANDED TODAY** `5ab3bcb5` | Was still the withdrawn "no PII / not individually read" boilerplate at HEAD this morning |
| `msb_bottle_scans` register cell | **LANDED TODAY** `5ab3bcb5` | The 2026-09-23 read missed that `note` carries a computed dollar figure |
| Stale-branch tips | **RECORD LANDED TODAY** `495eef8a`, then 3 deleted | See §4. The instruction's "19" does not reconcile to any set |
| Competitive-gap doc inventory | **LANDED before today** | `docs/2026-09-29-competitive-gap-doc-inventory.md`; one ref in its scope was deleted today and it is annotated rather than left to drift |
| SAIRNbiz finding 13 (records stranded by the sync latch) | **OPEN, NOT FIXED** | Registered `1977d133`, open-work row `0929a535`. Still the only thing keeping the preview check NOT CLEAN |

**BLIND SPOTS: 1.** This table is assembled from this clone's git log and the
shared registry; work another clone did and has not pushed is invisible to it,
and an empty claim record is indistinguishable from one nobody wrote to.

---

## 2. SAIRNbiz credentials — the answer, driven

**`SB-PINNACLE-2026` / `sairn-demo-owner` / `84350271` → 200, owner, token.
USE THAT.** No SQL needed.

All four combinations, one run, against the real `POST /api/sb-auth`:

```
SB-PINNACLE-2026  /  sairn-demo-owner  /  84350271  ->  200  owner, token issued
SB-PINNACLE-2026  /  sairn-demo-owner  /  60417293  ->  401  INVALID_CREDENTIALS
SB-TEST-2026      /  sairn-demo-owner  /  84350271  ->  200  owner, token issued
SB-TEST-2026      /  sairn-demo-owner  /  60417293  ->  401  INVALID_CREDENTIALS
```

**The PIN is the discriminator, not the key.** `60417293` is dead on both
licences; `84350271` works on both. The two had only ever been driven as matched
pairs, so a dead PIN and a dead key were indistinguishable and the key took the
blame for six days.

**And `SB-TEST-2026` is a DIFFERENT TENANT, not "the same demo company" as the
old advice said** — the tokens carry `license_hash` `05c4e1e1…` and `87e7f2ee…`.
Following that advice would have put an evening of client and employee entry
into the wrong company.

`bootstrap` is **409 `ALREADY_PROVISIONED`** on both, re-driven, so there is
still no self-serve route to a fresh Owner. The 409 is real; the inference that
the licence was closed never followed from it.

**BLIND SPOTS: 3.** (1) The click-through is NOT re-run — the last full one is
the 2026-09-30 second pass, and finding 13 is still open. (2) Only
`sairn-demo-owner` was driven on these two keys. (3) The other fourteen rows of
`docs/2026-09-03-demo-credentials.md` share the one-PIN-per-key structure that
produced this mis-attribution and were not re-driven.

---

## 3. The revoked-licence AI cutoff — present, held, ablated, and HALF DORMANT IN PRODUCTION

### It is at HEAD and the suite is green

`api/claude-licence-enforce.test.js`: **12 passed, 0 failed.** `node --check`
clean on `api/claude.js`.

### Ablated, per ARM and not per exit code

Discipline 12: remove ONE named layer from already-clean code and measure what
that layer alone catches. Both mutants were confirmed to **parse** before being
run, because a syntax-error mutant scores as CAUGHT for the wrong reason.

| Layer removed | Arms that go red | Arms that stay green |
|---|---|---|
| The refusal — `api/claude.js:352`, `enforce && authState === 'inactive'` → 403 | **A1, A2** (2 of 12) | 10, including every control |
| The budget grouping — restoring `authState === 'valid' \|\| authState === 'inactive'` at `:470` | **C1** (1 of 12) | C2, C3, C4 — the three controls that make C1 mean something |

Each layer is held by arms that are **specific to it**: removing the refusal does
not move C1, and restoring the budget grouping does not move A1/A2. That is the
result that makes the suite worth trusting, not the 12/12.

`api/claude.js` restored byte-for-byte after each run; `git diff` empty.

### THE HALF THAT IS NOT LIVE, measured today rather than quoted

**`SAIRN_CLAUDE_AUTH_MODE` does not exist on the Vercel project at all.** Read
from the Vercel API against `prj_bj475nKLxC1TTmpFU6j7HVCSMEhn`, all targets,
`hiddenProductionEnvCount: 0` — so there is no chance it is set and unreadable.
`api/claude.js:288` defaults to `observe`. Therefore:

* **The budget half IS LIVE.** It is mode-independent. A revoked tenant draws on
  `anon:<app_id>`, not the licensed app's paying pool. That was the half that was
  costing real money and it is fixed in production.
* **The refusal half is DORMANT.** In `observe` mode a revoked licence is still
  **served AI**. The 403 exists, is correct, is tested, and never fires.

**This is not a new finding and is not a defect in the fix** —
`api/claude-licence-enforce.test.js:29` says "THE REFUSAL is LATENT",
`docs/2026-09-13-ai-red-teaming-scoping.md:109` says the mode is still `observe`
in production, and `docs/2026-09-05-claude-proxy-auth-rollout.md:167` makes the
flip Phase 4 of a deliberate rollout. What is new is that it is now **measured
at the platform** instead of inferred from a default in the source.

**The decision is Michael's and it is one env var.** Setting
`SAIRN_CLAUDE_AUTH_MODE=enforce` turns on the refusal — and also the
absent/invalid refusal at `:325`, which is the larger blast radius and the
reason Phase 4 was never a rider.

**BLIND SPOTS: 2.** (1) Nothing was driven against the deployed endpoint — a
revoked licence key to test with was not available, so "live" here means the code
is on `main` and the env state is read from Vercel, not that a revoked call was
made and observed. (2) The ablation covers the two layers this fix added; the
`absent`/`invalid` refusal at `:325` was not ablated.

---

## 4. Branches — 27 recorded, 3 deleted, and the "19" does not exist

Full account in `docs/2026-09-29-stale-branch-tips.md`, addendum. Record pushed
at `495eef8a` **before** any deletion.

**There is no set of 19.** 27 remote branches besides `main`: 15 `regfresh/*`
left by the first pass plus 12 that pass never looked at. 19 is neither half nor
their sum, under ancestry, content, age, or name.

Deleted — all three satisfy **ancestor of `main` AND zero unique commits AND
zero-file diff**, a stricter test than the first pass could apply:
`claude/cloud-research-competitive-vet-law`,
`claude/stonedesk-div-balance-dedup-6mju2o`,
`worktree-stonedesk-chamfered-corners`. All three tips confirmed still
resolvable afterwards, one `git cat-file` at a time.

**Four of the 24 kept are kept for reasons beyond the test**, named in the file so
a later sweep does not take them: `claude/wizardly-ride-wtun13` is **open PR
#18** with 15 unique commits; the two `regfresh/2026-09-28` branches hold the
`sv_mobilevet` and `sen_settings` repoints a conflict resolution set aside; and
`master` is left because `tools/git_push_master_guard.py` exists to refuse pushes
to it.

**BLIND SPOTS: 3.** (1) The tests prove nothing is lost *relative to `main`* — an
abandoned branch and a landed one look identical. (2) "Has unique content" is not
"is wanted". (3) Tips survive only until some future `git gc --prune`, and
nothing watches that.

---

## 5. Who holds `api/sd-data.js`

**NOBODY.** `python tools/sairn_claim.py list` → *"No active claims"*, confirmed
after a fetch, three times across this session.

**And that sentence is worth exactly as much as the claim record is fresh** — the
dispatch hook's own words: *"NO ACTIVE CLAIMS. That is indistinguishable from a
claim record nobody pushed, so it is not evidence nobody is working."* The shared
registry agrees: all six sessions read `idle` / `DEAD`, newest row
2026-09-30T16:59.

**So three things that were blocked on that file are actionable now, and are
logged rather than taken** (this batch is inventory, not fixes):

| Was blocked on | State at HEAD today |
|---|---|
| `mech_docs` write not session-gated | **GONE — fixed and live-verified.** `api/sd-data.js:1186` |
| `c8b5e5b1`'s credential pre-gate turning suites red | **STILL RED.** `tests/sairnbuild_retainage_race.js` = **1 passed, 2 failed** at HEAD, driven today |
| The tombstones paired-negative FLOOR (`reads.length >= 3` against six occurrences) | **NOT re-measured today.** Named as unverified rather than carried forward as true |

**Two other things I was blocked on have cleared themselves and are closed here
rather than left in the index:**

* **`tools/conflict_marker_preflight.py` is pushed AND WIRED.** It is on `main`
  and `.claude/settings.json:95` calls `conflict_marker_preflight_hook.py`. The
  blocker was fourth's 13 unpushed commits; they landed.
* **`tools/mutation_anchor_check.py` no longer sits in COULD-NOT-RUN.** Exit
  **0**, **527 anchors checked, 0 could-not-read**, run today. It was exit 2 with
  unresolvable arms on 2026-09-28. Its own stated limit stands and it prints it:
  a unique anchor that drifted onto *different* code is still invisible to it.

**Two more measured at HEAD today, and recorded here because I had first written
them off as unmeasured when the run had actually finished in the background:**

* `tests/run_report_only_checks_probe.py` — **arm E2 still FAIL** (*"every entry
  records when and why it was promoted"*), 78 checks, 1 failed. Same cause as
  2026-09-28: four report-only tools carry no `evidence` field, and writing
  evidence for tools I did not promote would be inventing a real-run record.
* `tools/sairn_seam_check.py` — **96 clean, 0 not-forwarded, 19 COULD-NOT-TELL**,
  and the tool says *"COULD NOT TELL IS NOT A PASS"* in its own output. **That is
  19, up from 18 on 2026-09-28** — the count moved with nothing watching it,
  which matters more than either number.

**A TIMEOUT IS NOT A RESULT, and I treated it as one.** The foreground command hit
its limit, was moved to the background, and completed; I had already written "not
re-measured" on the strength of the timeout. That is the §1.11 shape — a third
state folded into a verdict — committed inside the document reporting on it.

**BLIND SPOTS: 2.** (1) "Nobody holds it" is read from a record that is only as
fresh as the last push to it; a session working without claiming is invisible, and
this report cannot distinguish that from an idle platform. (2) The tombstones
paired-negative FLOOR was not re-measured at all — no run was started for it, so
unlike the two above it is genuinely unknown rather than belatedly known.

---

## 6. The inventory — ranked, and ranked twice

Two orderings, because they disagree and the disagreement is the useful part:
**platform severity** (what breaks or misleads) and **competitive exposure** (is
a competitor actually beating us here). A thing can be severe and competitively
irrelevant, and a thing can be competitively fatal and mechanically trivial.

### Ranked by platform severity

| # | Finding | Sev | Logged? |
|---|---|---|---|
| 1 | **SAIRNbiz finding 13 — a record entered while the backup latch was armed is stranded on that device forever.** `sbSyncCollection` diffs against the value immediately before that one save, so a change that already happened is never offered again. A full re-save of `sb_ap` left the server at 5 rows | **HIGH** | **YES** — register `1977d133`, index `0929a535`. Open, unfixed, and the only reason the preview check is NOT CLEAN |
| 2 | **`c8b5e5b1`'s credential pre-gate still has suites red, re-driven today.** `tests/sairncare/test-alf-mar.js` = **0 passed, 20 failed** — the MEDICATION ADMINISTRATION RECORD gate, zero of twenty. `tests/sairnbuild_retainage_race.js` = 1 passed, 2 failed. Twelve suites and 172 assertions when first bisected 2026-09-27; two re-confirmed at HEAD today | **HIGH** | **YES** — index row stands. Now unblocked (`api/sd-data.js` free) and deliberately NOT taken in an inventory pass |
| 3 | **The revoked-licence refusal is dormant in production** — `SAIRN_CLAUDE_AUTH_MODE` absent from Vercel, so a revoked licence still gets AI. The money half is live | **MODERATE** | **YES, now, with the measurement** — previously recorded as a default in source; now read at the platform. Flip is one env var and Michael's call |
| 4 | **`mech_takeoffs` and `mech_quotes` carry the same withdrawn "no PII, not individually read" sentence** that was just removed from `mech_docs`, and both now store redacted extracted text through the same gate. Out of today's two-finding scope | **MODERATE** | **NEW — logging now** |
| 5 | ~~**`tools/md_table_check.py` exits 2 while reporting 0 malformed over 820 rows.**~~ **&#10060; THIS CLAIM IS FALSE AND IS WITHDRAWN (2026-10-05, same day, by me). `md_table_check.py` EXITS 0, and `main()` has no path that returns 2 at all (`return 1 if (total or unseen) else 0`). I read the 2 off a COMPOUND Bash command, where the status belongs to the pipeline's last element rather than to the tool. Full withdrawal in `docs/SAIRN-OPEN-WORK-INDEX.md` row 73 and in commit `7ca1c7b9`; the half that WAS true -- a three-file default list -- is fixed and the list now covers six files.** A report-only checker permanently in COULD-NOT-RUN is the third state working as designed and nobody reading it — the exact shape §1.11 exists for | **LOW-MODERATE** | **NEW — logging now** |
| 6 | **`docs/2026-09-29-register-cells-hank.md` offers a pasteable `api/sd-data.js` fix that is already landed.** `MECH_SCANNED_TEXT` at `:14456` covers all three resources. Two of its citations have also drifted (`:14284` → `:14475`) | **LOW** | **NEW — logging now.** A prepared-text document with no freshness check is a stale plan dispatching finished work, discipline 10's own failure |

### Ranked by competitive exposure — and this ordering is almost the inverse

| # | Finding | Is a competitor actually beating us? |
|---|---|---|
| 1 | **Three apps have NO competitive-gap doc of any kind: `sairndesign`, `sairnlegacy`, `sairnscape`.** Not thin — nothing, on `main` or any branch, dedicated or shared | **UNKNOWN, AND THAT IS THE POINT.** For three products we cannot answer the question at all. Unknown exposure is worse than known-bad exposure because it cannot be priced |
| 2 | **Nine of the fourteen covered apps have their newest audit ONLY on an unmerged branch**, eight of them on PR #18 alone | **Yes, in effect.** The research exists and is invisible to anyone reading `main`. Same shape as the `regfresh/*` backlog: done, verified, parked |
| 3 | SAIRNbiz finding 13 | **Yes, and directly.** "Data you typed is on one device forever" is table stakes every competitor clears. It is the one finding on this page a prospect would discover themselves in a trial |
| 4 | The red SAIRNcare/SAIRNbuild suites | **No.** Internal verification surface. Real severity, zero competitive visibility — which is exactly why it has survived since 2026-09-27 |
| 5 | The dormant AI refusal | **No.** It costs us money on revoked tenants, not customers. Commercially ours to eat |
| 6 | The stale tier sentences and the stale prepared-text doc | **No.** Internal honesty debt, invisible outside |

**THE DISAGREEMENT IS THE FINDING.** The severity list is led by things only we
can see; the exposure list is led by **not knowing where we stand on three
products and having most of the answer parked on one branch**. Those two
competitive items were found by an inventory and have never been ranked against
engineering work, because nothing on this platform ranks them in the same table.
**That is now logged rather than argued.**

### Deliberately left, per the instruction

Items 5 and 6 of the severity list are logged and not fixed. Item 4 is logged
and not fixed because widening a register correction past the two cells asked
for is the scope growth this platform refuses.

**BLIND SPOTS: 4.** (1) The competitive-gap figures are quoted from the
2026-09-29 inventory, whose per-app table was **not** re-derived today, and which
never read any doc's CONTENTS — a file named after an app counts as covering it.
(2) "Is a competitor beating us" is a judgement, mine, with no market evidence
behind it in this document. (3) The severity ranking covers what this session
touched or tripped over; it is not a sweep. (4) The twelve-suites-red figure for
`c8b5e5b1` is from the 2026-09-27 bisect — **two** of the twelve were re-driven
today (`test-alf-mar.js` 0/20 and `sairnbuild_retainage_race.js` 1/2), so the
other ten are unverified at HEAD and are not claimed red.

---

## 7. What this batch did NOT do

* **No click-through of SAIRNbiz.** The credential half was driven; the panels
  were not clicked.
* **No fix to anything in §6.** Inventory only, per the instruction.
* **No live call with a revoked licence key.** §3's "live" is code-on-main plus
  a platform env read.
* **No re-derivation of the competitive-gap per-app table.**
* **No deletion of any branch carrying unique content**, including `master`.

**BLIND SPOTS: 1.** This list is what I know I did not do. The class it cannot
cover is what I did not think to check — which is what the per-section blind-spot
counts above exist to narrow, and do not eliminate.
