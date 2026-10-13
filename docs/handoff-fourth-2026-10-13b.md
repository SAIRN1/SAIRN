# HANDOFF — fourth / ted, batch b9 CONTINUATION, 2026-10-13

**Written BEFORE the report**, at a point where nothing is half-finished: the
push has landed, every queue item is closed with evidence or named as open with
the exact next step, and no operation is in progress.

**READ THIS ONE, NOT `docs/handoff-fourth-2026-10-16.md`.** That file is this
batch's EARLIER handoff and **it is misdated three days into the future.**
CLAUDE.md says to find the latest handoff **by the date in the filename**, so a
date-sort puts the stale one first and the correct one second. The misnaming is
not corrected by renaming it — a row in `docs/external-files-index.json` and the
Drive delivery copy both carry that name — so a banner was added to the top of
that file instead, pointing here. **If you are reading `-2026-10-16` without
having seen this file, stop and read this one.**

**Transcript and working files:**
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\d1bef68d-f747-45a9-89b1-59dd99a42ae2\scratchpad\`
Derivations are scripts and logs, not prose: `drop_scratch.py` (+
`dropped-scratch-manifest-2026-10-13.txt`), `declare_ext.py`, `rfg_probe.py`
(+ `rfg_probe.log`), `cte_fix.log`, `cte_real.log`, `cte_ctrl.log`,
`cte_reseated.log`, `gate_dry.log`, `gate_arm_unfetched.log`,
`gate_arm_known.log`, `push_b9c.log`, `push_b9d.log`, `push_b9e.log`,
`item2_audit.log`, `reg_add1..4.log`, `f_origin.txt`, `f_m2.txt`,
`refs-salvage-b6-2026-10-13.bundle`, `settings-backups-moved-2026-10-13/`,
`dropped-sql-2026-10-13/`.

---

## 0. THE HEADLINE, measured rather than claimed

**THE PUSH LANDED. `c5af98dc..d30e9e42`, 48 commits, five batches (b5–b9).**

```
git rev-parse HEAD        d30e9e42...   (at the moment of the landing)
git rev-parse origin/main d30e9e42...
git rev-list --left-right --count origin/main...HEAD   ->  0   0
```

HEAD has since moved by the two documentation commits this batch still owed
(the methodology note and this handoff), which are pushed in the same way and
restated in the report at finalisation per RULE E.

---

## 1. THE TWO THINGS THE NEXT SESSION MUST NOT "FIX"

1. **HOOKS STAY CLEARED.** `.claude/settings.json` carries **0 hook groups and
   0 entries**, and that is now the COMMITTED state — cc committed it in b5 on
   Michael's instruction, so this clone's working tree and `HEAD` agree and
   `git status` is clean on that path. **Do not restore them.** A stash holding
   a pre-cc copy was found and **dropped deliberately**, because popping it
   would have reverted cc's committed permission rules while looking like a
   routine restore.
2. **`tools/tooling_inventory.py` CANNOT BE RUN IN THIS WORKING TREE and that
   is correct.** It derives one of seven sources from `.claude/settings.json`,
   reads 0 hook entries, and refuses (exit 2) rather than writing a thinner
   document. **Regenerate it inside a detached worktree of the commit**, which
   reads the committed settings, and copy the result in. Do not "fix" the
   refusal.

---

## 2. WHAT THE PUSH REFUSAL ACTUALLY WAS — four defects, one message

The b8 diagnosis (a missing remote sha, cleared by a fetch) was correct and
**incomplete**: a one-off fetch cannot close a race that recurs. Re-diagnosed at
HEAD, **one refusal was four distinct defects**, each measured before it was
fixed and each carrying a defect record.

| # | cause | landed as | record |
|---|---|---|---|
| 1 | `tools/report_sha_check.py` (b5, `d7accea0`) and `tools/temp_state_leak_check.py` (b7, `7db6bf03`) carried **no `PURPOSES` and no `REGISTRY` entry** | `f2f9953b` | — (the entries are the fix) |
| 2 | push-gate **check 12 measured the TIP in the live working tree and the BASE in a clean checkout**, so it compared the base commit against the base commit PLUS this clone's uncommitted files | `f2f9953b` | yes, rule 1.1 |
| 3 | `register_feed_gate.py` and `copy_exactly_gate.py` treated **the REMOTE's sha, read off pre-push stdin, as a local object** | `ac9d47d8`, `55777a74` | yes, rule 1.11 ×2 |
| 4 | the same unfetched base made the **owner-header check classify every MODIFIED `tools/*.py` as newly ADDED** | `9c36aa7c` | yes, rule 1.1 |

**Defect 2 is the one that cost the five batches, and its worse half is that a
wrong subject did not merely produce a false refusal — it REPLACED the true
one.** The live-tree refusal fires on the empty derivation source *before* the
generator reaches its undescribed-tool list, so cause 1 never appeared in the
output check 12b greps.

**Defect 4 is the one worth remembering.** It did not refuse to answer, it
answered **wrongly**, and the remedy it printed instructed a land grab:
`NO OWNER: 4` over `copy_exactly_gate.py`, `register_feed_gate.py`,
`sairn_push_gate_hook.py` and `tooling_inventory.py` — all four pre-existing,
all four grandfathered by that check's own written scope — with "add an
`# OWNER:` line" as the fix. One session would have written itself as owner of
four shared tools, two of them contested, to get an unrelated push out.

### Where the fix went, and why one of the three is central

Defect 3 was fixed **twice per-gate** and then **once centrally**, in that
order, because fixing it in one gate only moved the refusal to the next gate in
`.githooks/pre-push`. `sairn_push_gate_hook.py` now resolves the base **once,
where it enters** — `git cat-file -e <sha>^{commit}`, falling back to
`merge-base(origin/main, tip)` with the substitution printed and both shas named
— so **a check added later inherits a readable base instead of repeating this a
fifth time**.

**`tools/hover_auditor_scope_gate.py:409` is the fourth instance and is NOT
fixed.** It builds `rsha..lsha` and returns *"could not read the outgoing
range"* on a non-zero git exit. It runs **first** in `.githooks/pre-push`, it
**passed every push attempt this batch**, and it is the auditor separation gate,
so it is routed with the line rather than edited by a build agent.

---

## 3. ITEM BY ITEM, with the exact next step for each open one

| # | item | state | exact next step |
|---|---|---|---|
| 1 | push first | **DONE — `c5af98dc..d30e9e42`, 0 ahead 0 behind** | nothing |
| 2 | audit-event check | **DONE — EXIT 1, unchanged across 27 upstream commits** | §4; needs a live `pg_constraint` read. hank's |
| 3 | bundle then delete the salvage refs | **DONE — bundle verified, both refs deleted** | nothing; see the caveat in §5 |
| 4 | move the settings backups; drop the throwaway | **DONE — 3 backups moved, 2 SQL files moved out, 1,566 scratch files deleted** | 307 could not be deleted (locked); re-run `drop_scratch.py --apply` once the holding processes exit |
| 5 | one new check or rule | **DONE — `commit_tool_entry_check.py` built and WIRED; the input-validity rule ROUTED, not self-promoted** | whoever runs convention intake takes the rule; NEXT FREE is 35 |
| 6 | push and confirm landed | **DONE — shas in §0 and in the report** | nothing |
| — | handoff before the report | **DONE — this file** | — |

### Item 2 — the result, and why it is still not an answer about the database

`python tools/audit_event_type_check.py` → **EXIT 1**. Unchanged after rebasing
onto 27 upstream commits, which was the thing to check rather than assume:

| table | values its CHECK REJECTS | emitted by |
|---|---|---|
| `sairncode_audit_log` | `credential_change_refused`, `pin_setup` | `api/sc-ai.js`, `api/sc-auth.js` |
| `sairnlaw_audit_log` | `ai_interaction`, `ai_rejected`, `ai_reviewed`, `ai_used_in_filing`, `deadline_engine`, `legal_reference_lookup` | `api/law-auth.js`, `api/legal-citator.js`, `api/legal-deadlines.js`, `api/legal-reference.js` |
| `stonedesk_audit_log` | `order_link_created`, `order_link_revoked`, `pin_setup`, `sub_roster_write` | `api/sd-auth.js`, `api/sd-sub-auth.js`, `api/sd-sub-data.js`, `api/stonedesk-track.js` |

**3 of 16 tables with a CHECK, 11 distinct values. `sv_audit_log` has no
`event_type` CHECK at all** and is listed apart from the clean ones. Every one
of these is a write that fails at the database; `writeAuditLog` is non-fatal and
returns false, so the calling code carries on and the row is simply absent.

**The tool reads the CHECK out of `sql/*.sql`, not out of Supabase**, and says
so in its own LIMITS. So **"the migration did not take" and "the repo's DDL lags
the database" are indistinguishable from here.** It needs one `pg_constraint`
read or one real insert against Supabase with live credentials. **hank's.**

---

## 4. CLAIMS AND EXTERNAL HOLDS

| hold | count | detail |
|---|---:|---|
| repo claims held | **1** | b9 continuation, 8 declared FILES, committed AND pushed — visible to every clone without a fetch |
| session locks held | **1** | `fourth.lock` — still here; b8's release was DENIED by the permission layer and that is now a third batch |
| locks released by me | **0** | none of the dead ones is attributable |
| worktrees besides main | **4** | **none of them mine** — `gate12-65340-3`, `invis-c0-75132`, `sairn-abl-q_gv10j5`, `sairn-gate-base-d78d62e71203`. The last is the push gate's own throwaway that it failed to remove and says so. My two (`sairn-origin-probe`, `sairn-tipwt-test`) were removed and pruned |
| `git stash` | **0** | one existed and was deliberately dropped — see §1.1 |
| `refs/salvage/b6-*` | **0** | bundled, verified, deleted |

**Two files were edited outside the declared `FILES`** and are named rather than
absorbed: `docs/external-files-index.json` (one additive row plus a discharge
note; no active claim names it) and `.githooks/pre-commit` (the wiring for item
5; no active claim names it). `docs/defect-density-register.json`,
`docs/scrutiny-flags.json` and `docs/tool-owner-map.json` were also touched —
all three are **written by the gates themselves when they run**, and leaving
them dirty is what refuses the next rebase.

**`tools/register_feed_gate.py` was taken under a declared conflict, PR §4.3.**
`docs/handoff-fourth-2026-10-16.md` routed `register_feed_gate.py:747` to cc as
"one message for two causes, new". **No active claim names that file**, and it
was the standing blocker on this clone's own push, so this session took it and
**cc's routed item is discharged rather than left queued.**

---

## 5. WHAT IS OPEN, AND WHY

* **`tools/hover_auditor_scope_gate.py:409`** — the fourth instance of the
  unfetched-base shape, unfixed by decision. Routed. **Next step:** whoever owns
  the auditor clone applies the same `cat-file -e` + merge-base treatment.
* **No checker exists for the shape itself** — a sha read off pre-push stdin and
  then passed to `rev-parse`, `cat-file` or `log` with no existence test. A
  fifth gate can still be authored with it. Recorded as a **planned** action on
  defect record `55777a74`; **nothing has been built.**
* **Unmeasured, and stated rather than discovered later:** how many of the push
  gate's *other* checks were silently reading a wrong answer off the same absent
  base. Only the owner-header check happened to fail loudly, which is the only
  reason any of this was found.
* **The live-tree SCREEN in check 12 still cannot see** a document that the
  COMMITS break while an uncommitted edit compensates. Unchanged by this fix,
  stated in the code, and it is the fail-open direction that check's own scoping
  decision already accepts in writing.
* **`docs/TOOLING-INVENTORY.md` lists `commit_tool_entry_check.py` as UNWIRED
  while it is wired into `.githooks/pre-commit`.** The generator derives wiring
  from `.claude/settings.json` hook entries and from the push gate and reads
  `.githooks/` for neither, so **every pre-commit-wired tool is under-reported
  the same way.** Not fixed — it is a change to the inventory's source list in a
  file two sessions contest. **Next step:** add `.githooks/` as an eighth
  derivation source, with the owner of that file.
* **4 pre-existing bad rows in `docs/scrutiny-flags.json`** — `2a3a95c2` and
  `3ead2e86` accused of changes their diffs do not contain, over
  `tools/tier_a_review_gate.py` and `tests/run_tier_a_review_gate_probe.py`.
  **Already on `origin/main`, not added by this batch**, and that was measured
  rather than assumed: the checker exits 1 with exactly those 4 rows against a
  clean worktree of `origin/main`, and the failure set after every merge this
  batch made is byte-identical. **cody's files.** They make
  `tools/sairn_rebase_resolve.py` REFUSE on every scrutiny-flags conflict, which
  is a standing tax on every rebase in every clone.
* **The audit-log constraints** — 3 tables, 11 values, plus `sv_audit_log` with
  no CHECK. **hank's**, and it needs a live read nobody in this clone can do.
* **307 scratch files could not be deleted** — locked by live processes. The
  manifest lists all 1,873 candidates; re-running `drop_scratch.py --apply`
  clears the remainder.
* **`fourth.lock`** — still held; the release has now been denied in three
  successive batches.
* **A `git push` issued from inside a shell wrapper is refused** by
  `register_feed_gate` with *"stdin is not a terminal and carried NO ref
  lines"*. Hit once this batch (`push_b9e.log`). **Issue the push as its own
  direct command** — the gate's own message says so, and it is correct.
* **The salvage bundle lives in `%TEMP%`**, which is declared HIGH volatility.
  That is acceptable only because both refs were **PROBE FIXTURE commits** —
  `"PROBE ambiguous-subject fixture -- not a real commit"` and `"drop a
  generator"` — and neither is an ancestor of `origin/main`, checked with
  `merge-base --is-ancestor` before deletion. **No real work was in them.**

**Nothing is partial except item 4's 307 locked files, whose count and manifest
path are both recorded.**
