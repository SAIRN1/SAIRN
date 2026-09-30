# `docs/live-residue/` — what a live verification actually left behind

**Every file in this directory is written by the tool that created the rows, at
the end of its own run.** One file per tool per day,
`<YYYY-MM-DD>-<tool>.json`, listing every row by **table and id column** and
carrying the `select` / `delete` / `confirm` SQL that removes it.

## Why this directory exists

On 2026-09-29 a live gate verification was driven by an ad-hoc script in a temp
directory. It answered the question correctly and it left two rows on a
**demo-facing** SAIRNmechanical licence, on tables whose `service_role` has no
DELETE grant — so removing them needed a human in the SQL editor.

The rows were only known about because whoever ran it happened to read them back
afterwards. Nothing obliged the run to say what it had created.

`tools/live_probe_residue_audit.py` already required a writing live probe to
**name** where its residue goes. Naming a path is not the same as **enumerating
the rows**, and it was the enumeration that was missing.

## The contract a tool in here satisfies

1. **Every write is recorded before the run reports success** — table, id column,
   id value.
2. **The recorder's count is checked against the number of writes the endpoint
   observed**, and the run exits `2 COULD NOT RUN` when they disagree. A recorder
   that counts only its own calls cannot see a write that bypassed it, and would
   then print removal SQL that is confidently incomplete.
3. **The removal SQL names the table's real id column**, derived from the schema
   rather than assumed. The four `mech_*` tables use `check_id`, `takeoff_id`,
   `doc_id` and `quote_id` — **not** `entry_id`, which the rest of this platform's
   blob tables use. A removal script naming a column the table does not have
   deletes nothing and, wherever the error is swallowed, reads as a clean sweep.
4. **The licence hash is DERIVED in the SQL**, with
   `encode(digest('<key>','sha256'),'hex')`, rather than pasted as a hex literal
   nobody can check.
5. **No tool in here runs a `delete`.** It prints the block; a human runs it.

## Reading a record

`removal_sql` is a list of statements in the order they must be run: the
`create extension`, the derived-hash check, one `select` per row, then the
`delete`s, then the `confirm` counts. **Run the selects and read the counts before
any delete** — if a select returns more than the one row it names, something other
than the probe wrote there and the delete's predicate is wrong.

## What this directory does NOT tell you

- **A missing file is not evidence of a clean run.** It means no tool wrote one,
  which includes the case of a tool that was never obliged to.
- **A record is true as of its run.** A row it lists may have been removed since,
  and the `confirm` step is the only thing that settles that.
- **Rows created by anything outside `tools/ tests/ scripts/` are invisible here**,
  which is the same blind spot `tools/live_probe_residue_audit.py` discloses: its
  universe is tracked files, and the 2026-09-29 script was neither tracked nor in
  those directories.
