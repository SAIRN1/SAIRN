# SAIRNvet's credential fix is written and cannot be pushed — and the schema snapshot is stale

**Written 2026-10-05 (Fourth). Two blockers, one of which is a finding about
the snapshot rather than about SAIRNvet.**

---

## 1. The file

`sql/restore_sairnvet_demo_pin_2026-10-05.sql` is written, **untracked**, and
preflight-clean against the declared schema (0 findings). It restores the one
demo credential that is actually broken, carries the PR 3.4 recoverability
guard inside a transaction, and prints no PIN.

**It replaces `sql/restore_demo_pins_2026-09-29.sql`, which must not be run.**
That file writes two credentials and its SAIRNbiz row encodes the PIN
`docs/2026-09-03-demo-credentials.md` marks **DEAD 2026-09-25**, while the live
SAIRNbiz credential works — driven 200 again today. Running it would cause on
SAIRNbiz the outage it was written to repair on SAIRNvet.

**Root cause of that bad row, which matters more than the row:**
`.demo-credentials.local.json` `apps[1].pin` **still holds the dead SAIRNbiz
PIN.** The 2026-09-29 header was truthful about where its hashes came from —
the value moved *on the server* and the local file was never updated. **The SQL
was a faithful copy of a stale source.** Fix the local file before anyone
regenerates from it, or the defect comes back.

## 2. Blocker A — I cannot run it

No database access in this clone: no `SUPABASE_*`, `POSTGRES_*` or
`DATABASE_*` in the environment, and the only SQL-adjacent tools are a
preflight linter and a column-existence check. Neither executes anything.

SAIRNvet is recoverable **only** by direct database access — `bootstrap` is
permanently refused on that licence because it deliberately does not filter on
`active`.

## 3. Blocker B — THE PUSH GATE REFUSES IT, AND THE GATE IS WORKING FROM A STALE SNAPSHOT

```
Blocked: this push contains SQL naming a table or column that the live
database does not have.
  restore_sairnvet_demo_pin_2026-10-05.sql: MISSING_TABLE sairnvet_employee_auth
```

`db/schema_snapshot.json` holds **ten** `*_employee_auth` tables —
`grd`, `sairnbuild`, `sairncare`, `sairncode`, `sairndental`, `sairndesign`,
`sairnlaw`, `sairnlegacy`, `sairnmechanical`, `sairnroofing` — and **not**
`sairnvet_employee_auth`.

**Live behaviour says the table exists.** Driven today against
`https://sairn.vercel.app/api/sv-auth`:

| attempt | response |
|---|---|
| login, documented PIN | **401 INVALID_CREDENTIALS** |
| …after repeated failures | **429 LOCKED** |

`docs/2026-09-03-demo-credentials.md` uses exactly this inference in the
opposite direction: it records that `/api/sv-auth` once answered **503
NOT_PROVISIONED** while `sairnlegacy` and others answered INVALID_CREDENTIALS,
*"so their auth tables exist and SAIRNvet's does not"*. SAIRNvet now answers
401, not 503.

**The 429 is the stronger half.** `LOCKED` requires reading a stored
`failed_attempts` / `locked_until` off a row. A constant-time dummy path can
manufacture a 401 with no table; manufacturing a per-subject lockout counter
without one is much harder.

**STATED AS EVIDENCE, NOT PROOF.** I have not seen the table. The honest
reading is that the schema snapshot is **stale** with respect to SAIRNvet —
the migration was very likely applied after the snapshot was taken — and the
gate is correctly refusing on the information it has. Its own message says so:

> *If the object really does exist because a migration was applied after that,
> regenerate the snapshot rather than overriding the gate.*

**No override was used.** `SAIRN_SEED_GATE` stayed on and the SQL was dropped
from the commit instead.

## 4. What someone with database access needs to do, in order

1. **Regenerate the snapshot** — run `sql/schema_snapshot_query.sql` in the
   Supabase editor and save the JSON over `db/schema_snapshot.json`. This
   unblocks the push gate for any SAIRNvet SQL, not just this file, and it is
   worth doing regardless of the credential.
2. **Run `sql/restore_sairnvet_demo_pin_2026-10-05.sql`** — section 1 SELECT
   first, so you can see which of the three states the row is in before
   changing it.
3. **Confirm with `python tools/demo_credentials_check.py`.** The SQL proves
   the row changed; only a sign-in proves the credential works.
4. **Then SAIRNvet's third of the click-through audit can run** — it is the
   last third, StoneDesk (74/74) and SAIRNbiz (20/20) having come back clean on
   2026-09-26.
5. **Fix `.demo-credentials.local.json` apps[1].pin** so the next person to
   generate credential SQL does not reproduce the dead-PIN row.

## 5. Also left alone

`sql/restore_demo_pins_2026-09-29.sql` is **still untracked and still
dangerous**. I did not delete it — it is another session's file — but nothing
should run it in its current form.

## 6. One thing I caused

Two probe attempts pushed SAIRNvet's failed-attempt counter over the lockout
threshold, so it answers 429 rather than 401 for a while. Nothing usable was
lost — there is no working PIN to lock out — and the UPSERT in §1 resets
`failed_attempts` and `locked_until` for exactly this reason. But the next
person to probe will see 429, and that is my doing rather than a new fault.
