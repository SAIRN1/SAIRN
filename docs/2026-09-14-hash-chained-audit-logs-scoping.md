# Item 35 — hash-chained audit logs, and the two tamper modes that are already closed

**Written 2026-09-14 (Fourth).** Scoped before anything is built, because the
measurement moved the answer twice: once on what a chain would actually defend
against here, and once on whether the obvious implementation can survive this
platform's own concurrency.

---

## What exists, measured

There is one shared server-side audit writer, `api/_lib/audit.js`, called from
**7 sites across 7 files** (`alf-auth`, `bld-auth`, `dnt-auth`, `grd-auth`,
`law-auth`, `leg-auth`, `mech-auth` and the legal endpoints). It writes to one of
**three allowlisted tables** — `sairnlaw_audit_log`, `sairncode_audit_log`,
`stonedesk_audit_log`. One writer, three tables, and the table name is
allowlisted rather than interpolated.

**Nothing verifies any of them. There is no verifier in `tools/` or `tests/` for
any audit table on this platform.**

Separately, and NOT the same problem, two client-side trails: `sv_audit_log`
(SAIRNvet's dosing trail, whose retention and retrievability are item 39) and
`alf_op_audits` (SAIRNcare). Those are written from a browser, so a chain
computed there says only what that browser chose to say.

---

## The finding that reframes the item: two of the three tamper modes are already closed

All three schemas carry the same grant, checked in each file rather than assumed
from one:

    grant select, insert on public.<table> to service_role;

**No UPDATE. No DELETE. On all three.**

| Tamper mode | Status today |
|---|---|
| Alter a row in place | **Already impossible through the API** — no UPDATE grant |
| Remove a row | **Already impossible through the API** — no DELETE grant |
| **INSERT a row that was never true** | **OPEN** — and this is the whole of item 35 |

The writer sends `license_hash`, `employee_id`, `role`, `event_type` and
`detail`, and lets `created_at` take its `default now()`. But the grant is
table-level, so it covers every column: **anyone holding the service key can
insert a row with any `created_at` they like, under any `license_hash` they
like.** A forged sign-in, backdated into last month, under another practice's
licence, is a single INSERT and nothing today would notice.

So item 35 is not "make the audit log tamper-evident". It is **"close the one
hole the grant leaves"**, and saying it that way matters because the other two
modes are already prevented BY CONSTRUCTION — which is a stronger guarantee than
any chain can offer, and it should not be re-bought with a mechanism that only
detects.

**What a chain cannot do here, stated rather than left to be assumed:** anyone
with direct database access — the Supabase dashboard, a superuser — can rewrite
rows and recompute a whole chain over them. Detection only binds someone limited
to the API. An external anchor is the only thing that changes that, and it is out
of scope until somebody decides where an anchor would live.

---

## The design finding: the obvious chain forks, and here it cannot be repaired

A per-row chain stores `hash(this row + previous row's hash)`. It needs the
previous row's hash, which means **a read before every write**.

Two problems, and the second is decisive:

**1. It puts a read on a path whose contract is that it must never block.**
`api/_lib/audit.js` is best-effort by design — its header says a failed audit
write must never block or fail the operation being audited, and every one of the
7 callers ignores the return value. A read-then-write doubles its round trips and
adds a failure mode to a function that is deliberately allowed to fail quietly.

**2. CONCURRENT WRITES FORK THE CHAIN, AND THE INSERT-ONLY GRANT MEANS NOTHING
CAN REPAIR IT.** Two audit writes in flight at once read the same previous hash
and both chain onto it. On a normal database you would fix the loser with an
UPDATE. **Here there is no UPDATE grant** — that is the same property this
document just praised — so a fork is permanent, and every verification from that
moment on reports a broken chain.

This platform has already paid for exactly this shape once: `anon-rate-limit.js`
was an in-process counter on a horizontally scaled runtime, and concurrency —
the very condition it existed for — is what defeated it. A chain that breaks
under concurrent load would produce **false tamper alarms on an audit log**,
which is worse than no chain: a detector that cries wolf on a correct record
teaches everyone to ignore it, and the one real alarm arrives into that habit.

---

## The design that fits: periodic checkpoints, not per-row chaining

Compute nothing on the write path. Instead, on a cadence, hash **every row up to
a closed time window** and store that digest in its own append-only checkpoint
table:

    checkpoint(window_end, row_count, digest, prev_digest)

- **No read-before-write and no cost on the hot path.** `api/_lib/audit.js` does
  not change at all.
- **No fork.** The window is closed before it is hashed, so concurrency inside
  the window is irrelevant.
- **It detects the open mode.** A row inserted retroactively into any window that
  has already been checkpointed changes that window's digest, and the chain of
  `prev_digest` values makes a wholesale recomputation of the checkpoint table
  detectable too.
- **It states what it cannot see:** an insertion into the CURRENT, not-yet-closed
  window is invisible until that window closes. That is the residual, and it is
  bounded by the cadence rather than open-ended.

This is the shape transparency logs use, and it is chosen here for the specific
reason that it is the only one of the two that survives an INSERT-only grant.

---

## Sizing

| # | Work | Size |
|---|---|---|
| 35a | `sql/audit_checkpoint_schema.sql` — one table, INSERT+SELECT grant only, same treatment as the three it protects | **S** |
| 35b | The checkpointer: hash a closed window per audit table, chained on the previous digest. Runs on a cadence, not on the write path | **M** |
| 35c | **The verifier, which is the half that makes the rest real** — recompute every closed window and report which one first disagrees. A chain nobody verifies is a column of hashes | **M** |
| 35d | A control that plants a backdated INSERT into a checkpointed window and demands the verifier find it, plus the other direction on an untouched table | **S** |

**35c and 35d are not optional extras.** Building 35a and 35b alone produces a
tamper-evident log that nobody has ever seen detect tampering — the same state
`checkblocks.py` sat in for months while always exiting 0.

**And one decision belongs to Michael before 35b, because it is not technical:**
what the cadence is, and **who reads the verifier's answer**. A detector with no
named reader is the `console.warn` problem one layer up — item 39 found the
idless-record warning going to a console nobody in a clinic reads. The cadence
sets the size of the invisible window; the reader is what turns a detection into
a response.

---

## What this scoping does NOT claim

- **No live tampering is alleged or has been looked for.** Nothing in any
  production audit table was read. The INSERT hole is derived from the grant and
  the writer, not from evidence that anyone used it.
- **The client-side trails are out of scope.** `sv_audit_log` and
  `alf_op_audits` are written from a browser; chaining them would attest to what
  a browser chose to send, which is a different and weaker claim than this
  document is about. Their problem today is item 39's.
- **Nothing was built or changed.**
