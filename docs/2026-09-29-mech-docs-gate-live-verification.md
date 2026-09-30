# `mech_docs write` gate — LIVE verification, and the two rows it left behind

**2026-09-29 (CC).** Driven against the real deployed endpoint
`https://sairn.vercel.app/api/sd-data` on licence key `MECH-PINNACLE-2026`,
after the push landed. A clean `git push` is not proof; this is.

## What was driven, and what came back

Licence key in the `Authorization` header, **no `X-SD-Auth` session token** —
which is the exact caller the change exists to refuse.

| Request | Expected | Observed |
|---|---|---|
| `mech_docs` **write** | refused | **HTTP 403** `FORBIDDEN` — *"A valid employee session is required — sign in first"* |
| `mech_docs` **read** | 200, unchanged | **HTTP 200** `{ok:true, data:[], provisioned:true}` |
| `mech_checks` **write** | 200, unchanged | **HTTP 200** `{ok:true, data:{id:…}}` |
| `mech_takeoffs` **write** | 200, unchanged | **HTTP 200** `{ok:true, …redaction:{…}}` |

**The gate is live and the scope held.** The write is closed on the licence key
alone; the read and the three sibling tables are exactly as they were. That
second half matters as much as the first — a gate that quietly took
`mech_checks` (a cheque register, and its own branch comment calls it "the sharp
one") with it would be an unreviewed decision, not a fix.

**The 403 is a real refusal, not a swallowed error.** `mech_docs read`
immediately afterwards answers `provisioned: true` with zero rows, so the table
exists and is reachable — the write was rejected at the gate, not at the
database.

## THIS CHECK LEFT TWO ROWS ON A LIVE DEMO LICENCE AND THAT IS A FINDING ABOUT THE CHECK

Verifying that `mech_checks` and `mech_takeoffs` are still writable **means
writing to them**, and both writes succeeded, as they were supposed to. There is
no `delete` action on `MECH_RECORDS` — the branch has `read` and `write` and
nothing else — so **nothing in the API can remove what this check created.**

Read back immediately afterwards, so this is a measurement and not an estimate:

| Table | Rows on `MECH-PINNACLE-2026` | Ids |
|---|---|---|
| `mech_checks` | **1** | `GATE-LIVE-CHECK-DO-NOT-KEEP` |
| `mech_takeoffs` | **1** | `GATE-LIVE-CHECK-DO-NOT-KEEP` |
| `mech_docs` | 0 | — |

**Both tables held exactly one row and it is mine.** The demo licence had none
before, so there is no risk of a removal touching real demo content — and that
is stated because it was read, not because it is likely.

The row contents are synthetic: an id that says what it is in its own name, and
`text: 'gate check'`. No personal data, no customer, no amount.

**The general form of this is already somebody's open work.** Fourth's queue
carries *"the asserted-teardown obligation to `tools/live_probe_residue_audit.py`
so a future writing probe with the same gap is caught by the convention that
already invokes it."* This is a writing probe with exactly that gap, found the
same day, from the other direction. It is named here so the two meet.

## REMOVAL SQL — Michael runs this, nothing here ran it

Scoped to the one licence key by hash and to the one id. **Run the `select`
first and read the count.** Do not run the `delete` if the select returns
anything other than the one row each.

```sql
-- 1. SELECT FIRST. Expect exactly ONE row from each, id GATE-LIVE-CHECK-DO-NOT-KEEP.
--    If either returns more, or returns a different id, STOP: something other
--    than this check wrote to these tables and the delete below is wrong.
select 'mech_checks' as tbl, entry_id, license_hash, updated_at
  from mech_checks
 where entry_id = 'GATE-LIVE-CHECK-DO-NOT-KEEP'
union all
select 'mech_takeoffs' as tbl, entry_id, license_hash, updated_at
  from mech_takeoffs
 where entry_id = 'GATE-LIVE-CHECK-DO-NOT-KEEP';

-- 2. DELETE, only after the select above returned exactly two rows.
--    entry_id is matched exactly, not by LIKE -- a LIKE here is how a cleanup
--    takes a real row that happens to share a prefix.
delete from mech_checks
 where entry_id = 'GATE-LIVE-CHECK-DO-NOT-KEEP';

delete from mech_takeoffs
 where entry_id = 'GATE-LIVE-CHECK-DO-NOT-KEEP';

-- 3. CONFIRM. Both counts must be 0. A delete that reports success and leaves
--    the row is the failure this third step exists for.
select 'mech_checks' as tbl, count(*) as remaining
  from mech_checks
 where entry_id = 'GATE-LIVE-CHECK-DO-NOT-KEEP'
union all
select 'mech_takeoffs' as tbl, count(*) as remaining
  from mech_takeoffs
 where entry_id = 'GATE-LIVE-CHECK-DO-NOT-KEEP';
```

**The `delete` is not scoped by `license_hash` on purpose, and that is the
riskier-looking choice being made deliberately:** `entry_id` is this exact
synthetic string, which appears nowhere else on the platform, and scoping by a
hash typed from a document is how a cleanup misses. The `select` in step 1
prints the `license_hash` of every matching row so the operator can see that
all of them belong to the demo licence before deleting anything.

## What this does NOT verify

- **The signed-in path was not driven live.** Arm 2 of
  `api/sd-data-mech-session-gate.test.js` drives a correct `sairnmechanical`
  session through the gate against the real handler, and that is a unit-level
  answer. Driving it live needs a real employee PIN on this licence, which this
  session does not hold. **If `SD_GATE_APP` were wrong, every signed-in
  technician would be refused and this document would not have caught it** —
  the unit arm is what covers that, and it is the weaker of the two.
- **The `mech_docs` tier row is still wrong.** It says *"no PII, PHI,
  privileged communication, or financial-account detail"* and, in the same
  sentence, that it was *"classified by the stated B rule rather than
  individually read"*. `docs/CRITICALITY-TIERS.md` is claimed by another session
  working on exactly those cells, so it is untouched here.
