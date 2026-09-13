# Scoping: a witnessing lock on irreversible writes

**Written 2026-09-13 (Fourth). NOTHING HERE IS BUILT.** Scoped first, with a
real size, and every figure names the command that produced it.

The ask, from the electronic-witnessing research: not a checker that flags and
not a gate that blocks a push, but a **hard workflow lock** — the next write
cannot fire at all until the verification step for it completes, the way an
embryology system will not let the next handling step begin until the current
one is scanned. The research finding that motivates it is that even
*independent double-review* has a measured, non-zero failure rate in domains
where a mistake cannot be undone. That is an argument for a lock, and equally an
argument against claiming a lock makes anything safe. Both halves are carried
below.

---

## First: what "irreversible" has to mean, or this scopes everything

"Important" is not the test. Almost every write on this platform is important.
The test used here:

> **A write is irreversible-if-wrong when the state it replaces, or the
> assertion it makes, cannot be restored or withdrawn by the product after the
> fact.**

That splits into four classes, and only one of them is open.

### Class A — APPEND-ONLY BY DESIGN · **the real target**

A wrong row can never be removed *because removal is what the design forbids*.
A correction is a SECOND row and the wrong one stands forever. This is not a
gap to close — it is the correct design for a regulated record, and it is
precisely why the verification has to happen BEFORE the write.

Declared in the registry files themselves, read rather than guessed
(`grep -rn "append.only" api/_resources/`):

| App | Append-only resources named in its own registry |
|---|---|
| `sairnvet` | `sv_audit_log` (the dosing audit trail) |
| `sairndental` | `dnt_payments`, `dnt_charges`, `dnt_credentials`, `dnt_vendor_orders` |
| `sairnroofing` | `rf_certifications`, `rf_claim_photos`, the signed-document chain, `rf_proposals` |
| `sairncare` | the signals table, the routing-decision log, `alf_staff_credentials` |
| `sairnmechanical` | `mech_credentials` |

**And the sharpest single instance is not in that list, which is the point.**
`sv_controlled` — SAIRNvet's controlled-substance register, described in its own
registry file as *"the controlled-substance register (DEA-relevant)"* — comes
out of `python tools/removal_path_check.py --burn-down` as **Tier A with no
removal path**. Nobody declared it append-only; it simply cannot be unwound.

### Class B — Tier A with no removal path · already a tracked burn-down

**53 resources**, from the same command. Distinct from Class A: nobody *decided*
these are permanent, the product just has no way to remove one. That is an
existing open row with an owner-less burn-down order, and it is a removal-path
problem rather than a witnessing problem. Not in scope here.

### Class C — whole-record upsert over a live row · **largely CLOSED**

Measured across `api/`: **161 `resolution=merge-duplicates` sites in 33 files**,
of which **74 carry a whole caller-supplied record** (`data: payload`, `record`)
across 7 files — `bridge.js`, `legal-citator.js`, `legal-deadlines.js`,
`sd-data.js`, and three SAIRNdental endpoints. There is no general versioning
table behind them, so the prior blob is not recoverable from the server.

**It is nevertheless not the open class.** Every app that merges server rows
into local state now carries a per-record `_m` stamp and resolves on it
(`1e0d4527`), and that is all four of them:

    sairndental.html  sairngrounds.html  sairnscape.html  stonedesk.html
    apps with a client merge: 4, of which stamped: 4, UNGUARDED: 0

A wrong server write no longer destroys a newer local edit. Recording this
because the merge-by-id overwrite is one of the two incidents that prompted the
ask, and **the honest answer is that its class was closed three hours before
this was scoped.** A lock built for it would be a lock on a fixed bug.

### Class D — fabricated records reaching a live store · **swept, and held**

The SAIRNvet demo-data leak, the other prompting incident. Irreversible in a
different way: the rows are deletable in principle, but once mixed with real
ones nobody can afterwards say which were fake. Swept across all five apps whose
`st()` carries a backup hook on 2026-09-10 and held by
`tests/seed_never_syncs_platform.js` with a negative control against the true
pre-fix `sairnvet.html`.

**Worth keeping in view rather than closing:** a lock on Class A writes would
also have caught this one, because a fabricated controlled-substance row is
exactly a write nobody verified.

---

## THE BLOCKER, and it is the finding of this scoping

**SAIRNvet has no per-employee identity at all.** Fifteen apps ship a
per-employee auth endpoint —

    api/*-auth.js : alf bld dnt grd law leg mech rf sb sc scp sd sd-sub sdn sen

— and `sv` is not among them. There is no `sv-auth.js`, and no
`sv_employee_auth` table anywhere in `sql/` or `api/`
(`grep -rln "sv_employee_auth" sql/ api/` returns nothing). SAIRNvet writes
through `api/sd-data.js` keyed on `license_hash` and `app_id: 'sairnvet'` only.

So the app holding the DEA-relevant, append-only, Tier A, no-removal-path
controlled-substance register is **the one app that knows which PRACTICE is
writing and not which PERSON.**

A witnessing lock needs an identity to witness with. On SAIRNvet there is
nothing to bind a witness to, and a lock that records "the practice confirmed
it" is theatre. **This is a hard prerequisite, not a detail**, and it is the
first thing to fix whatever is decided about the lock itself.

---

## What the lock would be

Two-phase, server-enforced, and a REFUSAL rather than a warning:

1. `witness_request` returns a single-use, short-lived token bound to a **hash
   of the exact record about to be written** and to the identity of the
   witness. Binding to the content is the whole mechanism — a token bound only
   to "a write is coming" can be spent on a different record.
2. The write endpoint REFUSES without a valid, unspent token whose hash matches
   the body it was handed.

Three properties it must have, each already learned here the hard way:

- **Checked against the table, never an in-memory map.** This runs serverless;
  a second request is a second process. `api/sairndental/public-complaint-submit.js`
  records exactly this.
- **A failed witness check REFUSES rather than writing unchecked** — a failed
  check is not the same answer as "verified". Same rule as that endpoint's 503.
- **The token is single-use.** A reusable token is a witness who signed once for
  everything that followed.

---

## Size

| Piece | Size | Why |
|---|---|---|
| **Prerequisite: SAIRNvet per-employee auth** | **M** | Not novel — 15 apps ship it, `api/_lib/auth.js` is shared, and `sairn-employee-auth-scaffold` exists precisely so a sixteenth is assembled rather than hand-written. It carries the credential-deactivation lifecycle with it |
| **The lock, on `sv_controlled` alone** | **M** | One resource, two endpoints, one table for spent tokens, plus the control that plants an unwitnessed write and requires a refusal |
| **Extending to all of Class A (~15 resources, 5 apps)** | **L** | And it is a PRODUCT decision before a technical one — see below |

The first two are sequential; the third should not start until the first lock
has been lived with.

---

## The decision this cannot take

**Single-operator confirm, or a genuine second person?**

The research finding is that *independent double-review still fails at a
measurable rate*. Two things follow, and they point in opposite directions:

- A single-operator confirm step is **much weaker** than a second witness — the
  person who made the error is the person confirming it. It is cheap, needs no
  staffing assumption, and would still have caught a demo-seed write.
- A true second witness is the thing the research is actually about, and it
  costs a second person present at every controlled-substance entry. On a
  one-vet practice that is not a workflow, it is a blocker.

**That is a staffing and product call, not a code one**, and the code differs
substantially between them: a second-person lock needs a second live session,
a roster of who may witness, and a refusal when only one person is logged in.

A third option worth naming rather than leaving implicit: **lock on the
single-operator confirm now, record the witness identity in the token, and
leave the second-person requirement as a per-licence setting.** That gets the
mechanism built and the schema right without deciding the staffing question for
every customer.

---

## What this scoping deliberately did not do

No tool was written and no endpoint was changed. It also did not extend the
definition of "irreversible" to cover Class B — 53 Tier A resources with no
removal path is a real open row, and folding it in here would have turned a
scoped lock into a platform-wide rewrite on the strength of a word.
