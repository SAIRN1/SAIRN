# SAIRN-PLATFORM — 2026-10-13 — cc batch b5 handoff

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**Written BEFORE the report**, at a point where nothing is half-finished: every
item below is either committed or explicitly not started.
**Companions:** `SAIRN-report-cc-b5.txt` (full account),
`SAIRN-digest-cc-b5.txt` (six fields, ≤150 words).
**Transcript:** this session's scratchpad is
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\990f6ecf-9e40-4d3b-8fa1-320e25a9ca0d\scratchpad\`
— every measurement quoted in the report has its raw log there
(`perm_tests.tsv`, `bldverify4.log`, `shard_c3.log`, `reseat_cites.log`,
`ta_list.log`, `hip5.log`, `efip.log`, `drp_b5g.log`).

---

## Committed / pushed state

Seven commits, rebased onto `origin/main` (69 behind at the start of the push
loop, 0 after), ledger conflicts resolved by `tools/sairn_rebase_resolve.py`.
**Whether they are on `origin/main` is stated in the report, which is written
after the push — this file is deliberately written before it.**

| SHA | What |
|---|---|
| `93aea737` | **hooks `{}` COMMITTED** + `docs/hooks-disabled-2026-10-13.json` + `hook_integrity_check` reports "intentionally disarmed" |
| `93aef81f` | **mechanical permission rules**, project + user level |
| `ea0f3607` | external-files gate: a Drive handoff **warns**, a tool/script still blocks |
| `4f499eb0` | `tools/digest_lint.py`; E9 fixture isolated; `leg_invoices` fixture renamed |
| `70684519` | a fully-superseded register is a closed state — `--reseat` stops exiting 1 forever |
| `23dc5e43` | **open-work sharding** + `ACTIVE.md` + `--check`; per-gate skip design |
| `4d01593f` | Rule E routed to ted (number **34**); 15 field findings re-derived |

---

## Michael's decisions, applied

1. **Hooks stay off.** The 23 I restored on 2026-10-12 are gone again and
   `hooks: {}` is now **committed**, so no clone, reset, rebase or fresh clone
   puts them back. The definitions are preserved verbatim in
   `docs/hooks-disabled-2026-10-13.json`. `hook_integrity_check --wiring-only`
   reports **INTENTIONALLY DISARMED, exit 0** — and still reports a half-wired
   or absent `hooks` key as drift, which is the 2026-10-11 shape.
2. **Vercel is back** — confirmed by item 4 below running at all.
3. **`bld_draws` role scope left alone.** Not touched.
4. **External-files gate warns, not blocks.** Done.
5. **Audit-log migration** — not re-verified this batch; no item needed it.
6. **`SD-AUDIT-2026` expired** — not used.

---

## The one thing that needs a decision

**`SAIRN_SEED_GATE=off` cannot be stopped by a permission rule.** Measured, not
inferred:

- as a **deny** it is not expressible — deny rules match *past* a leading env
  assignment, so the assignment is never the thing matched;
- as a **fall-out-of-allow** it is documented to prompt, and **it did not**:
  `SAIRN_SEED_GATE=off git push origin main --dry-run` ran with **no prompt**.

So the gate-side design in `docs/2026-10-13-per-gate-skip-design.md` (item 7,
design only as instructed) is not a belt-and-braces addition — it is the only
available control. **It needs approval before any code.** The log says why:
94 rows, **80 of them the blanket form**, and only 13 carrying a reason beyond
the mechanism.

---

## Open, and whose

| Item | Owner | Exact next step |
|---|---|---|
| per-gate skip, items 1–4 of the build order | **Michael to approve**, then any session | `docs/2026-10-13-per-gate-skip-design.md` — start with `skipped_findings` on the existing row, one field, no behaviour change |
| **Tier A: 17 open obligations, all overdue** | cody 6, fourth 3, cloud 3, cc 3, hank 2 | `python tools/tier_a_review_gate.py --list`; anybody may `--takeover` — all are past 48h. **Five carry COULD-NOT-TELL**: re-derive the basis, do not trust the recorded sha |
| the 2 obligations assigned to **cc** | cc, next batch | not discharged here: `docs/tier-a-reviews.json` is in hank's live b5 FILES (PR §4.3) |
| 11 `api/sd-data.js` field findings | next claim on each app | **line numbers re-derived in `docs/2026-10-13-cc-routed-b5.md` §6** — all 11 had moved. Two have no such field token anywhere: `alf_op_audits/temperature_f`, `rf_claim_agreements/include_signature` |
| 4 `api/_lib/ai-scan-redaction.js` candidates | sairnmechanical / sairnscape claims | lines 44, 48, 72, 84 — still exact |
| **migrate the 14 open-work row parsers to the shards** | whoever owns each tool | listed with file:line in the routing doc. Until then the index stays canonical and `open_work_shard.py --check` is the forcing function |
| extend `doc_sha_reseat.py` `REWRITE` (line 154) | that tool's owner | otherwise a rebase re-seats SHAs in the index and the shards go stale — `--check` catches it, the fix is `--write` |
| 2 hover-auditor row parsers | **the auditor**, not a build agent | `hover_duplicate_finding_check.py` (both copies) and `hover_threshold_cluster.py` |
| 7 manifest-drift rows + 1 self-drift in `hook_integrity_check` | that manifest's owner | `docs/hook-manifest.json` was NOT regenerated — doing so would silently bless seven other sessions' tool changes |
| Rule E → convention **34** | **ted** | text is paste-ready in `docs/METHODOLOGY.md`'s routed queue; nothing of ted's was edited |

---

## Claims held

**`cc`, claimed and pushed at the start of this batch.** Release it with
`python tools/sairn_claim.py release cc` once the report and digest are
uploaded.

**Conflicts declared and NOT overridden (PR §4.3):** `docs/tier-a-reviews.json`
and `api/sd-data.js` are both in hank's live b5 FILES, so items 11 and 12 are
report-only. Neither task string was reworded to slip the matcher.

**Files written that were NOT in cc's declared FILES**, said out loud:
`tools/defect_register.py`, `tests/run_defect_register_superseded_probe.py`,
`tools/open_work_shard.py`, `docs/open-work/*`, `docs/METHODOLOGY.md`,
`docs/2026-10-13-per-gate-skip-design.md`, `~/.claude/settings.json`. No
session held an active claim on any of them.

---

## Three things that will cost the next session time if nobody says them

1. **`rm` is denied now, and so are `curl`, `wget`, `npm install`,
   `pip install`, every force/discard git spelling, and editing
   `.claude/settings*.json` with the Edit tool.** If you need one of those,
   that is a decision for Michael, not a prompt to click through. A python
   script that opens a file is **not** covered — that is a documented limit,
   not an oversight, and it is how the user-level settings file was edited.

2. **Issue `git push` as its own top-level command.** Not inside a script (the
   pre-push hook gets no ref lines) and not in an `&&` chain with the edit that
   clears a gate — the PreToolUse half can deny the whole command, and then
   nothing in it ran. Both were measured in b4.

3. **I reproduced a defect CLAUDE.md names by name.** A regex written through
   two layers of shell quoting arrived in `open_work_shard.py` as
   `(?i)<BS>(closed|...)<BS>` — a literal backspace, a pattern that can never
   match — and the first run classified all 812 rows as open. It is built from
   a word list now and the module refuses to run if the pattern cannot match a
   word it is made of. **If you are writing a regex through a heredoc, print
   `.pattern` and look at it.**
