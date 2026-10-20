# ROUTED TO fourth — close the 3 rollup findings cody b26's retier created

**cody b27, 2026-10-19.** Michael asked cody to confirm the `leg_clergy` rollup
row is closed after the b26 tier change and to close it if not. **It is not
closed, the fix is proven below, and cody did not apply it — `fourth` holds
`docs/CRITICALITY-TIERS.md` under a live claim** taken 2026-10-19T20:41:49Z,
whose own subject is that register. A declared-file block is real.

## The 3 findings, and all three are cody's to own

`python tools/criticality_tier_check.py` → `PROBLEMS:14`, of which three are
the `leg_clergy` B→A retier cody landed in b26 and **two more are cody b25's
`customers` B→A retier**, which nobody reconciled either:

```
LIST MISSING sairnlegacy/leg_clergy is Tier A and is not named in the rollup list.
COUNT        sairnlegacy rollup says A=**20**, the rows say 21.
COUNT        sairnlegacy rollup says B=16, the rows say 15.
COUNT        sairnscape  rollup says A=**3**,  the rows say 4.    <- b25, customers
COUNT        sairnscape  rollup says B=9,  the rows say 8.        <- b25, customers
```

**A retier that updates the row and not the rollup is the defect the checker
exists for**, and cody did it twice. Named here rather than left for the
checker to keep reporting.

## The fix, DRIVEN IN A DISPOSABLE WORKTREE, not suggested

Three commands. The first is cc's tool doing its own job; the other two are the
counts, which that tool does not fix.

```bash
python tools/criticality_tier_check.py --fix-rollup-list
#   INSERTED  sairnlegacy/leg_clergy into the rollup list
```

Then the two count cells, exactly these four characters of change:

```diff
-| `sairnlegacy` | 36 | **20** | 16 | 0 | **RE-TIERED** — …
+| `sairnlegacy` | 36 | **21** | 15 | 0 | **RE-TIERED** — …

-| `sairnscape` | 12 | **3** | 9 | 0 | **RE-TIERED** — `customers`, …
+| `sairnscape` | 12 | **4** | 8 | 0 | **RE-TIERED** — `customers`, …
```

**MEASURED AFTER APPLYING ALL THREE, in a `git worktree` at b27's tip:**

```
PROBLEMS:14 -> PROBLEMS:9
docs/CRITICALITY-TIERS.md  2 insertions, 2 deletions
python tools/md_table_check.py   TOTAL_MALFORMED_ROWS:0
```

The five that close are exactly the five listed above. **The remaining 9 are
not cody's and are not touched by this**: `shared` has a rollup line and no
registry (GONE), `sairnsenior/sen_period_closings` is registered with no row
(NO TIER), and the seven `shared.js` resources that have rows and no registry
entry (NOT A RESOURCE) — the same `apps_with_registries()` blind spot
`api/_resources/routes.js`'s header documents.

## Why cody did not just do it

`fourth`'s active claim declares `docs/CRITICALITY-TIERS.md`. b27 already hit
one real file-level block this batch (hank on `api/_lib/leg-roles.js`) and
dropped the file rather than argue; this is the same call. The worktree used to
prove the fix was removed.

**If fourth would rather cody landed it, say so and it is three commands.**
