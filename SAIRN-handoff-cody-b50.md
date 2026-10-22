# SAIRN handoff — cody b50 (2026-10-22)

Three answers and one file. Nothing is half-finished.

## Committed / pushed state
On origin/main, no force. Both commits were checked with `git merge-base --is-ancestor` after a fetch:
- `ac68c838f`: `sql/2026-10-22-cody-b49-leg-f3-residue-removal.sql` and the path-manifest override.
- `846887d4e`: chore(claims): cody releases sairnlegacy.

The claim tool's own push carried both commits through the pre-push gate.
The cody override for b50 replaces b49's and names only that one sql file.

Claims held: **none**. `.claude/claims/cody.json` has no active entry; sairnlegacy was released at 2026-10-22T15:13:06Z.

Transcript: `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## 1. The residue-removal SQL: `sql/2026-10-22-cody-b49-leg-f3-residue-removal.sql`
**Correction:** b49 put the removal SQL only inside `docs/live-residue/…json`. CLAUDE.md says SQL goes in `sql/` and the digest gives the path only. This file is that fix.

What the file does:
- **Step 1** (read-only) — expect **1, 1, 2**. Anything else: stop.
- **Step 2** — ONE transaction. It deletes:
  - test cremation `CR-B49-F3-LIVE-F3D9FB`;
  - the spent token prepared by `b49-f3-apprentice`;
  - the two DEACTIVATED test credentials. These are role apprentice and director, never an owner.
  - It also runs the PR 3.4 guard: it aborts if no active `owner` would remain. SAIRNlegacy's PROVISIONING_ROLES is `['owner']`.
- **Step 3** — expect 0, 0, 0 and at least 1 active owner.
- **Not touched:** `sairnlegacy_settings` (already restored by the run) and `sairnlegacy_audit_log` (a ledger, not residue).

Checks run on the file:
- `employee_auth_guard_check --changed`: OK.
- `sairn_sql_preflight --live db/schema_snapshot.json`: 0 findings, exit 0.
- Every column it references is present in the snapshot.

Without `--live`, preflight exits 2. That is the tool's "declared schema only, NOT A PASS" state, not a finding.

## 2. "Disciplines #40?" — what it meant
- `docs/2026-09-13-cross-domain-disciplines.md` has **39** numbered conventions today. I counted the `## <n>.` headings. The last is #39, "A CHECK IS WORTH WHERE IT RUNS".
- "#40" was my offer to add a 40th, from b49's finding: **a checker's `skipped` list is a silent pass.**
  - `tests/run_adversarial_prompt_corpus_probe.py` sat red for 26 days inside probe_anchor_freshness's `skipped` list, which CHECK 5e never printed.
  - Then my first fix moved the anchors out of BOTH lists: skipped went from 1 to 0 while the counted total stayed at 645.
  - **The rule:** prove the COUNTED total rose by the expected number, plus an ablation that reads VANISHED. "Skipped fell" is not proof.
- It is not written into the doc. That doc is a standing document under docs/, which belongs to fourth, and adding a convention is Michael's call. **Decision needed: yes or no.**

## 3. Claim
Released. See above.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | b49 live residue on LEG-PINNACLE-2026 | Michael: run the sql file — step 1, read it, then step 2 as one paste, then step 3 |
| O2 | disciplines #40 | Michael: yes → whoever holds docs/ adds it; no → nothing |
| O3 | carried from b49: probe_anchor_freshness ignores bare-tuple edits | cc |
| O4 | carried from b49: no countersign UI in sairnlegacy.html | fourth |
| O5 | carried from b48: Tier A review of `d6b37bb1c` | cc |
