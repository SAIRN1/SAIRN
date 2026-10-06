# Andon log — fourth

**Started 2026-10-06 (batch 10), as a standing practice rather than a one-off.**

An **andon pull** is a halt-and-flag: I stop a specific item short of
merge/deploy because of a genuine uncertainty, say so here, and keep going on
everything else. **A pull is never held against the puller.** The thing that
gets held against somebody is shipping past the doubt.

**Zero pulls in a batch is not automatically good.** On a platform whose own
standing conventions are mostly about checks that cannot fire and documents
that went false, a batch with no halts is more likely to mean nobody looked
than that nothing was uncertain. Both numbers are logged — pulls, and the
batch they came from — so a zero can be read as the claim it is.

**Logged either way:** a pull that turns out to have been unnecessary stays in
this file with that outcome written next to it.

| # | Date | Item | Pulled because | Resolution |
|---|---|---|---|---|
| 1 | 2026-10-06 | batch 10 item 2 — merge `constraints.json` into `db/schema_snapshot.json` as `_constraints` | **The named input does not exist.** `constraints.json` is absent from this clone (searched the whole tree, `%USERPROFILE%`, Downloads, Desktop) and from all five sibling clones. It can only be produced by running `sql/schema_snapshot_constraints_query.sql` in the Supabase editor against the live database, which I cannot do. | **HALTED, unmerged.** Everything around it verified instead: the claim is CLEAR, the snapshot's keys are `_generated_at`, `_anon_grant_baseline_2026_08_26`, `_anon_nontable_baseline_2026_08_26` and **no `_constraints`**, 439 tables, generated `2026-10-05 15:10:30+00`; and the preflight's verdict is real, measured, not inferred — see below. **Needs Michael.** |
| 2 | 2026-10-06 | batch 10 item 3 — the `.git/config` writer inside `check8_probe.py` | Pinned to ONE STEP (`dry_push(probe_env=False)`, the first dry-run push whose outgoing range resolves) but **not to one command**. The remaining suspects are inside `tools/sairn_push_gate_hook.py`'s check-12 path, which builds a base worktree and runs **generators from the base commit** with cwd inside a worktree — where a `git config` write lands in the shared config. That is a plausible mechanism and **not a measurement**. | **CONTAINED, NOT ROOT-CAUSED, and labelled as such in the file.** Config is snapshotted, reasserted after every push-shaped step, restored at exit, and backed up for the killed path; `--check-residue` / `--restore-config` repair a killed run. The arm still FAILS, deliberately, because the writer is still there. Routed to the owner of that gate. |
| 3 | 2026-10-06 | the instruction to discharge my most overdue Tier A review obligation first | **cody holds `docs/tier-a-reviews.json` under a live claim and the claim's own first line is "Tier A discharges most-overdue-first with adversarial controls"** — the identical work. Discharging into that file would be two sessions writing the same ledger in the same hour. | **HALTED. Nothing written to that file.** My nine eligible obligations are listed in the handoff with their ages so they are not lost, and the most overdue (228h, `alf_staff` + `sen_visits`) is named explicitly. Flagged rather than taken, per the standing rule that a claim overlap is stopped and handed back, not disclosed and proceeded through. |

## Pull 1 — what was verified instead, and the exact next step

The preflight's inability to compare is **measured, not assumed**:

```
python tools/capture_exit.py --status demo.status -- \
  python tools/sairn_sql_preflight.py --live db/schema_snapshot.json sql/sairnlegacy_data_schema.sql
EXIT 0 2026-10-06T16:07:59Z
```

and its CHECK CONSTRAINTS section reads, in full:

```
CHECK CONSTRAINTS
    COULD NOT CHECK      snapshot carries no _constraints key -- re-run
                         sql/schema_snapshot_query.sql to capture them
```

**The merge command is already written down** and nothing new is needed for it
— `sql/schema_snapshot_constraints_query.sql` carries it at its "HOW TO USE"
block. The whole remaining step is:

1. Run `sql/schema_snapshot_constraints_query.sql` in the Supabase SQL editor.
2. Save the single JSON cell as `constraints.json`.
3. Merge it (the one-liner in that file), **including an empty
   `{"_constraints": {}}`** — the file says why: an empty object means *asked,
   and there are none*, a missing key means *never asked*, and the preflight
   distinguishes them.
4. Re-run the preflight; the CHECK CONSTRAINTS section must report a
   comparison rather than a could-not-check.

**`constraints.json` itself is not committed** — per the dispatch, and because
it is a transcription of live database state, not a repo artefact.
