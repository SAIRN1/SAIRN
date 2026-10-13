> **SUPERSEDED, AND THIS FILENAME IS WRONG.** It is dated 2026-10-16 and
> was written on **2026-10-13**. CLAUDE.md says to find the latest handoff
> **by the date in the filename**, so a date-sort puts this file above the
> real latest one and a session following the rule reads the stale document
> first. **Read `docs/handoff-fourth-2026-10-13b.md` instead** -- the push
> this file records as blocked has since LANDED (`c5af98dc..d30e9e42`, 48
> commits), so its section 2 and its items 4 and 5 are overtaken.
>
> NOT renamed, deliberately: a row in `docs/external-files-index.json` and
> the Drive delivery copy both carry this name, and a rename would turn two
> correct pointers into dead ones to fix one misleading sort.

# HANDOFF — fourth / ted, batch b9, 2026-10-13

**Written BEFORE the report**, at a point where nothing is half-finished: every
queue item is closed with evidence, partial with its denominator stated, or
named as not-triggered with the condition that would have triggered it.

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\26107814-6275-4923-8a05-52f5d7ac19bd\scratchpad\`
Derivations are scripts, not prose: `item2_repro.py` (+ `item2_repro.log`,
`item2_repro2.log`), `resolve_flags.py`, `resolve_reg.py`, `item6_withdrawn.py`,
`item6_tsv.py`, `item10_recover.py`, `item11_dups.py`, `drive_reds.py`
(+ `drive_red86.jsonl`), `counts9.py` (+ `counts9b.txt`), `push_b9.log`,
`push_b9b.log`, `item5_audit.log`, `tierA.log`.

---

## 0. THE CLAIM LINE, as item 1 required

**Taken as the FIRST action, before any edit**, which is what b8 did not do.

```
python tools/sairn_claim.py claim --no-push fourth "batch b9 -- FIRST ACTION is this claim, because b8 ran unclaimed ... FILES: docs/2026-10-12-fourth-b5-routing.md docs/2026-10-06-hank-routed-to-fourth.md docs/2026-10-13-ted-seq17a-owners.tsv docs/METHODOLOGY.md docs/2026-09-13-cross-domain-disciplines.md docs/known-red-suites.json docs/defect-density-register.json SAIRN-report-fourth-b9.txt SAIRN-digest-fourth-b9.txt docs/handoff-fourth-2026-10-16.md"
```

`check` returned **CLEAR**; the claim is **committed locally** and the push half
failed, so the tool printed `NOT CLAIMED`. **That half of its message is wrong on
this machine and the correction is measured:**
`~/SAIRN-SESSION-LOCKS/status/fourth.json` carries the claim — 1 claim, 10 files,
`2026-10-13T08:15:26Z` — so the other five sessions here can see it without a
fetch. Routed to cc (§3 below).

**Two files were edited outside the declared `FILES`** and are named rather than
absorbed: `docs/2026-10-13-fourth-routed-to-cody.md` and
`docs/2026-10-13-fourth-routed-to-cc.md`, both new routing documents under
`docs/`, which is mine by the directory rule. Nobody else declared them.

---

## 1. THE TWO THINGS THE NEXT SESSION MUST NOT "FIX"

1. **HOOKS STAY CLEARED.** `.claude/settings.json` is modified in the working
   tree and **must never be committed or restored**. Michael cleared them on
   purpose. It is also the direct cause of the push block in §2 — do not
   "solve" that by putting them back.
2. **`refs/salvage/b6-*`** — two refs pinning commits whose worktrees are gone.
   They are **still live** because the push did not land; item 4's bundle-then-
   delete is conditional on a landed push and **did not trigger**.

The three `.claude/settings.json.*.bak` files are also still in place for the
same reason: moving them was part of the same post-push item.

---

## 2. COMMITTED / PUSHED STATE

| | |
|---|---|
| HEAD | `35be6e97` |
| position | **28 ahead, 12 behind.** Nothing from b5–b9 is on `origin/main` |
| b9 commits | 3 — the claim, `988a1d8f` the work, `35be6e97` the register |
| diffstat of the work commit | `6 files changed, 739 insertions(+)` |
| `SAIRN_SEED_GATE=off` | **not used** — `docs/BYPASS-LOG.jsonl` gained no `fourth` row this batch |

### The push: ONE refusal diagnosed and FIXED, a second one standing

**ITEM 2 IS ANSWERED. The b8 refusal was a MISSING SHA, and it is measured:**

```
git cat-file -t 326f2894c0b7eeac04717a786721674a28a13119
  fatal: git cat-file: could not get object info      (exit 128)
git log ... 326f2894..94e608a4
  fatal: Invalid revision range                        (exit 128)
git fetch origin
git cat-file -t 326f2894...                            commit   (exit 0)
```

The left-hand sha is **the remote's current tip, handed to the pre-push hook on
stdin**. Five sessions push here, so the remote moves between a session's fetch
and its push, and the hook is then asked to read a range whose left side this
clone has never fetched. **The b8 range reproduces clean today** — `git log` exit
0, 20 records, 0 malformed — because a later fetch brought the sha in. So the
message was true and its implied cause was not.

**FIXED AS ITEM 2 DIRECTED: fetch, rebase, push once.** That push got **past**
this gate and was stopped by a different one:

```
Blocked: this push makes a GENERATED document stop matching what it is
derived from.
  docs/TOOLING-INVENTORY.md -- the generator REFUSES to run (exit 2)
        hook entries -- read from .claude\settings.json
```

**That is the hooks-off block, standing since b5, and it is the gate itself** —
so per item 2 the repro is written, it is routed to cc, and I stopped. No retry
loop: two push attempts in total, the second being the instructed one-push-after-
the-fix.

**ITEM 3 was run at the final HEAD both times** — `master_plan.py --check` and
`traceability_matrix.py --check` each **exit 0**. Nothing of mine made them
stale, so nothing was regenerated by hand. The rebase did conflict on both, and
the repo's own `tools/sairn_rebase_resolve.py` regenerated and staged them —
classified MERGE/GENERATED, not SOURCE.

### The rebase: three conflicts, none of them source

| file | class | resolution |
|---|---|---|
| `docs/scrutiny-flags.json` | append-only ledger | **UNION**, both sides' rows kept; 155 flags after, and both the `law-role-matrix` row and my two `6942098b` rows are present |
| `docs/defect-density-register.json` | mergeable ledger | `sairn_rebase_resolve.py`: 516 ancestor + 6 upstream-only + 0 local-only = **522** |
| `docs/MASTER-PLAN.md`, `docs/traceability-matrix.md` | generated | regenerated from the repo by the same tool |

---

## 3. ITEM BY ITEM, with the exact next step for each open one

| # | item | state | exact next step |
|---|---|---|---|
| 1 | claim first | **DONE** | nothing; the line is in §0 |
| 2 | diagnose the refusal | **DONE — missing sha, fixed; second gate routed** | cc decides the `TOOLING-INVENTORY` / hooks-off interaction |
| 3 | re-check the generated pair | **DONE — both exit 0** | nothing |
| 4 | post-push bundle/delete/move | **NOT TRIGGERED** | **do it the moment a push lands**: bundle `refs/salvage/b6-*`, verify, delete the refs, move the 3 `.bak` files to scratchpad |
| 5 | run the audit check | **DONE — EXIT 1, and the red is ambiguous** | **one `pg_constraint` read or one real insert** against Supabase; needs live credentials. hank's |
| 6 | classify 4 + owner TSV | **DONE — 23 of 23 sites verified, 36 rows** | the 36 findings themselves are open by design |
| 7 | route to cody | **DONE** | `docs/2026-10-13-fourth-routed-to-cody.md` |
| 8 | route to cc | **DONE** | `docs/2026-10-13-fourth-routed-to-cc.md`; §5 confirms the two b8 items are present |
| 9 | re-count conventions | **DONE — nothing to reconcile** | 34 headings, 1–34, no gap/dup; denominator agrees; no 35 appeared |
| 10 | re-drive every red suite | **PARTIAL — 21 of 86** | **re-run `drive_reds.py` over the 65 not yet driven**; the register records which |
| 11 | duplicate sweep | **DONE — 0 duplicates** | nothing |
| 12 | blameless note + routed spec | **DONE** | cc builds `claim_coverage_check.py` |
| 13 | stop listing two questions | **DONE** | neither appears in this handoff or the report |
| 14 | this handoff | **DONE** | — |

### Item 5 — the result and why it is not an answer about the database

`python tools/audit_event_type_check.py` → **EXIT 1**, 3 of 16 tables, 11
distinct rejected values:

| table | rejected values | emitted by |
|---|---|---|
| `sairncode_audit_log` | `credential_change_refused`, `pin_setup` | `api/sc-ai.js`, `api/sc-auth.js` |
| `sairnlaw_audit_log` | `ai_interaction`, `ai_rejected`, `ai_reviewed`, `ai_used_in_filing`, `deadline_engine`, `legal_reference_lookup` | `api/law-auth.js`, `api/legal-citator.js`, `api/legal-deadlines.js`, `api/legal-reference.js` |
| `stonedesk_audit_log` | `order_link_created`, `order_link_revoked`, `pin_setup`, `sub_roster_write` | `api/sd-auth.js`, `api/sd-sub-auth.js`, `api/sd-sub-data.js`, `api/stonedesk-track.js` |

**The tool reads the CHECK out of `sql/*.sql`, not out of Supabase**, and says so
in its own LIMITS: *"a CHECK this tool reads out of a file is not proof the
constraint exists in Supabase."* So **"the migration did not take" and "the
repo's DDL lags the database" are indistinguishable from here.** The marker in
`docs/2026-10-06-hank-routed-to-fourth.md` now says exactly that rather than
picking the reading that sounds better. Also recorded: `sv_audit_log` has **no**
`event_type` CHECK at all, listed apart from the clean ones.

### Item 10 — 21 of 86, and the denominator is in the register

**RECOVERED and moved out of `entries`:** `tests/faults/sd_write_faults.js` —
green because **b8 fixed it**, and the entry outlived the fix by a batch — and
`tests/hover_separation_ci_probe.py`. Entries 86 → 84, recovered 9 → 11.

**LEFT IN PLACE because not-run is not green:** four came back exit 2 or timed
out. Moving one would quietly declare a red suite fixed.

**65 NOT DRIVEN.** 86 suites at a 180s ceiling is about three hours; I chose a
stated denominator over a sweep that would have consumed the batch, and
`_b9_census_2026_10_13` in the register carries the count, the four third-state
suites by name, and `scratchpad/drive_red86.jsonl` as the authority. **NEW: none
in this subset — and it could not have found one, because the subject was the
register's own list rather than a fresh census.**

---

## 4. CLAIMS AND EXTERNAL HOLDS

| hold | count | detail |
|---|---:|---|
| repo claims held | **1** | b9, 10 files, committed locally, mirrored to the registry |
| session locks held | **1** | `fourth.lock`, pid 61696 — **b8's release was DENIED by the permission layer and it is still here** |
| locks released by me | **0** | none of the 8 dead ones is attributable; fifth batch |
| worktrees besides main | **0** | |
| `git stash` | **0** | |
| `refs/salvage/b6-*` | **2** | still live; item 4 did not trigger |

---

## 5. WHAT IS OPEN, AND WHY

* **The push.** 28 commits, five batches. One blocker diagnosed and fixed this
  batch; the standing one is the hooks-off `TOOLING-INVENTORY` generator, routed.
* **65 registered red suites not re-driven.** Log and denominator recorded.
* **The audit-log constraints** — 3 tables, 11 values. hank's, and it needs a
  live read nobody in this clone can do.
* **`tests/run_tier_a_review_gate_probe.py`** — exit 0 with two **unplanted**
  `PermissionError` tracebacks. cody's. The third traceback IS planted and
  correct, and telling them apart is the finding.
* **`tests/seam_check/run_delegation_probe.py:76, :80, :113, :119`** — cody's.
* **`tools/session_lock_check.py:128, :349, :357`** — cc's, fifth batch.
* **`tools/sairn_claim.py:1966, :1921, :2414`** — cc's.
* **`tools/register_feed_gate.py:747`** — one message for two causes. cc's, new.
* **`claim_coverage_check.py`** — spec routed, built by nobody here.
* **The 36 seq 17-A findings** — all 23 sites' subjects verified; the findings
  are open by design.
* **`fourth.lock`** — still held; the b8 release was denied.

**Nothing is partial except item 10, whose denominator is stated in three
places, and item 4, which did not trigger.**
