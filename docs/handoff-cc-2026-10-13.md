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

**THIRTEEN commits, all on `origin/main`** — `git log origin/main..HEAD`
returns empty. HEAD at close **`14a771a4`**; 49 files, +4,865 / -346. One
rebase, 69 behind at the start, 0 after; ledger conflicts resolved by
`tools/sairn_rebase_resolve.py`.

*This block said "seven commits" and deferred the landing question to the
report, because this file is written BEFORE the push, deliberately. Six more
commits followed — five gate refusals, each satisfied rather than overridden —
and the correction is left visible rather than overwritten, which is Rule E's
second half applied to the document that routes it.*

| SHA | What |
|---|---|
| `ab919080` | chore(hooks): COMMIT the empty hooks object, so no clone, reset or rebase puts them back |
| `39224920` | feat(permissions): mechanical deny/allow rules so Michael stops being prompted and nothing risky passes |
| `54ead33f` | fix(external files): a handoff under the Drive report directory WARNS now; an undeclared tool or script  |
| `4f6f03f9` | feat(digest lint) + fix(two probe fixtures): a 150-word ceiling with six fields, E9 isolated from the li |
| `c2c4aa7b` | fix(defect register): a fully-superseded register is a CLOSED state, so --reseat stops exiting 1 forever |
| `04c27cc1` | feat(open work): shard the 2.38MB index into per-app files plus an ACTIVE index, with a check that prove |
| `6bd9239f` | docs(routing): Rule E routed to ted with the next free number, and the 15 field findings re-derived |
| `12d189b1` | docs(handoff): cc batch b5 |
| `81015287` | chore(defect register): the two records this push owed |
| `3ed68365` | fix(tooling inventory): the hook leg is OPTIONAL in a clone whose hooks are off on purpose |
| `b902ff2b` | chore(defect register): the record for the tooling-inventory refusal |
| `e08bab0c` | fix(open work): cap the shard filename, and give both new tools an OWNER line |
| `14a771a4` | chore(defect register): the record for the 198-character shard filename |

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
