# Where the server can enforce SAIRNfreedom's three officer guards — DESIGN ONLY

**NO CODE IN THIS BATCH.** Item 6 of hank b5 is explicitly design only; the
implementation waits on Michael's answer about a SAIRNfreedom role matrix (b4
Q3). This document exists so that when the answer arrives the work is a
transcription rather than a re-derivation.

**Line numbers are at `e04c2c21` and they MOVED since the b5 brief was
written.** The brief cites `:2849`, `:2860-2869`, `:2878-2885`. Adding
`sfHydrateAfterSignIn()` in b4 pushed that region down by ~67 lines. Current:

| guard | brief said | actually at | what it does |
|---|---|---|---|
| `activeProvisioners()` | `:2849` | **`:2916-2918`** | officers that are `active` AND whose `capability` is in `PROVISIONING_CAPS` |
| SPEC 1c, last-provisioner refusal | `:2860-2869` | **`:2927-2940`** (`sfToggleOfficer`) | refuses deactivating the last active provisioner |
| sole-holder refusal | `:2878-2885` | **`:2942-2956`** (`sfAddOfficer`) | refuses a second active holder of a `sole:true` capability |

Verified by `grep -n 'function activeProvisioners\|function sfToggleOfficer\|function sfAddOfficer'`,
not by trusting the brief. **Re-derive them again before writing code** — this
table will go stale the same way.

---

## What is already true, so the design does not overstate the problem

`sf_officers` has been in `SD_SESSION_GATED` and `SD_GATE_APP` since
`56e040c3`, so a **bare licence key** can no longer write the roster. What
remains is that **any signed-in SAIRNfreedom session of any role** can, and all
three guards above run **only in the browser**. A write that does not come from
this page — curl with a stolen session, a second tab with a modified script, a
future integration — is a write past all three.

`sf_officers_provisioning_bypass_repro.py` exits 0 FIXED and still prints
`role/capability check present in that write block: False`. That is the gap this
design closes.

**And the severity has a ceiling, which matters for sequencing.** The server's
own provisioning gate does **not** read this table: `api/sf-auth.js:328` takes
`caller.role` from the **signed session token** and checks it against
`PROVISIONING_ROLES`. A forged officer row **mints no credential**. The finding
is integrity of the governance record and of the trapdoor guard — Tier A on
integrity per `docs/CRITICALITY-TIERS.md:365` — not privilege escalation.

---

## The three guards are not the same KIND of rule, and that drives the design

This is the part worth getting right before any code.

### Guard A — `activeProvisioners()` is a DERIVED READ, not a rule

It is a filter over the roster. There is nothing to enforce; it is the input to
the other two. The server needs the same derivation available to it, and that
is all.

### Guard B — SPEC 1c is a WHOLE-TABLE INVARIANT

"At least one active provisioner, or zero officers" is a property of the **set**
of rows, not of the row being written. A per-row handler cannot evaluate it
without reading the rest of the table first. Two safe end states and only two —
the same rule `tools/employee_auth_guard_check.py` already enforces on the SQL
side for credential rows, which is the precedent to copy rather than a new idea.

### Guard C — the sole-holder refusal is a UNIQUENESS CONSTRAINT

"At most one active holder of a `sole:true` capability" is a partial-unique
index in disguise. `CAPABILITIES` at `sairnfreedom.html:2301` carries the
`sole` flag; `post.govern` is the only `sole:true` entry today.

**So B and C want different mechanisms, and that is the finding of this
document.** Shipping both as handler code would put a set-invariant and a
uniqueness constraint in the same `if` block, which is how one of them ends up
only approximately enforced.

---

## Recommended placement

### C — the database, as a partial unique index

```
-- NOT RUN, NOT PART OF THIS BATCH. For Michael, after the role-matrix answer.
create unique index if not exists sf_officers_one_sole_holder
  on public.sf_officers (license_hash, (data->>'capability'))
  where (data->>'active')::boolean is true
    and (data->>'capability') in ('post.govern');
```

**Why the database and not the handler:** a uniqueness rule enforced by
read-then-write loses to two concurrent writes, and the officer roster is
exactly where two people act at once (an outgoing and an incoming Commander).
The handler would have to do a compare-and-swap; the index does it for free and
cannot be bypassed by a future second write path.

**The cost, stated:** the capability list is then in TWO places — `CAPABILITIES`
in the page and the index predicate in SQL. That is the
two-lists-that-must-agree shape this platform keeps paying for
(`SD_SESSION_GATED`/`SD_GATE_APP`). **Mitigation: a test that reads `sole:true`
out of `sairnfreedom.html` and asserts the index predicate names exactly those
ids** — the same shape as `api/audit-shape-pinning.test.js`. Without that test
this recommendation is worse than the status quo, because a new `sole:true`
capability would be silently unenforced while looking enforced.

### B — the handler, in `api/sd-data.js`'s `sf_officers` write branch

A set invariant over `active` and `capability` needs the current table, so it
belongs where the table can be read before the write. The shape to copy is the
one `dnt_appointments` already uses (`api/sd-data.js:~15490`): read the stored
state, decide against **the server's record**, never the client's claim, and
fail **closed** on an unreadable pre-read.

Sketch, deliberately not code:

```
if (resource === 'sf_officers' && action === 'write') {
  // 1. pre-read the roster for this licence           -> 502 if unreadable
  // 2. compute the roster AS IT WOULD BE after this upsert
  // 3. REFUSE 409 if the result has officers and zero active provisioners
  // 4. ...and refuse the same way on a DELETE-equivalent, if one ever exists
}
```

**The three things that will go wrong if this is written carelessly:**

1. **The write is an UPSERT, so step 2 must merge, not replace.** Computing the
   invariant against the payload alone passes a write that deactivates the last
   provisioner by id without mentioning capability.
2. **Fail CLOSED on the pre-read.** An unreadable roster must be a 502 that
   changes nothing, not a write that proceeds without the check — PR §1.11.
3. **Zero officers is a SAFE end state and must stay writable.** A naive
   "always require one active provisioner" bricks a post trying to start over,
   which is the opposite of the trapdoor this guard exists to prevent.

### A — nowhere new

Derived inside the handler for step 2. No endpoint, no stored column.

---

## What this design does NOT decide, and must not

**Who may write `sf_officers` at all.** That is Michael's role-matrix question
and it is a different question from either invariant: B and C must hold *no
matter which roles are allowed to write*. If the answer later restricts writes
to `post.govern`, both guards are still required — a Commander can deactivate
the last provisioner as easily as anyone.

So the correct implementation order is **B and C first, role restriction
second**. They are independent, and B and C are not blocked on the answer.

**Whether the client guards come out.** They should **stay**. They give an
immediate, specific refusal with the post's own org-type title in it; the server
gives a 409 a page has to translate. Removing them would make a correct refusal
read as a server error. The client guards become a convenience; the server
becomes the boundary.

---

## Open, and not mine to close

* **`sf_officers` has no dedicated SQL schema file** that this index could be
  appended to — the roster lives in the generic `sf_*` jsonb blob table. The
  index predicate above assumes `data->>'capability'` and
  `data->>'active'`, read off `sairnfreedom.html`'s `sfAddOfficer()` write at
  `:2952`. **Confirm against the real table before running it**; this was read
  from the client, not from the database.
* **Not proven live, and not provable today.** The whole `sairn.vercel.app`
  deployment answers **402 "Deployment Paused"** on every path as of
  2026-10-13, so no behaviour described here was driven against the real
  endpoint.
