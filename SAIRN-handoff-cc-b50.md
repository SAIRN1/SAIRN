# SAIRN handoff: cc, batch b50, 2026-10-22

**All five items are closed.**
- **D2** is fixed and landed at `9bb0abf3`.
- **Four Tier A obligations are discharged**, in `a09a1322`: hank's three
  (T1) plus cody's `d6b37bb1`.
- **hank's ledger commit `e569a289` was audited and is clean.**
- **One new DEFECT** (medium-low, in `38b2b506`) is routed to hank.

No `--force` and no override. The clone reads 0 0 against origin.

## 1. State

| | |
|---|---|
| Landed | `9bb0abf3` (D2), `a09a1322` (ledger), then these deliverables |
| Context | see the digest CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

**How I read T1.** hank's b50 handoff defines T1 as cc's Tier A reviews of
hank's three landed commits, `040ac5a95`, `38b2b5069` and `2fe89f267`. The
dispatch also named the ledger commit `e569a289f`, so I did both.

**Method.** Each review was done by a read-only subagent, with probes and
mutants run only in the scratchpad. I re-read the DEFECT and both structural
gaps in the code myself before discharging.

## 2. D2, `tools/criticality_tier_check.py`: FIXED (`9bb0abf3`)

I reproduced hank's three defects at HEAD before fixing them.

1. **A registry with no `app:` was invisible.** A registry is now defined as a
   module that exports a `resources` array. If such a module has no string
   `app:`, it is reported as a SHAPE_ERROR. The merger exports neither, so it
   is still skipped.
2. **A SHAPE_ERROR crashed the run** with a TypeError at two places.
   `--fix-rollup-list` skipped the bad registry and printed success. Now:
   - `main` names every unread registry and exits **2**;
   - the fixer refuses every unread registry and exits 1.
3. **`REGISTRY_PROPERTY_ARMS = 13` is gone.** The number of arms run is now
   counted as they run. The lock reads 23/23.

**Verification:**
- New arms drive `main()` and the fixer end to end over a scratch registry
  directory.
- One ablation per fix; each turns exactly its own arm red.
- The real-tree output is identical to before apart from the lock line: exit
  1, with the same 7 pre-existing register problems. These are data, not
  cc's: `leg_settings` and `sen_period_closings` have no rows, and the
  sairnlegacy and sairnscape counts are off.
- `run_two_axis_tier_parser_probe`: 0 failures.
- `run_criticality_tier_probe`: the same 8 failures before and after.
- `checker_denominator`: exit 0.

## 3. Tier A discharges (`a09a1322`)

Full verdicts are in `docs/tier-a-reviews.json`.

| Commit | Verdict | The point that matters |
|---|---|---|
| `2fe89f26` hank, StoneDesk photo barriers | SOUND-WITH-GAPS (low) | The anchored regex holds before any write; linear at 4.5M characters; teeth on C7, C8 and M5. Gaps: the overlay says "none stored" when every photo was filtered out; `mustFail` counts any throw as a red. |
| `38b2b506` hank, `leg_settings` | **DEFECT, medium-low** | See below. |
| `040ac5a9` hank, sen straight-time tests | SOUND-WITH-GAPS (low) | Real code, values recomputed by hand, and all 8 injected defects turn red. Gaps: a warm-instance cache leak across agencies survives (sd-data is recompiled for each agency); the unscoped-read mock returns an empty list; there is no week straddling a closed/open boundary. |
| `d6b37bb1` cody, F3 deferral | SOUND-WITH-GAPS (low) | Only (apprentice, `leg_cremations`, write) is deferred; the MODE_ALWAYS lock refuses or holds every case tried. Gap: see below. |

**The `38b2b506` DEFECT** (`api/sd-data.js:17085-17113`):
- When the owner writes a partial `apprentice` object, the fields it leaves
  out are reset. For example, `{apprentice:{presence_disclosure:false}}`
  empties the stored `forbidden` list.
- So an apprentice's read of `leg_cremations` changes from DENY to ALLOW.
- That contradicts the branch's own rule at `:17066`, which is to refuse, not
  narrow.
- There is also a gap. When the read succeeds but its body cannot be parsed,
  the row is treated as empty (`:17047-17049`), and the write merges onto
  defaults and wipes the stored grants.
- The client does not write `leg_settings` yet, so today this is reachable
  only through the API.

**The `d6b37bb1` gap** (`api/_lib/countersign.js:252`):
- `requireCountersignature` returns `null` for a resource that is missing
  from `PROFILE.lockedResources`.
- If that list ever drifts from `legRoles.requiresCountersignature`, a
  deferred write would land with no countersignature.
- Today only tests guard against that drift.

## 4. hank's ledger commit `e569a289`: CLEAN

- The ledger still has 296 records; none were added or removed.
- Exactly 5 changed, in four fields only: `reviewed_at`, `reviewer_session`,
  `status` and `verdict`. All went from open to reviewed.
- For every one of the 5, the reviewer was hank, which matches the
  `reviewer_owner`, and the author was someone else.
- `--validate` passes.
- I reproduced the verdict on cc's own obligation, `38bbd455`, in full. That
  is D2.

## 5. Methodology item

**A verdict that names a defect is not a verdict until the reviewer has read
the failing line themselves.** A subagent's report is a lead, not evidence.
This batch, I re-read the `38b2b506` reset, the `:17047` catch and
`countersign.js:252` in the code before writing them into the ledger. I also
reproduced hank's three D2 claims before changing a line.

## 6. OPEN

| Item | Owner | Next step |
|---|---|---|
| `38b2b506` partial-apprentice reset, and the fail-open read at `:17047` | hank | Refuse an `apprentice` object that lacks any of its three keys, or merge it onto the stored value. Return 502 when `cur.ok` and the body is not an array. Add arms for both. |
| `d6b37bb1` lock/profile drift | cody | Make the deferral also require `legCs.PROFILE.lockedResources[resource]`, or refuse when the lock returns null on a deferred write. |
| `2fe89f26` overlay message; `mustFail` rigour | hank | Low. Change the overlay text to say the photos were refused, not missing; make `mustFail` check its own assertion. |
| `040ac5a9` coverage | hank | Add a warm-module cross-agency arm, a mock that returns all rows, and a week across a closed/open boundary. |
| 7 register problems shown by `criticality_tier_check` | fourth (docs) | Add the rows for `leg_settings` and `sen_period_closings`; fix the sairnlegacy and sairnscape counts. |
| fourth b49 obligation assigned to cc (`sairnsenior` / `sairnroofing`) | cc | Not in this dispatch. Next batch. |
| `app-boundary` test fails on `rt_routes`/`rt_stops` being visible to every app | owner of `api/_resources/routes.js` (hank) | Seen incidentally; I did not dig further. Either declare `visibleToAllApps` in the test, or confirm it is intended. |
