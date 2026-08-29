# The single-provisioning-role trapdoor: what it actually is, and the fix I'd make

**2026-08-29 (Hank).** Analysis of the open Platform row in
`docs/SAIRN-OPEN-WORK-INDEX.md`, taken up after RF-PINNACLE-2026 turned out to
have already recovered. Every claim below is read from source on this date, not
carried from the index row.

---

## 1. The state, stated precisely

The trapdoor is **not** "this app has one provisioning role". It is:

> **Credential rows exist for a licence, and none of them is both `active` and
> holding a role in `PROVISIONING_ROLES`.**

All three exits are then closed, and each for a different reason:

| exit | why it fails |
|---|---|
| `bootstrap` | refuses 409 while **any** row exists — the existence probe deliberately does not filter on `active` |
| `setup` (provision a new provisioner) | requires an active caller in `PROVISIONING_ROLES` |
| `set_active` (reactivate one) | same gate, plus a re-read that the caller's own row is still `active` |

The single-role count matters only because it makes the pool smaller. It is a
risk multiplier, not the mechanism.

## 2. What is actually in the five files

Read from source 2026-08-29. Exactly five of sixteen auth files implement
`set_active` at all; the other eleven have neither it nor a `PROVISIONING_ROLES`
constant and are out of scope rather than unaudited.

| app | file | `PROVISIONING_ROLES` | `MANAGEMENT_ROLES` |
|---|---|---|---|
| SAIRNdental | `dnt-auth.js` | `['owner']` | `{owner}` |
| SAIRNmechanical | `mech-auth.js` | `['owner']` | `{owner, admin}` |
| SAIRNroofing | `rf-auth.js` | `['owner']` | `{owner, admin}` |
| SAIRNcode | `sc-auth.js` | `['admin']` | *(none defined)* |
| StoneDesk | `sd-auth.js` | `['owner', 'admin']` | *(none defined)* |

**SAIRNdental is the worst-placed, not SAIRNcode.** It is the only app where
`PROVISIONING_ROLES` and `MANAGEMENT_ROLES` are *both* a single role and the
*same* role. In mech and rf an `admin` at least remains as a management-capable
account that could be promoted by a SQL fix without inventing a new credential;
in dnt there is nobody but the owner.

**The SAIRNcode trap in the index row is real but narrower than stated.** Its
single role is `admin`, not `owner`, so any recovery path that names a role in
code misses it silently. I checked whether the *existing* guards fall into this:
they do not — all five read `PROVISIONING_ROLES` rather than a literal, in both
the `activeOwners`/`activeAdmins` filter and the target test. The trap applies to
**new** code only.

## 3. The finding that changes the recommendation

**The API cannot reach this state. At all.** `set_active` in each of the five:

1. requires `caller.role ∈ PROVISIONING_ROLES`;
2. re-reads the roster and refuses if the caller's own row is not `active`
   (`CREDENTIAL_INACTIVE`) — so a token outliving its credential is no help;
3. refuses self-deactivation (`SELF_DEACTIVATE`);
4. refuses when the target is an active provisioner and
   `activeProvisioners.length <= 1` (`LAST_OWNER` / `LAST_ADMIN`).

Taken together the count cannot cross from 1 to 0 through any API path. That is
why `LAST_OWNER` is documented as unreachable-by-construction — correctly.

So RF-PINNACLE-2026 did not get stuck through the API. It got stuck through
**seed files and direct SQL** — verification passes that wrote `active: false`,
and a cleanup script that would have deleted some owner rows while leaving
others. That is the only door, and it is the one nothing guards.

This matters because it kills the obvious fix. "Let `bootstrap` proceed when
there are rows but no *active provisioner*" is usually rejected on the grounds
that someone holding the licence key could deactivate their way to a fresh owner
and seize the company. **That specific attack is not reachable** — you must
already be an active provisioner to deactivate anyone, and the guards stop you
before zero.

But the softening is still wrong, for a different reason worth stating since the
usual one does not hold:

> A licence key is shared with every employee and is not a secret. An
> organisation can legitimately sit at zero active provisioners — the sole owner
> is on leave, deactivated, or has left — while narrow-role staff keep working.
> Under the softened rule, **anyone holding the key could bootstrap themselves a
> new Owner over a live tenant's data.** The current rule refuses, and it is
> right to.

## 4. Recommendation

**Guard the door that is actually open, and detect the state; do not widen
`bootstrap` and do not change any app's authorisation model.**

Three parts, in priority order. Only the first is urgent.

### 4a. A guard on every SQL file that touches an `*_employee_auth` table

This is the only path that can create the state, and it currently has nothing on
it. The guard asserts the **end state** is one of the two safe shapes and rolls
the transaction back otherwise:

- **zero rows** for that licence → `bootstrap` is re-armed, licence healthy; or
- **at least one active row holding a provisioning role** → `setup` and
  `set_active` both work.

Anything else is the trapdoor. A worked implementation is already in
`sql/sairnroofing_access_panel_verify_cleanup_2026-08-28.sql` (rewritten
2026-08-29); the reusable shape is at the bottom of this document.

Note what this deliberately does *not* do: it does not stop a file deleting
every row. Deleting everything is **recovery**, not lockout — the original
roofing cleanup was right about that, and conflating the two is what made this
row confusing for a day.

### 4b. Detection, so the state is noticed rather than discovered

The same shape as tonight's load-state gate: a read-only check reporting, per app
per licence, the active-provisioning-role count. RF-PINNACLE-2026 sat in this
state long enough for a HIGH PRIORITY index row to be written about it, then
recovered, and **nothing noticed either transition** — the row was still
asserting zero active owners on 2026-08-29 when the live roster had two.

The check must read each app's own `PROVISIONING_ROLES` rather than assume
`owner`, or it reports SAIRNcode clean forever. That is where the index row's
trap genuinely bites.

### 4c. Widening `PROVISIONING_ROLES` — a real decision, not a safety patch

StoneDesk's `['owner', 'admin']` means two deactivations are needed rather than
one; it is a reduction in exposure, not immunity. If the last active `owner` and
the last active `admin` both go inactive, StoneDesk is locked out identically.

So the question is **"how many provisioning-role holders must remain active"**,
not "does this app have two roles" — and widening the pool is an authorisation
change with product consequences (an office manager who can now provision
owners), which should be decided per app on those merits, not adopted as a
lockout mitigation. For SAIRNdental it is the only structural option available,
which is a reason to look at dnt first and not a reason to do all four.

## 5. What I did not verify

- Whether any **other** licence on any of the five apps is currently in the
  state. That needs 4b, or a query per app, and I have no DB access from this
  clone.
- The eleven auth files without `set_active` were confirmed to lack the
  constant; I did not audit how they provision at all.

---

## The reusable guard

Paste at the end of any transaction that inserts, updates or deletes rows in an
`*_employee_auth` table. Substitute the table, the licence key, and the app's own
provisioning role(s) — **read them from that app's `PROVISIONING_ROLES`, do not
assume `owner`; SAIRNcode's is `admin`.**

```sql
do $$
declare
  lh   text := encode(digest('<LICENCE-KEY>', 'sha256'), 'hex');
  rows int;
  prov int;
begin
  select count(*) into rows
    from public.<app>_employee_auth where license_hash = lh;
  select count(*) into prov
    from public.<app>_employee_auth
   where license_hash = lh
     and active = true
     and role = any (array['owner']);   -- <- that app's PROVISIONING_ROLES

  -- Safe shape A: zero rows      -> bootstrap re-armed.
  -- Safe shape B: >=1 active provisioner -> setup and set_active both work.
  if rows > 0 and prov = 0 then
    raise exception
      'ABORTED: would leave % credential row(s) and ZERO active provisioners. '
      'Delete EVERY row for this licence, or leave at least one active '
      'provisioner. Never a subset of the provisioners.', rows;
  end if;
  raise notice 'Guard passed: % row(s), % active provisioner(s).', rows, prov;
end $$;
```
