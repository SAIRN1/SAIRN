# SAIRN handoff: cc, batch b30, 2026-10-20

**Five of six items are closed. Item 4 is half done:** the re-capture half is
blocked on a database credential that no clone holds. Everything is committed
and pushed, the tree is clean, there are zero stashes, and no override of any
kind was used.

## 1. Pushed state

| | |
|---|---|
| Branch | `main` |
| Claim commit | `271264f4`, taken before the first edit, with a FILES list |
| **Push range start** | **`9f6c1e58`** `fix+docs(cc b30): the freshness tool sees all 37...` |
| Push | **LANDED, no force.** `1e2e033b..9f6c1e58`. One cannot-lock-ref rejection was answered with `pull --rebase`. After `git fetch`, `rev-list --left-right --count origin/main...HEAD` returns **0 0** |
| Overrides | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `--force`, no BYPASS-LOG row |
| Claims held | `cc`, released after this handoff, the report and the digest land |
| Exclusions honoured | `api/`, `tests/`, `sql/` and every `.html` file **untouched** |
| Context at wrap | see the digest's CONTEXT line (measured; under the 85% trigger) |

Read back from `origin/main`: `def queried_tables` is present in the freshness
tool, and `CLAUDE.md` carries "only seven are wired". **The range end is not
named;** take the tip from origin.

## 2. CLOSED

- **Items 1 and 2: the freshness tool.**
  - The concept was stated first (notes §1).
  - `--fixtures` passes 11/11, and the fixtures were locked before the tool was
    run on real code.
  - The old matcher fails the constant and resource-map cases.
  - Against the pre-migration snapshot, the tool's "absent and queried" list
    is **identical to the known 37**.
- **Item 3: notes routed to cc.**
  - **SAIRNscape `customers` verified live:** with the licence key alone, read
    returns 403 and write returns 403.
  - **Two register cells re-driven before applying them.**
    `supplier_lead_times` had changed from not provisioned to provisioned, so
    cody's 10-05 text was recorded alongside today's reading rather than
    pasted.
  - **Two index rows added;** the shard check is CLEAN.
  - **`CLAUDE.md` counts corrected from measurement:** 11 skippable gates
    (7 wired, 4 not) plus 3 unskippable; 39 disciplines.
  - **hank's 520 s probe:** decided NOT to land it in a sweep that allows
    300 s per check and about 270 s per shard.
  - **hank's b18 suites:** already wired by someone else.
- **Item 5: backlog.**
  - **15 FMEA drafts saved.**
  - **Tier A discharged:**
    - hank, 2026-10-19T15:04:45Z: IOLTA reconcile. MEDIUM finding:
      `inert_until` names two blockers that are both gone, and arm A4 passes
      on that text.
    - cody, 2026-10-16T12:24:12Z: not-provisioned misclassification. LOW
      finding: P2's label is misleading.
- **Item 6: pushed and confirmed.**

## 3. OPEN, and why

**(a) THE SNAPSHOT RE-CAPTURE (half of item 4) IS NOT DONE.** No clone holds a
database credential. `db/schema_snapshot.json` is still the 07:55Z capture
from before Michael's run, so:

- `tools/schema_snapshot_freshness.py` still reports 37 absent, and exits 1;
- every snapshot-reading tool is behind by 37 tables.

Done in its place:

- Preflight `--live` returned 0 findings on 28 of 28 files, against the old
  capture.
- **32 of the 37 tables were corroborated live, signed in.**

The other 5 rest on Michael's `to_regclass` check:

- `sairncare_witness_tokens`
- `sairnvet_witness_policy`
- `sairnvet_witness_tokens`
- `sd_quote_request_photos`
- `sairnscape_org_intel`

**(b) Two findings from the law IOLTA review, routed to hank.**

- `LAW_RECONCILE_ATTESTATION.inert_until` is stale, and arm A4 asserts the
  stale text.
- `decide()` says DENY for a paralegal reconcile, while the handler allows it
  as prepare-only.

**(c) P2's label in `tests/sd_data_not_provisioned_misclass.js`, routed to
cody.** "292 route through notProvisioned()" includes about 150 calls to
`unreadableNotEmpty()`, which end in a 200.

**(d) Still waiting from b29:** eight routed code defects (b29 notes §1).
Sharpest of them: the false success in `api/accounting.js:296`. The
per-file grant end state of seven files can now be read in the live catalog;
not done here.

**(e) FMEA backlog: 745 files owed** (definition in notes §6); 256 of them are
non-test product or tool files. b28's 901 used the wrong slug.

**(f) Three cc-owned Tier A obligations are still open:**

- hank 2026-10-16T13:03:47Z (20 resources)
- cody 2026-10-20T05:51:44Z (routes)
- cody 2026-10-20T11:47:22Z (rf/rt, cody's b30 work in progress)

**(g) The path-scope probe's home:** a scheduled run, not the per-push sweep.
Unbuilt.

## 4. Exact next step

| item | next step |
|---|---|
| (a) | **Michael:** run `sql/schema_snapshot_query.sql` in the Supabase SQL editor, save the JSON cell as `db/schema_snapshot.json`, commit. Then `python tools/schema_snapshot_freshness.py` must report **0 absent-and-queried** (6 comment-only tables may remain) |
| (b) | **hank:** rewrite `inert_until` to what is actually still between built and usable, re-aim A4 to the captured state, then either teach `decide()`'s locked branch `LAW_RECONCILE_PREPARE_ROLES` or say it is superseded |
| (c) | **cody:** print `unreadableNotEmpty` and `notProvisioned` as two buckets in P2 |
| (d) | **cody / hank / fourth**, per the b29 table. After (a), run the `role_table_grants` query from the b29 handoff §5(e) |
| (e) | **Next cc batch:** continue down the owed list newest-first, one `--save` per file. A multi-path `--save` writes nothing |
| (f) | **Next cc batch:** take hank 10-16 first, since it is the oldest |
| (g) | Only if Michael wants it: a cron or `/schedule` entry for the probe |

## 5. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\d7c0c45c-9fc3-4704-80ea-61d13ebeabb2.jsonl
```

Session-local. The durable record is `docs/2026-10-20-cc-b30-notes.md`, the
tool, the register, the index and the tier-a ledger.
