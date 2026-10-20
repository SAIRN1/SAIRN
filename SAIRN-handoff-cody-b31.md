# SAIRN handoff — cody b31 (2026-10-20)

Six items. Four changed code, two were **already closed at HEAD** and are
reported as verified, not re-done. Handoff written at a safe stopping point:
code committed as `d593d8461`, not yet pushed when this was written.

| Item | State |
|---|---|
| 1. push-retry loop recommits the gate's write-back | **DONE** — `tools/push_retry.py`, 7 new selftest arms, 2 red under ablation |
| 2. H1 #1613 MODE_PREPARED_ONLY reads role from token | **ALREADY FIXED in b28 (`7e43c9dab`) — no change made** |
| 3. H1 #1614 settling step checks ACTIVE only | **ALREADY FIXED in b28 (`7e43c9dab`) — no change made** |
| 4. rf_invoices cap at the default | **DONE, but on `write`, not `issue`** — see §3 |
| 5. extra-actions.test.js 41/7 | **DONE — 48/0** |
| 6. Push | see the report for the verified remote state |

## 1. Item 1 — the concept, then the fix

**ONE LINE:** the gate's write-back is bookkeeping *about* the commits being
pushed, so it gets **one** bookkeeping commit that every later round **amends** —
never a new commit per round, and never folded into a work commit, because a
work commit's sha **is** the row key and amending it orphans the row the gate
just wrote.

`tools/push_retry.py` already amended generated documents but knew nothing about
`docs/scrutiny-flags.json`, so the hand-written loop (which this tool exists to
replace) committed it every round. New: `fold_scrutiny()`, called at the top of
every `--loop` attempt (a dirty tree would also block the rebase).

- **First round** creates `chore(gate-bookkeeping <tip7>): the push gate's own
  scrutiny rows` — tip sha in the subject so the duplicate-subject gate cannot
  collide — and registers the subject in the amend guard's safe set.
- **Later rounds** `git commit --amend --no-edit -- docs/scrutiny-flags.json`
  (pathspec, so nothing else staged is swept in).
- **Folds only a provable append:** every row at HEAD survives unchanged and no
  other top-level key moved. Anything else — removed row, changed key,
  unparseable file — is **named and not staged** (could-not-tell is not a pass).
- Arms run on a **real scratch repo**, because the defect was a commit *count*.
  Ablating `--amend` to a plain commit turns "round 2 AMENDS it" red.

**Two things this does not fix, both pre-existing:**
1. A rebase rewrites work-commit shas, so rows the gate wrote *before* the
   rebase name shas that no longer exist (`scrutiny_ledger_check` counts those
   UNRESOLVABLE, exit 0). They stay in the bookkeeping commit. Nothing re-seats
   them (`.githooks/post-rewrite` has no scrutiny arm).
2. A **successful** push still leaves the gate's rows uncommitted in the tree,
   so the next batch's first loop round creates the bookkeeping commit. That is
   the existing `chore(gate-bookkeeping …)` pattern, now automatic.

## 2. Items 2 and 3 — not fixed because already fixed; evidence

Both are closed at HEAD by `7e43c9dab` (b28, an ancestor of HEAD):

- **#1613** `api/_lib/countersign.js:299` — the `MODE_PREPARED_ONLY` branch no
  longer trusts `ctx.callerRole` alone: `currentStanding()` re-reads
  `employee_id,role` from the employee table under `active=eq.true` and returns
  `COUNTERSIGN_ROLE_REVOKED` if the roster role is no longer a signer. Fails
  **closed** (503) when the roster cannot be read.
- **#1614** the settling step (`countersign.js` ~line 395) loops over *both*
  attesters (preparer → `isPreparer`, signer → `isSigner`) with a fresh
  `currentStanding()` each.
- `api/_lib/countersign-endpoint.js:174` `activeCaller()` already reads role from
  the DB — the model the instruction named.
- **`node api/b28-role-from-token.test.js` → 15 passed, 0 failed**, including
  ablation arms A1 (exactly one caller lookup) and A2 (two lookups at settle).
- All four `requireCountersignature` callers pass through that one function
  (`sd-data.js` ×3, `law-attest.js`).

**I could not find the text of H1 #1613/#1614 anywhere in this repo** (open-work
index, the fourth b26 findings, the hover logs I could reach). So: *if the H1
rows describe a path other than the one above, I have not seen it* — send the
row text. Most likely they were raised against pre-b28 code.

**One observation, not a defect:** `api/law-attest.js:429` calls
`requireCountersignature` without `callerEmployeeId`. Its only locked resource is
`MODE_ALWAYS`, which never reaches the prepared-only branch, so it is
unreachable today; if that resource ever became `MODE_PREPARED_ONLY` it would
**fail closed** (no roster row for `undefined`). Left alone.

## 3. Item 4 — measured, and the measurement moved the target

b30 §4.2 said to measure the largest `issue` payload and raise `rf_invoices` to
262144. Measured with the real modules and the payloads `sairnroofing.html`
builds (`:3101`, `:3108`, `:3126`):

| verb | measured payload |
|---|---|
| `issue` | **61 bytes** (client `{invoice_id}`); 87 with `issue_date` |
| `add_payment` | 964 bytes with 200-char reference and 500-char notes |
| `write` | line items: 134 B/line typical, **438 B/line worst**; **nothing bounds the line count** |

`issue` is two orders of magnitude inside the 64KB default; raising it would
loosen a gate for no measured need. The verb that can approach the table's
ceiling is **`write`** (draft carrying `line_items`). So the entry is
`PAYLOAD_CAP_BY_ACTION['rf_invoices|write']`, **not** a per-resource cap that
would also loosen `issue`/`add_payment`/`reconcile_claim`/`gl_export`.

Derived like `rt_routes`: `RF_INVOICE_DATA_CEILING (262144, = rfinv_data_size) +
32768 allowance = 294912`. Arms (in `api/b30-cap-per-action.test.js`, now 22/0):
W1 a 256000-byte write passes the size gate; W2 307200 → 413 naming
`rf_invoices/write` and 294912; **W3 `issue` still 413 at 65536** (what fails if
someone sets a per-resource cap); W4 reads the SQL constraint and compares it to
the code constant, so a migration moving it fails here. Ablating the entry turns
W1 and W2 red.

**This departs from the literal instruction** (raise the cap measured on
`issue`). If a per-resource 262144 was wanted anyway, it is a one-line change and
W3 must be inverted.

**Not measured:** a live read of real stored invoices (no audit-licence access
this batch). The line-count ceiling is therefore the table's, not an observed
maximum.

## 4. Item 5 — 41/7 → 48/0, and why it was the test

All seven reds were the **suite** going stale against deliberate code changes:
Tier A `sc_` resources grew to 24 (security fix `5c781b990`) and now grant
`'tombstones'` beside `'soft_delete'`; `sc_dme` became Tier A, so `delete` on it
is a correct 400; two compute-only verbs (`'therapy_accumulator'`, `'payroll'`)
were documented with backticks where the suite requires quotes.

Fixed: expected grants/messages updated; the hard-deletable subject is now
**derived** (`resources` minus `tierASoftDeleteOnly`) instead of the name of "the
newest" resource, which is what rotted; two `//` comments requoted in
`sairncode.js` / `sairnsenior.js`. Its row in `docs/known-red-suites.json` moved
from `entries` to `recovered` (the file's own rule: a green suite must not stay
as an exemption).

## 5. Verification (all run this batch)

```
EXIT=0  node api/b28-role-from-token.test.js          15/0
EXIT=0  node api/b30-cap-per-action.test.js           22/0   (was 18)
EXIT=0  node api/_resources/extra-actions.test.js     48/0   (was 41/7)
EXIT=0  node api/b28-photo-cap.test.js                23/0
EXIT=0  node api/_lib/roofing-billing-endpoint.test.js 42/0
EXIT=0  node api/sd-data-approvals.test.js            23 assertions
EXIT=0  python tools/push_retry.py --selftest         ALL ARMS PASS
EXIT=0  node --check on all five changed JS files
```

## 6. Next

- If the H1 rows describe a different path, send the text (§2).
- Consider a post-rewrite arm that re-seats scrutiny rows (§1, limit 1).
- `docs/known-red-suites.json` total_files counter was not touched.
