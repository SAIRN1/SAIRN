# The advisory lock was doing nothing under REPEATABLE READ — on attorney trust money, and in two other places

**2026-09-15 (Hank).** Item 78's formal work established that
`pg_advisory_xact_lock` serialises *acquisition*, not the *snapshot*, and that a
guard requiring READ COMMITTED is what closes the hole. Two functions got that
guard on 2026-09-14. **Nobody asked how many others had the same shape.** Asking
it found three more, and the sharpest one moves client money.

---

## 1. The defect, and why it survives review

Under **READ COMMITTED** every statement after the lock takes a fresh snapshot,
so a caller that waited sees what the previous holder committed, and
read-decide-write is genuinely atomic.

Under **REPEATABLE READ or SERIALIZABLE** the snapshot is fixed at the
transaction's first data statement. A caller that **waited on the lock** still
reads from before the holder committed — and then writes.

**The cap over-runs, or the balance overdraws, with the lock working perfectly
the whole time.** No error. No contention symptom. Nothing in the lock's own
behaviour to review.

**That is why it survives review: the code containing the bug is correct, and
the thing that is wrong is a setting in another file.** It is one statement
away — `alter role service_role set default_transaction_isolation = 'repeatable
read'` — and that statement reads as a *hardening* change.

---

## 2. What the sweep found — 9 advisory-lock functions

| function | before | why |
|---|---|---|
| `law_check_and_insert_disbursement` | **UNGUARDED** | **attorney IOLTA trust money** |
| `law_check_and_void_deposit` | **UNGUARDED** | the hazard was *already documented in a comment* |
| `cl_rate_limit_consume` | **UNGUARDED** | shared third-party token, 4/minute |
| `sairn_ai_rate_limit_consume` (×2 current files) | guarded 2026-09-14 | — |
| `sairnlaw_rate_limit_consume` | guarded at birth | — |
| `sairn_circuit_breaker_step` | **SAFE** | `SELECT … FOR UPDATE` |
| `rf_allocate_invoice_number` | **SAFE** | `UPDATE … RETURNING` |
| `sairn_ai_rate_limit_consume` in `sairn_ai_usage_columns_2026-09-02.sql` | **SUPERSEDED** | see §4 |

### 2.1 The sharpest one is trust money

`law_check_and_insert_disbursement` locks on (licence, client), then calls
`law_client_balance()` — an aggregate SUM over `law_trusttx` — then checks
`p_amount > v_balance`, then inserts.

**Under REPEATABLE READ, two concurrent disbursements against one client each
sum a balance from before the other committed, each pass the sufficiency check,
and both insert.** An overdrawn client trust ledger. On an IOLTA account that is
a **bar-reportable event**, not an internal accounting discrepancy.

The author reasoned carefully about concurrency here — the retry-idempotency
branch and the id-collision branch are both thought through. The snapshot was
simply not part of the model.

### 2.2 The second one had the hazard written down and unenforced

`law_check_and_void_deposit`, 100 lines below, carried this comment against its
post-lock re-select:

> *"relies on PostgREST/Postgres's default READ COMMITTED isolation … if this
> connection pool were ever changed to REPEATABLE READ or SERIALIZABLE, this
> re-select would silently return the same pre-lock tuple and this guard's whole
> point would quietly stop working with no error anywhere."*

**That is exactly right, and it is prose.** A hazard that is known, written down
and left unenforced is the most common defect shape this platform records — and
it is presumably why the *sibling* function above it had the same dependency with
no comment at all. Both are now mechanical.

### 2.3 And the two that are safe are classified, not suppressed

`SELECT … FOR UPDATE` and `UPDATE … RETURNING` both raise
**serialization_failure (40001)** under REPEATABLE READ rather than silently
reading stale. **They fail loud, which is the opposite of this defect.**
Reporting them alongside it would be worse than missing them: a checker that
flags the two correct patterns is one whose findings get read as noise, and this
repo's own record is that an over-reporting first draft becomes a column people
switch off.

---

## 3. Re-qualified, not copied

Cross-domain discipline 7 — *byte-identical is not safe-in-context*. The
mechanism is the same three lines in all three; **what happens when it fires is
not**, and it differs in both directions:

- **`api/_lib/ai-rate-limit.js` ALLOWS the call when its RPC errors** — a
  counting outage must not take down every AI feature.
- **`api/_lib/courtlistener.js` REFUSES.** Read out of the file, not assumed:
  `consumeAtomic()` falls back to the legacy racy path on a **404 and only a
  404**, and throws on everything else (`courtlistener.js:62-63`). So a raise
  here does **not** degrade to the racy path — it stops the citator. That is the
  intended direction for a third party's revocable, shared token, and it is
  stated so nobody discovers it during an outage.
- **The trust functions raise on a money write.** A new refusal path, recorded as
  a review obligation in §5 rather than assumed harmless.

---

## 4. The stale-migration hazard, which is invisible

`create or replace` means **re-running an older migration file silently reverts
a guard**, and nothing about running a migration tells you it is older.

`sql/sairn_ai_usage_columns_2026-09-02.sql` still contains a guard-less
definition of `sairn_ai_rate_limit_consume`, which was guarded on 2026-09-14/15
in two other files. Running that file today — for its *columns*, which is what
its name advertises — would quietly undo the fix. The checker reports this as a
separate **SUPERSEDED** class because it is not the same finding as an unguarded
function and needs a different action.

---

## 5. The checker, and the gate that could not see this change

`tools/advisory_lock_isolation_check.py`, report-only, registered. 31-arm probe.

**Its blind lock runs on every run, not only under `--self-check`** — a checker
that has silently stopped classifying must not then report the repository clean.
The teeth arms prove both directions: a classifier that can never say UNGUARDED
**and** one that always says it are both caught, and exit **2 (could not run)**
rather than 0.

**Two of the six fixtures exist because they caught real bugs in the first draft,
before it ever touched `sql/`:**

- **The comment trap.** The stripper treated a `$$` body as opaque — exactly
  backwards, because in plpgsql *every* function comment lives inside `$$`. A
  body whose only mention of the guard was in a `--` comment classified
  **GUARDED**. On files like these, which carry long prose blocks naming
  `transaction_isolation`, that single bug would have reported the whole
  platform clean.
- **`UPDATE … RETURNING … INTO`** is a read *and* a write in one statement and
  contains no `select`, so asking "are there reads?" first sent the
  roofing-shaped function to `NO_RMW` — a harmless verdict reached by wrong
  reasoning, which stops being harmless the next time the rule moves.

### The Tier A review gate cannot see this change, and that is by design

`tools/tier_a_review_gate.py` **excludes `sql/`** from its scan. So a change to a
Tier A *function* — in the one file type where Tier A tables are defined and
operated on — can never raise an obligation. The exclusion has a reason (every
schema file names its tables constantly), and I did not change it; **but the
consequence is recorded here rather than left to be rediscovered.** The review
obligation is written into the open-work row instead, where a human reads it.

---

## 6. Not established

- **THE REPOSITORY IS NOT THE DATABASE.** Every guard here is a file. **None of
  them does anything until the migration is re-run**, and I have no route to the
  deployed database to confirm any of it. `cl_rate_limit_consume_fn_2026-09-04.sql`
  and `sairnlaw_trusttx_functions.sql` both need re-running; both use `create or
  replace`, so re-running is safe.
- **Nothing is exploitable today.** Nothing on this deployment sets a
  non-default isolation level *as far as can be seen from here* — which is a
  statement about what I could check, not about what is true.
- **The verification that proves the fix is the one that sets the isolation
  level**, and it is written into each file's footer: open a transaction, `set
  transaction isolation level repeatable read`, call the function, and expect
  **ERROR 25000**. A jsonb row there means the guard is not installed, whatever
  the repository says.
- **Three of the seven queued items were already built** and are named in the
  index row rather than rebuilt: item 88's Tarjan articulation points
  (`tools/dependency_graph.py`, iterative Hopcroft-Tarjan, plus cut-pairs), item
  90's three anti-pattern shapes (`tools/shape_antipattern_check.py`, running
  with real findings), and item 65's restore-test (`nightly-backup.yml` restores
  the dump it just took and runs a coherence check against it).
