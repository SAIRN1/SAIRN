# SAIRN handoff — cody b52 (2026-10-27)

All six items are closed. Nothing is half-finished. Items 3 and 5 each include one routed half that is outside a build agent's scope, as follows.

## Committed / pushed state
On origin/main, no force. Every commit below was checked with `git merge-base --is-ancestor` after a fetch:

| commit | what |
|---|---|
| `d8f47f7ab` | fix(sd-data): a per-resource cap is measured as jsonb text (hover **H2 seq1109**) |
| `bb1d93a88` | test(rf_jobs): the write response's assignee and `ok` are pinned (**H2 seq1127**) |
| `21fc838ab` | feat(vercel): `frame-ancestors 'none'` and `X-Frame-Options: DENY` on every response |
| `ca5a88be5` | live residue and its removal SQL |
| `8e35dce1f` | fix(dora_metrics): the CFR numerator is drawn from its own denominator |
| `c2c39263d` | fix(tools): seven status/coverage tools now print what their population left out |
| `0c46dc3b9` | Tier A obligation for the cap change, assigned **cc** |

Plus register records and re-seats, regenerated derived docs, and gate bookkeeping.

- **Claims:** none held. `platform` (b52) was released after the work landed.
- **Status registry:** idle.
- **Path manifest:** cody override b52 replaces b51 and names every file edited this batch.
- **No skip and no override was used.**
- **Transcript:** `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\2d1bcf76-c842-40ed-b21d-9b20d98e7d45.jsonl`

## 1. H1's #1613/#1614 pointer (Drive `SAIRN-pointer-H1-to-cody-1613-1614-b84.md`): CLOSED, nothing to fix
The pointer itself says both are closed by my b28 `7e43c9dab`. I verified that at HEAD rather than taking it from the pointer:
- `7e43c9dab` is an ancestor of HEAD.
- `countersign.js` re-reads the roster role (`select=employee_id,role`, `currentStanding(..., ctx.callerEmployeeId)`) and checks preparer and signer in the settling step.
- All four sd-data call sites pass `callerEmployeeId`.
- `api/b28-role-from-token.test.js` 15/0.

I did not run H1's repro driver: it lives under `.claude/skills/sairn-hover-auditor/`, which is hover scope.

## 2. "seq1127" = **H2 seq1127**: DONE
H1's seq1127 is unrelated housekeeping; the routable finding is H2's.

The finding: the rf_jobs write response's `assigned_employee_id` (`requestedAssignee || ''`) and `ok: true` were never asserted, so five Stryker mutants survived.

The fix:
- Arms W2a/b/c drive the real handler for the three ways the assignee resolves: requested → itself, `''` → `''`, omitted → the stored value. Each also asserts `ok === true`.
- `api/b32-rf-jobs-projection.test.js` 10/10.
- **I hand-planted all five mutants and each one now turns the suite red.**

## 3. b28's live staff write and the vercel.json frame headers: DONE
**Live staff write, on https://sairn.vercel.app with DNT-PINNACLE-2026:**
- The owner created a 96,419-byte appointment with two photos: **200**. The old uniform cap was 65,536.
- The owner then declined it, sending the whole row with photos: **200**.
- Read-back: Declined, with both photos byte-identical in length.
- So b28's raised cap is live. Before b28, both writes would have been 413.
- The demo practice has **0 publicly bookable procedure types**, so the booking was created by staff rather than through public-book.
- It used the existing demo patient PT-DEMO-1, so **no new dnt_patients row** was created. That matters because that table has no delete.
- Residue is one Declined row, `AP-B52-LIVE-C68954`. Removal: `sql/2026-10-27-cody-b52-dnt-residue-removal.sql` (step 1 expects 1, step 3 expects 0).

**Frame headers:**
- vercel.json now starts with a catch-all route (`continue: true`) that sets `Content-Security-Policy: frame-ancestors 'none'` and `X-Frame-Options: DENY`.
- This closes the "header form" item fourth b43 left open by instruction.
- `'none'` rather than `'self'`, because no app embeds another (no `<iframe>` anywhere, measured) and the satellites are link pages, never embeds.
- `tests/vercel_frame_headers.js` 6/6; against the old config, 4 of its arms fail.
- **Live: both headers are on all 6 pages checked, and all 6 still render at top level.**

## 4. "seq1109" = **H2 seq1109**: DONE
The finding:
- The dnt_appointments and rf_claim_photos caps EQUAL their tables' `*_data_size` constraints, but the gate counted compact JSON.
- The constraint counts `octet_length(data::text)` on jsonb, which has a space after every `:` and `,`.
- In that window a record cleared the gate and was then refused by the table with an unclassified error.

The fix:
- **Per-resource caps now measure jsonb text** (`api/_lib/jsonb-text-bytes.js`), after the dental location stamp.
- The uniform 64KB default is a policy, not a constraint, so it keeps the compact measure.

`api/b52-cap-jsonb-measure.test.js` 6/6:
- J1: the measure equals hand-written jsonb text on 7 shapes.
- J2: a fixture is 1,290,994 bytes compact (under the ceiling) and 1,936,406 as jsonb (over it).
- G1: that fixture gets 413 at the gate.
- G2: a 200KB photo booking passes.
- G3: the default cap is untouched.
- X: with the compact measure restored, the J2 fixture gets through (200).

Regressions green: b28-photo-cap 23/0, b30 22/0, b40 27/0, appointments-photos, sd-photos 26/0.

## 5. Methodology: the denominator sweep
**`tool_provenance_status.py` is hover2's** (`.claude/skills/sairn-hover-auditor/tools-hover2/`). Running it was **denied** and editing it is outside a build agent's scope, so I audited it from source and **routed it to hover2 through the status registry**.

Defect (1) — the denominator:
- `SKIP` silently removes 3 files from N in "DUE: d of N", and one of them is the tool itself.
- By its own docstring, the tool is not independently validated, so excluding it overstates coverage.

Defect (2) — the numerator:
- Validations are counted by bare filename with no content hash, so a tool edited after its validation still counts as validated.

**Sweep of `tools/`:** a subagent examined 33 files and found 8 instances. I re-read every one in the code and fixed all 8:

| tool | the miscount | after the fix |
|---|---|---|
| `dora_metrics.py` | the CFR numerator (every injection commit, any date or path) was divided by this window's deployable commits | **11.7% printed, 6.4% true**; 117 of 260 outside, now printed. Probe +2 arms, red on the old tool |
| `suite_control_coverage.py` | 13 control files and 195 nested files were dropped without being announced | counted beside "N suite(s)" |
| `probe_anchor_freshness.py` | an unresolvable MUTATIONS entry was `continue`d out of every count | now a `skipped` row (0 affected today) |
| `checker_denominator.py` | checked and universe came from different sets | checked is the intersection, and the rest is printed (0 outside today) |
| `second_pass_coverage_scan.py` | the filter applied to first passes only | symmetric; 84 actions / 22 suites printed |
| `condition_coverage.py` | `--limit` printed the cut count as the population and could exit 0 | full count kept; a clean subset exits 2 (documented) |
| `auth_header_name_sweep.py` | 2 files dropped uncounted | counted |
| `session_recheck_coverage.py` | 9 test files excluded silently | counted |

**Left as clean-by-rule, and recorded in the register's recurrence note:**
- `resource_reachability_check` per-app totals versus its header total.
- `blob_conversion_coverage` docstring versus its .test.js skip.
- `entitlement_freshness_check` EXTERNAL_OWNED.
- `secrets_inventory`'s hard-coded "47 / 11".

**Pre-existing red, not caused by this batch:** `tests/run_condition_coverage_probe.py` arm 4b. It is identical with my change stashed; it is about restoring against a modified baseline, and the gate's own scrutiny-row write dirties the tree.

## Open, and the exact next step
| # | open | next step |
|---|---|---|
| O1 | hover2's `tool_provenance_status.py`: the SKIP-hidden denominator and validations with no hash | hover2: keep the tool in N and print SKIP's count; add a content sha to ledger events and treat a mismatch as STALE (note in the status registry) |
| O2 | Tier A review of `d8f47f7ab` (assigned cc) | cc: confirm no legitimate payload near a cap is newly refused |
| O3 | residue `AP-B52-LIVE-C68954` (Declined, harmless) | Michael: `sql/2026-10-27-cody-b52-dnt-residue-removal.sql`, step 1 first |
| O4 | the demo practice has 0 publicly bookable procedure types, so public booking cannot be driven live on it | Michael / fourth: decide whether the demo should offer one |
| O5 | the four milder tool cases above | cody or cc, if dispatched |
| O6 | the 64KB default cap still measures compact JSON against 65536 jsonb constraints (a small window, not routed by H2) | decide whether the default should also measure jsonb text; it would tighten every resource slightly |
