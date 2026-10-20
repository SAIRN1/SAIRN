# SAIRN handoff: cc, batch b29, 2026-10-20

**Six items, all six closed.** Everything is committed and pushed. The tree is
clean, there are zero stashes, and nothing is half-finished. No override of any
kind was used.

**Read §4(a) first.** The list is **37 tables from 28 files**, not 23 from 18.
All 28 files already exist, **none has ever been run**, and **no SQL was run
this batch**.

---

## 1. Pushed state

| | |
|---|---|
| Branch | `main` |
| Claim commit | `fb41521b` — taken **before the first edit**, with a FILES list |
| **Push range start** | **`43a3513a`** — `sql+tier-a(cc b29): 37 never-created tables from 28 files...` |
| Push | **LANDED, no force.** `8eeabd1c..43a3513a`. `git fetch` then `git rev-list --left-right --count origin/main...HEAD` gave **0 0**. Two rejections before that were remote moves (fetch-first, then cannot-lock-ref); each was answered with `git pull --rebase` and nothing was skipped |
| **Overrides** | **NONE.** No `SAIRN_SKIP`, no `SAIRN_GATE_EXEMPT`, no `--force`. `docs/BYPASS-LOG.jsonl` gained no row |
| Claims held | **`cc`**, released after this handoff, the report and the digest land |
| Exclusions honoured | `api/`, `tests/` and every `.html` file **untouched**; in `tools/` only `batch_manifest.py`, under a widened claim (`06bf7389`, re-taken after release `7f21e39c`) |
| Context at wrap | **32.0% of 1,000,000** (320,322 tokens, measured). The red-flag threshold is **85%**: `tools/builder_context_watch.py` `THRESHOLD = 85.0`, read, not assumed |

**The range end is not named.** The start commit never moves; the tip moves
every time this handoff's own commits land, so take the tip from
`origin/main` (this is b28's §2 answer).

**Read back from `origin/main`, not the working tree:**

- `sql/b29_never_run_tables_verify.sql` is present, with 37 table rows.
- `sql/sairnscape_org_intel_schema.sql` contains `enable row level security`.
- In the tier-a record for fourth 2026-10-20T06:38:48Z, status is `reviewed`
  and reviewer is `cc`.

## 2. What is CLOSED

**Item 1: the list.** The deliverable is `sql/b29_never_run_tables_verify.sql`:

- the 28 files in run order, with the tables each one creates;
- **one read-only query that always returns 37 rows**, each PRESENT or
  MISSING, plus a total row.

Why 28 files and not 18: the freshness tool's `QUERY_RE` misses 14 tables that
are reached through a constant or a generic handler, and `dnt_gfe` is one of
them (confirmed MISSING live).

Column shape was checked against every `api/` read, write, filter and
`on_conflict` for all 37 tables:

- **0 mismatches**;
- **no table needed a guessed shape**;
- preflight `--live` reports **0 findings on 28 of 28**.

Two never-run files were tightened before their first run:

- **`sairnscape_org_intel`.** It had no RLS and no revoke, so as written it
  would have been readable and writable with the anon key.
- **`rf_supplier_documents`.** A bare GRANT could not make its own verify come
  true.

Detail: `docs/2026-10-20-cc-b29-notes.md` §1.

**Item 2: root cause.**

- **The failure is swallowed at two layers, by design.**
  - The API answers a missing-table READ with **HTTP 200
    `provisioned:false`**.
  - Clients merge `[]` as a no-op and save to localStorage before the write,
    so the 503 becomes a *"saved on this device only"* toast.
- **No different table is being hit.**
- **Proven live** with signed-in reads on four tables.
- **Where it is not silent, it fails CLOSED:** the SAIRNcare witness gate
  refuses every controlled-substance count today.
- **Whether real customers ever reached these paths cannot be told from the
  repo, and is not claimed.**

Detail: notes §2.

**Item 3: batch manifest.** Produced as `docs/batch-manifest-cc-b29.json`,
**closed** with a Drive verify. The contract was right; cc's practice had
lapsed since b20.

**And the close was hollow, so it was fixed** (`tools/batch_manifest.py`, cc-owned, claim widened first). Every `--close` since `16c4715c` (b27) wrote `"deliverables": []` over a verify that passed, because the verifier began printing a line count between `bytes` and `sha256` and the parser required them adjacent. Now `deliverable_shas()` anchors on the two ends, and a PASS that names fewer than 3 deliverables is **exit 2, not a close**. Fixtures 39/39, failing-first shown (old pattern on the current shape reads `[]`), positive control closes with 3. `CRITERIA_VERSION` 2026-10-20.1. The b29 close now names all three.

**Item 4: Tier A `dnt_gfe` + `dnt_credentials`.** Discharged.

- `lateBy===0` was **driven**: 140,160 cases × 9 zones, 0 mismatches, all
  2,190 on-due-date cases render "in time".
- Three mutation controls each fail it, which proves the harness can catch a
  defect.
- `due<=today` was re-decided from the rule's own words, "not later than".
- **HIGH:** `dnt_gfe` does not exist in production.

Harness: notes Appendix A.

**Item 5: concepts.** Stated before each file. Notes §4.

**Item 6: pushed.** No force, 0 0 against origin.

## 3. One thing I got wrong and caught

**Git Bash on Windows silently drops a `TZ=` prefix.** The first nine-zone run
of the GFE harness was nine runs of New York, and every one passed. I caught it
before reporting by printing the zone node actually resolved. The harness now
sets the zone in-process and **exits 2 if `Intl` disagrees**. That is a
could-not-run state that had been folding into a pass (PR §1.11), in my own
control.

## 4. What is OPEN, and why

**(a) NONE OF THE 28 SCHEMA FILES HAS BEEN RUN.** These are not cc's to run.
Until they are run:

- every write to those 37 tables answers 503 (or 502 on two roofing paths);
- the data stays in one browser.

Highest urgency, in order:

1. **`dnt_gfe`** (file 18). It is a 45 CFR 149.610 record, and its issued
   date lives only in localStorage.
2. **SAIRNcare witness** (file 22). Count entries are refused outright.
3. **`sen_authorizations` and `sen_payer_contracts`** (files 13 and 12). A
   locally-saved contract or authorisation is applied to claims on that device
   only.

**(b) b28's three rt_stops SQL files are still unrun.** `b24 FINDING 1 (HIGH)`
is still open. Carried unchanged.

**(c) `tools/schema_snapshot_freshness.py` still under-reports by 14.** Not
fixed here: that file was outside this claim, and a matcher change needs its
criteria locked by fixtures before it runs. **Until it is fixed, anyone told to
"work the list from the tool" gets 23.**

**(d) Eight code defects were found and routed, not fixed** (`api/` and
`.html` were excluded). The table is in notes §1. The sharpest three:

- `api/accounting.js:296` reports a **false success on a credential discard**;
- `api/sd-data.js:18047` tells the user to run **the wrong file** for
  `dnt_gfe`;
- `sd_quote_request_photos` is **written and never read** anywhere.

**(e) MEDIUM grant end state on 7 files.** These are the three `sen_*` files
and the four dental files. None does `revoke all ... from service_role` before
its grant, so what service_role holds depends on `pg_default_acl`. RLS is on in
all of them, and the default ACL does not grant DELETE (grant-sweep skill).

**(f) Notes addressed to cc in the status registry, outside this dispatch and
not actioned:**

- cody (2026-10-05): SAIRNscape `customers` B→A retier plus the two-line gate
  edit; two register cell rewrites; index rows.
- hank (b26): path-scope probe registry entry and the `CLAUDE.md` count
  corrections at `:256` and `:302`.
- hank (b18): FMEA drafts and suite drivers.

Each is still waiting.

**(g) Not reviewed:** whether `gfeAddBusinessDays` should skip federal
holidays. It is outside fourth's five attack points.

## 5. Exact next step, per open item

| item | next step |
|---|---|
| (a) | **Michael runs the 28 files in the order printed in `sql/b29_never_run_tables_verify.sql`**, starting with 18, 22, 12 and 13 if not all at once. Then run that file's query: it must read **`37 present of 37`**, and any MISSING row names the file that did not apply. Then re-capture with `sql/schema_snapshot_query.sql`, save as `db/schema_snapshot.json`, and **commit** |
| (b) | Michael runs `sql/rt_stops_license_hash_composite_fk.sql`, then `sql/rt_stops_fk_probe.sql`, then `sql/rt_routes_drop_saved_sane.sql`, reading each file's verification query (b28 §5) |
| (c) | Next cc batch with `tools/` in scope. Lock fixtures first, in both directions: a `TOKEN_TABLE = '<t>'` constant and a resource-map entry must read as queried; a comment-only mention must not. Then widen the matcher. Success is the tool reporting 37 against this snapshot |
| (d) | cody: accounting `:296`, `:142`, `:260`; sd-data `:18047`, `:10468`, `:10570`. hank: `stonedesk.html:30672`; intake-photo reader. fourth: `sairnroofing.html:4175`, `:4833`; senior local-only contract and auth |
| (e) | After (a), run `select grantee, privilege_type from information_schema.role_table_grants where table_name in (<the 7 tables>)` and confirm no DELETE |
| (f) | A dispatch decision for Michael. Each note is pasteable from `python tools/sairn_status.py` |
| (g) | Only if Michael wants the holiday question answered from the regulation text |

## 6. Transcript

```
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\d7c0c45c-9fc3-4704-80ea-61d13ebeabb2.jsonl
```

This is session-local scratch, **not** a durable record. Everything this batch
depends on is in the repo: the notes (with the harness in Appendix A), the
verify SQL, the tier-a verdict and the manifest.
