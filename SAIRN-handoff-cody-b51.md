# SAIRN handoff — cody b51 (2026-10-22)

Items 1 and 2 are fixed and landed. Item 3's sweep is done and its findings are routed. Nothing is half-finished.

## Committed / pushed state
On origin/main, no force. Each commit was checked with `git merge-base --is-ancestor` after a fetch:
- `1e471c7ab` fix(countersign): an off-profile resource is refused, not passed as signed.
- `2d52f2d5b` fix(probe-freshness): a bare edit tuple is counted (criteria .3).
- `8e21a74e2` register records for both.
- `aa6c9ee16` Tier A obligation (assigned **hank**), plus the regenerated MASTER-PLAN and traceability matrix.
- `705e1ef0d` BYPASS-LOG row for the scoped skip below.
- Several `chore(gate-bookkeeping)` commits: register re-seats after rebases, and scrutiny rows.

**Said out loud (PR §3.3): I used one scoped skip, `SAIRN_SKIP=external-files`.**
- The only finding was `g:\my drive\sairn-status\h1_countersign_repro.js`, an H1 auditor file in the shared Drive folder. It is not cody's and not in this push.
- Indexing it would have meant inventing a purpose for another session's file.
- Every other gate ran and passed.

**How the push went:**
- `push_retry --loop` timed out at its 120s push limit, because the gate takes about 4 minutes on an sd-data change. So I pushed with plain `git push` (no force).
- One rebase staged conflict markers into MASTER-PLAN and traceability-matrix: my retry loop ran `git add -A` mid-rebase. The pre-commit check refused it.
- I resolved it by regenerating both files with their own tools. The ledgers were JSON-valid with no markers, and both of my ledger entries survived.

**Claims:** none held. `platform` (b51) was released after the work landed.
**Path manifest:** the cody override for b51 replaces b50's. It names countersign.js, sd-data.js, the b51 test and probe_anchor_freshness.py.

**Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## 1. The d6b37bb1 lock-drift gap: FIXED at runtime
- `requireCountersignature` used to return `null` for a resource its PROFILE did not lock, and `null` means "signed, proceed".
- All four callers ask only after their OWN table says the resource is locked: sd-data's two law gates, the leg gate, and law-attest. So off-profile means two lists have drifted, and the write would have filed with no second signature.
- **Now:** it returns 500 `COUNTERSIGN_LOCK_MISCONFIGURED` before any fetch. Because the fix is in the shared library, it covers every caller rather than one call site.
- **Test:** `api/b51-countersign-lock-drift.test.js` 5/5. The drift is made real by swapping `leg-countersign`'s PROFILE in the require cache.

| arm | case | result |
|---|---|---|
| U1 | library, off-profile | refusal, 0 fetches |
| R0 | control, no drift | the signed write files |
| R1 | drift + F3-deferred apprentice write | 500, nothing written |
| R2 | drift + unsigned owner write | 500, nothing written |
| **X** | old `return null` restored | R1's exact call FILES the record — the gap was real at runtime |

**Regressions, all green:** b18 59/0, b28 15/0, b48 8/0, leg-role-matrix 37/0, b27, b22, b19, b23, b20, b29, law phase2/session/role-matrix.

**Pre-existing reds, identical at HEAD and NOT in known-red-suites:**
- `api/_lib/law-trust-reconcile-endpoint.test.js`: a paralegal and an attorney expect 403 and get 200.
- `api/sd-data-law-trusttx-clearance.test.js`: the RPC carries no clearance field.
- Both are routed to hank.

## 2. The bare-tuple gap: FIXED
**Attribution correction:** this was not in cc's b50 report. It is my own b49 finding (handoff O1), which was routed to cc. I took it here as the dispatch asked.

The fix:
- `tools/probe_anchor_freshness.py` walked `arm(x, (SUBJ, old, new))` element by element and dropped it: it was neither counted nor unresolved.
- **Criteria .3:** a bare 3- or 4-tuple whose first element is a name or a path literal, and whose second is a string, is now read as one edit.

Results:
- Selftest fixtures in both directions: `i` (bare) is counted, `j` (bare, unknown subject) is unresolved, and `k` (bare, not an edit) contributes nothing. ALL ARMS PASS.
- Control probe 12/12. Real sweep: ok 648, 0 findings.
- **Ablation:** with the corpus probe rewritten to the bare form, the new tool reads 648 and the HEAD tool 645.

## 3. Methodology sweep: same fail-open shapes elsewhere
A subagent produced leads. Every row below was **re-read by me in the code**; that is cc's b50 methodology, under which a subagent report is a lead, not evidence.

**Class A — a lock helper returns null (= proceed) for a resource off its list (item 1's shape):**

| helper | callers pre-filter with a SEPARATE list? | verdict |
|---|---|---|
| `_lib/countersign.js` requireCountersignature | yes, all 4 | **FIXED (item 1)** |
| `sv-witness.js` requireWitness | no; called on every SV write, single lock table in the module | sound — no second list to drift |
| `sairncare-witness.js` requireWitness | no; called on every alf_mar write, single table | sound |

**Class B — a write reads the stored row and treats "read OK but body not an array or unparseable" as "nothing stored", so the write overwrites stored values (hank's 38b2b506 shape).** Verified by reading:

| site | consequence of a non-array 200 body | test for that branch |
|---|---|---|
| sd-data `leg_settings` (~:17047) | grants and apprentice lists reset to defaults | none — already routed to hank by cc b50 |
| sd-data `bld_draws` release fields (~:15823) | release history stripped, and the wholesale upsert wipes it | none; the `!ok` refusal RELEASE_FIELDS_UNREADABLE has 0 tests too |
| sd-data supplier lead times (~:2999) | observation totals reset to 0 | none |
| sd-data style profile (~:3982) | profile restarted from one sample | none |
| sd-data sb void (~:16679) | stored void read as false, so a non-manager could clear a void | `!ok` tested in 3 suites; the non-array branch is not |
| law-auth MFA setup (~:456) | a null row lets the PATCH proceed | MFA_ALREADY_ENABLED: 0 tests |

**Severity:** low. PostgREST answers every 200 select with an array, so these branches need an upstream contract break. The `.catch(null)` variant, which covers an unparseable body, is the more reachable one.

**Coverage answer:** test coverage does **not** match runtime on these branches. No suite drives a non-array 200 body at any of them. I did not fix them: they are in api/ (hank's) and outside items 1–2. They are routed below.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | Tier A review of `1e471c7ab` (assigned hank) | hank: confirm no caller relies on null for an unlocked resource |
| O2 | Class B sites above (6) | hank: refuse `r.ok && !Array.isArray(rows)` with 502 at each, and add one arm per site driving a non-array 200 |
| O3 | pre-existing reds: law-trust-reconcile-endpoint, sd-data-law-trusttx-clearance | hank: fix, or record them in docs/known-red-suites.json |
| O4 | `h1_countersign_repro.js` unindexed in the shared Drive folder | H1 / Michael: declare it in docs/external-files-index.json; until then every push needs the skip |
| O5 | push_retry's 120s push timeout is shorter than the gate on an sd-data change (~4 min) | cc: raise the timeout, or make the timeout its own class rather than "unknown" |
| O6 | my retry loop ran `git add -A` mid-rebase | not a repo change. Lesson: stage by name; it is now in memory |
