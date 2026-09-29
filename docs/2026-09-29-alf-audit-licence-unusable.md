# `ALF-AUDIT-2026` is live and no session can sign into it

**2026-09-29 (Hank).** Item 3 of queue22 asked for the owner and non-management
accounts to be bootstrapped through the product's own endpoints and for
`tools/alf_facility_role_gate_live_probe.py` to be re-run with real sessions.
**It cannot be, and the blocker is not the licence.**

## What was verified live, and it is good news

| Probe | Result |
|---|---|
| `POST /api/alf-auth` `{action:check_license}`, `Bearer ALF-AUDIT-2026` | **`200 {"ok":true,"active":true,"app_id":"sairncare"}`** |
| the same, with `SD-AUDIT-2026` | `403 LICENSE_WRONG_APP` — correct, that is StoneDesk's |
| `SV-AUDIT-2026` | `401 INVALID_LICENSE`, on `/api/sv-auth` too — **correct, see below** |
| `LAW-`, `SC-`, `MECH-`, `RF-AUDIT-2026` | `403 LICENSE_WRONG_APP` against this endpoint — each is live on its own app |

So `sql/audit_license_seed_2026-09-28.sql` has been run and the audit licences
are real.

**`SV-AUDIT-2026` answering 401 is NOT a finding, and I checked before saying so.**
It is absent on purpose: the seed file's own line 58 says *"SV-AUDIT-2026 IS
DELIBERATELY NOT HERE. No probe needs it"*, and `tools/audit_licence.py` records
that a measurement caught a tool naming it. Driving `/api/sv-auth` directly
confirms both halves — `SV-AUDIT-2026` → `401 Unknown license key`, while
`SV-PINNACLE-2026` → `200 {"app_id":"sairnvet"}`, so the endpoint is live and it is
the key that does not exist. Recorded here only because an unexplained 401 in a
sweep looks like a gap, and the next reader should not spend the same ten minutes.

## The blocker

```
POST /api/alf-auth {action:bootstrap, employee_id:..., pin:...}
  -> 409 ALREADY_PROVISIONED
     "This facility already has employee credentials set up — use action:setup instead"
```

`bootstrap` works **only** while the licence has zero credential rows.
`ALF-AUDIT-2026` has one: **`zz-audit-owner`**, created by Fourth on 2026-09-29
and — per `docs/2026-09-29-alf-incidents-live-verification-and-residue.md` —
**left active on purpose**, precisely so the licence would stay usable:

> `zz-audit-owner` is **left active deliberately**. `bootstrap` works only while a
> licence has **zero** credential rows, so deactivating the sole owner would make
> the audit licence unusable for the next live verification with no way to recover
> it through the product.

**That reasoning is right and the outcome is the opposite of what it intended.**
The account is active, and **its PIN is recorded nowhere** — not in that document,
not in `docs/2026-09-03-demo-credentials.md`, not in any tracked file. So:

* `bootstrap` refuses — the licence is provisioned.
* `login` refuses — `401 INVALID_CREDENTIALS`, because no session here has the PIN.
* `setup` needs an owner session, which needs `login`.
* the role-gate probe needs sessions, which need `setup`.

**Every door is correctly locked and nobody has the key.** The licence is live,
active, and unusable by any session other than the one that provisioned it.

## This is a named failure, one level up from where it is usually caught

The push protocol's §3.4 requires that SQL writing credential rows carry a
**recoverability guard — two end states are safe and only two.** The *rows* here
are fine. What is not recoverable is the **ability to use the licence at all**,
and that is not a property any SQL guard was looking at.

`docs/2026-09-03-demo-credentials.md` opens by describing this exact situation in
its first paragraph — *"owner account bootstrapped from an earlier session and I
don't have those PIN"* — and that document exists because of it. The lesson was
written down for demo licences and the same trap was walked into on an audit
licence three weeks later, because nothing mechanical connects "you bootstrapped
a provisioning account" to "record where its PIN lives."

**A credential that only one session can use is a single point of failure with
no alarm on it.** The session that holds it is a process that will end.

## Two ways to unblock, and the second is better

### 1. Fourth records where the PIN lives (preferred, costs nothing)

Fourth's session minted it. If it is still recoverable from that session's own
working notes, the fix is one line in
`docs/2026-09-29-alf-incidents-live-verification-and-residue.md` naming **where**
it is held — not the value. Nothing live has to change.

### 2. Michael removes the row, returning the licence to `bootstrap`-able

**Select first.** Nothing below is scoped by anything but the licence key and the
app, and the `select` tells you what the `delete` will take.

```sql
-- 1. VERIFY. Expect exactly ONE row: zz-audit-owner, active = true.
--    If it returns more than one, STOP -- the delete below would take them all
--    and this document's premise (a single provisioning account) is wrong.
select e.employee_id, e.role, e.active, e.created_at
  from public.sairncare_employee_auth e
 where e.license_hash = (select l.license_hash
                           from public.license_keys l
                          where l.key = 'ALF-AUDIT-2026'
                            and l.app_id = 'sairncare');

-- 2. REMOVE the provisioning account, and ONLY on the audit licence.
--    Scoped through the licence key rather than a pasted hash, so a mistyped
--    hash cannot reach a customer's roster. This is the one statement that
--    changes anything.
delete from public.sairncare_employee_auth
 where license_hash = (select l.license_hash
                         from public.license_keys l
                        where l.key = 'ALF-AUDIT-2026'
                          and l.app_id = 'sairncare');

-- 3. CONFIRM. Expect ZERO rows. `bootstrap` now works on this licence again.
select count(*) as should_be_zero
  from public.sairncare_employee_auth
 where license_hash = (select l.license_hash
                         from public.license_keys l
                        where l.key = 'ALF-AUDIT-2026'
                          and l.app_id = 'sairncare');
```

**Then the next session that bootstraps must record where the PIN lives before it
does anything else.** Otherwise this recurs, and it will be the third time.

### Why DELETE and not deactivate

`set_active … false` on the sole owner is refused by the lifecycle guard
(`remaining_admins` would reach zero), and even if it were allowed it would not
help: `bootstrap` counts **rows**, not active rows, so a deactivated owner blocks
it exactly as an active one does. Removing the row is the only path back to a
bootstrap-able licence, and `DELETE` on this table is available to
`service_role` — unlike `alf_incidents`, whose residue in Fourth's document needs
SQL for the opposite reason.

## What I did NOT do, stated rather than left to inference

* **I did not read another session's working notes or scratchpad to find the
  PIN.** It may well be there. Going after a credential in another agent's
  private working area is not a thing to do without being asked, and asking is
  cheaper than the alternative.
* **I did not fall back to a demo licence.** `ALF-TEST-2026` and the
  `-PINNACLE-` keys have documented PINs, and
  `tools/audit_licence.require_audit_licence` refuses them — correctly, because
  this probe **writes** `alf_facility` and the whole point of the audit-licence
  seed was to stop live verification writing onto customer-facing keys. Running
  it there would have produced a result at the cost of the thing the seed exists
  to prevent.
* **I did not seed credentials by SQL.** The item said *through the product's own
  endpoints*, and `alf_facility_role_gate_live_probe.py` says in its own header
  that it deliberately does not provision.
* **I minted four candidate PINs before discovering the 409**, for
  `ZZ-AUDIT-OWNER`, `ZZ-AUDIT-NURSING`, `ZZ-AUDIT-MEDAIDE` and
  `ZZ-AUDIT-CAREGIVER`. **None reached the platform** — the `bootstrap` call was
  refused before any row was written, and the three `setup` calls never ran. They
  are in this session's scratchpad, outside the repo, and are **not credentials
  for anything**: no account exists with them. If path 2 above is taken they can
  be reused; if not they are inert.

## State of the probe right now

```
python tools/alf_facility_role_gate_live_probe.py
  -> UNVERIFIED -- ALF_LICENSE is not set, so NOTHING was driven.
     This is the THIRD STATE. It is NOT "the gate is fine".
```

**That is the correct answer and it is the one to quote.** The `alf_facility`
write gate is verified three ways in-process — the isolation suite drives four
non-management roles to `403` each asserting no upsert, ablation proves those arms
bite, and the gate is present on `origin/main` at the line that deploys. None of
those is the deployed function, and this file does not claim otherwise.
