# The 11 UNPROVEN apps — resolved, and 9 of them were the check's fault

**hank, batch b13, 2026-10-15.** b12's `api/role-picker-vs-check-constraint.test.js`
ran over all 17 apps in `ROLES_BY_APP` and reported **6 clean, 0 failed, 11
UNPROVEN**, with the 11 named as the finding of the run. b13's dispatch:
*"work down the 11 UNPROVEN apps (role picker invisible to the detector, or
schema has no role CHECK); for each, name the command that proves or fails it,
and mark honestly any you cannot prove."*

**Measured answer: 0 remain unmeasurable, and the great majority of the 11 were
a defect in the check rather than a fact about the apps.** The run now exits 0.

    node api/role-picker-vs-check-constraint.test.js
    -> 17 app(s) clean, 0 with a refused role, 0 could not be measured

Evidence: `docs/hank-evidence/b13/unproven_before.log` (the b12 state, re-run at
this HEAD), `unproven_after_table_fix.log`, `unproven_after_second_method.log`,
`unproven_after.log` (final), `unproven_SABOTAGE.log`.

---

## What the 11 actually were

### Cause 1 — the check looked for four table names that do not exist (4 apps)

`stonedesk`, `sairnbiz`, `sairngrounds`, `sairnscape` were reported as *"no
`check (role in (...))` found in any sql/ file naming `<app>_employee_auth`"*.

The check constructed the table name as `app + '_employee_auth'`.
**`api/_lib/auth.js:1094` says in its own words that there is no such rule:**

> DECLARED, NEVER DERIVED. Fifteen apps and no rule: `sd`, `sb`, `grd` and
> `scp` use a prefix, the rest use the full app name... A derivation would be
> wrong for at least five of them and wrong SILENTLY.

The four tables are `sd_employee_auth`, `sb_employee_auth`,
`grd_employee_auth`, `scp_employee_auth`. All four **do** carry a role CHECK:

    grep -rn "check *( *role" sql/*.sql | grep -E "sd_|sb_|grd_|scp_"
    sql/sd_employee_auth_schema.sql:41   ('owner','admin','sales','install')
    sql/sb_employee_auth_schema.sql:37   ('owner','hr','accounting','manager','staff')
    sql/grd_employee_auth_schema.sql:27  ('owner','superintendent','manager','crew','office')
    sql/scp_employee_auth_schema.sql:27  ('owner','crew_lead','office')

**Fix:** the name is read from the exported `AUTH_TABLE_BY_APP` — the same map
the live session gate uses to decide which table to read — so there is one
source for it instead of a second rule that can disagree.

This is the eighth cross-domain discipline exactly: *nothing announces the day
a check stops testing anything.* It never tested those four; the output said
"could not measure" and that read as an open question about the apps.

### Cause 2 — the picker is built in JavaScript, not in markup (5 apps)

`sairnbiz`, `sairngrounds`, `sairnscape`, `sairnvet`, `sairnfreedom` were
reported as *"no role picker found — no `<select>` has two or more option values
from this app's own vocabulary"*.

The detector scanned **static `<option>` markup**. SAIRNfreedom's picker is:

    sairnfreedom.html:383   <div><label>Capability</label><select id="ac-cap"></select></div>
    sairnfreedom.html:2680  sel.innerHTML = CAPABILITIES.map(function(c){
                              return '<option value="' + c.id + '">' + ...

An option whose value is `' + c.id + '` leaves **no literal token** for an
option scanner to find.

**Fix — a second method that is structurally different, not a wider regex over
the same text** (cross-domain discipline 6): any **array literal** in the page
carrying two or more quoted tokens that are **all** in that app's own role
vocabulary is a declared role list. `['owner','crew_lead','office']` matches;
`['Pending','Completed']` fails on the first member. The line number of the
matched literal is printed so a reader can check what was matched.

**The weaker claim is labelled as weaker.** Five apps are ARRAY-ONLY — no static
picker was found at all — and for those what is proven is *"no declared role
list in this page carries a refused role"*, which is broader and weaker than
*"the provisioning picker was checked"*. The run says so on each of those five
lines rather than reporting them identically to the seven with a real picker.
The cost of the "all, not some" rule runs the other way and is stated rather
than discovered: **an array mixing roles with non-roles is still missed**, which
is why the static scan is kept beside it rather than replaced.

### Cause 3 — four apps do not assign roles from their own page at all

`sairncode`, `sairndental`, `sairnmechanical`, `sairnroofing` survived both
detectors. The reason is the same for all four and is **not** a detector gap:

    grep -c "'setup'" sairncode.html sairndental.html sairnmechanical.html sairnroofing.html
    -> 0, 0, 0, 0

SAIRNmechanical says it in its own UI text (`sairnmechanical.html:703`):

> PINs are no longer set here... An Owner provisions them through
> `api/mech-auth.js` (`setup`).

SAIRNcode's access panel reads the roster and toggles `active`; there is no role
control (`sairncode.html:5741`). **A page that cannot send a role cannot offer
one the CHECK refuses**, so "could not measure" overstated what was owed. These
are now reported **NOT APPLICABLE** with the command that re-derives it, and
with the limit named: this says nothing about what a **direct API caller**
sends — that is the endpoint's own role validation plus the database CHECK, a
different control this check does not measure.

### Cause 4 — stonedesk_sub is not an employee-auth app

`stonedesk_sub` was *"no stonedesk_sub.html in the repo"*. `api/_lib/auth.js`
records the real answer: it is **deliberately absent** from
`AUTH_TABLE_BY_APP` because subcontractors authenticate against `sd_sub_auth`
keyed on `sub_id`, not `employee_id`. So there is no `<app>_employee_auth` role
CHECK of this shape to compare against. **NOT APPLICABLE**, with the note that
if an app which *should* have employee credentials ever appears on that line,
**the missing map entry is itself the finding** — the live session gate reads
the same map and answers `NO_ACTIVE_CHECK` without one.

---

## Per app, with the command

| app | b12 | now | the command that settles it |
|---|---|---|---|
| stonedesk | UNPROVEN (no CHECK) | clean, 3 static + 1 array | `grep -n "check *( *role" sql/sd_employee_auth_schema.sql` |
| sairnbiz | UNPROVEN (no CHECK) | clean, **array-only** (2) | `grep -n "check *( *role" sql/sb_employee_auth_schema.sql` |
| sairngrounds | UNPROVEN (no CHECK) | clean, **array-only** (3) | `grep -n "check *( *role" sql/grd_employee_auth_schema.sql` |
| sairnscape | UNPROVEN (no CHECK) | clean, **array-only** (2) | `grep -n "check *( *role" sql/scp_employee_auth_schema.sql` |
| sairnfreedom | UNPROVEN (no picker) | clean, **array-only** (1) | `sed -n '2678,2684p' sairnfreedom.html` — CAPABILITIES fills `#ac-cap` at runtime |
| sairnvet | UNPROVEN (no picker) | clean, **array-only** (1) | `node api/role-picker-vs-check-constraint.test.js` prints the matched literal's line |
| sairncode | UNPROVEN (no picker) | **NOT APPLICABLE** | `grep -c "'setup'" sairncode.html` → 0 |
| sairndental | UNPROVEN (no picker) | **NOT APPLICABLE** | `grep -c "'setup'" sairndental.html` → 0 |
| sairnmechanical | UNPROVEN (no picker) | **NOT APPLICABLE** | `grep -c "'setup'" sairnmechanical.html` → 0; and `sed -n '703,707p' sairnmechanical.html` says so in the UI |
| sairnroofing | UNPROVEN (no picker) | **NOT APPLICABLE** | `grep -c "'setup'" sairnroofing.html` → 0 |
| stonedesk_sub | UNPROVEN (no HTML) | **NOT APPLICABLE** | `grep -n "stonedesk_sub is DELIBERATELY ABSENT" api/_lib/auth.js` |

Final shape of the run: **12 apps compared against a CHECK** (7 with a static
picker, 5 array-only), **5 NOT APPLICABLE**, **0 with a refused role**, **0
unmeasurable**.

---

## The check was sabotaged to prove it still fails, and the first sabotage was MISSED

Two runs in a detached worktree at HEAD, `unproven_SABOTAGE.log`:

**Sabotage 1 — a misspelt role planted into a picker.** `med_aide_II` added to
SAIRNsenior's picker and `crew_lead_II` to SAIRNscape's array.
**Result: exit 0, MISSED.** The comparison skips any option value not in
`ROLES_BY_APP`, because a picker legitimately carries `''` and non-role options.
So a **misspelt role is invisible to this check** — it would be offered, and
refused 23514 by the database, with nothing saying so.

**That is now printed as a named limit on every run**, beside the live-lag one.
It is not closed, and closing it means deciding which non-role option values are
legitimate per app — a vocabulary nobody has written. **Named, not fixed.**

**Sabotage 2 — the real defect shape.** A role removed from a schema file's
CHECK while the picker still offers it (`'caregiver'` out of
`sairnsenior_employee_auth_schema.sql`, `'crew_lead'` out of
`scp_employee_auth_schema.sql`).

    exit=1
    FAIL  sairnscape: a picker offers a role the database CHECK refuses -- 2 case(s)
    FAIL  sairnsenior: a picker offers a role the database CHECK refuses -- 1 case(s)
    15 app(s) clean, 2 with a refused role, 0 could not be measured

**Both methods catch it independently** — sairnsenior through the static
picker, sairnscape through the array literal, which is the path that did not
exist before this batch. The second method is not permissive.

---

## What is still NOT proven, and the one query that would settle it

**This compares a picker against the CHECK in `sql/` — the repo's INTENDED
constraint, not production's.** Unchanged by this batch and printed every run:

* **CAUGHT:** a picker ahead of the schema file (drift).
* **NOT CAUGHT:** a schema file ahead of production (lag). That is the
  `office_manager` state today: `sairncare`'s and `sairnlegacy`'s CHECKs are
  widened by `sql/2026-10-14-michael-run-order.sql`, which is **unrun**.
* **NOT CAUGHT:** a picker value in neither the vocabulary nor the CHECK
  (sabotage 1).

The live question is one query per app, and only Michael can run it:

    select pg_get_constraintdef(oid) from pg_constraint
     where conname = '<app>_employee_auth_role_check';
