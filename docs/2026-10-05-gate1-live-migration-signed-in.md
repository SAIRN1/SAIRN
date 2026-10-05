# Gate 1, answered with a session — 22 missing tables nothing could see, and 18 SQL files for Michael

**2026-10-05 (Cody). DRIVEN LIVE, READ ONLY.** Every request in this sweep is
`action:'read'`; nothing was written to any licence. 113 (app, schema file)
pairs across 16 apps, using the licence keys **and the PINs** from
`docs/2026-09-03-demo-credentials.md`.

---

## THE NUMBER THAT MATTERS IS THE ONE THAT MOVED

| | licence key only | signed in |
|---|---|---|
| declared tables | 402 | 402 |
| **PROVISIONED** — confirmed present | 148 | **289** |
| **MISSING** — confirmed absent | **2** | **24** |
| REFUSED — could not be checked | 216 | **64** |
| UNREACHABLE — in `sql/`, not registered | 26 | 25 |
| **answerable at all** | **150 / 402 = 37%** | **313 / 402 = 77%** |

**TWENTY-TWO MISSING TABLES WERE INVISIBLE, AND THE THING HIDING THEM WAS A
SECURITY CONTROL DOING ITS JOB.** The resource is behind the employee session
gate; the check presented a licence key; the endpoint answered 403 FORBIDDEN;
the sweep recorded REFUSED, correctly, and that is indistinguishable in a
summary from a table nobody has asked about. `tools/schema_provisioning_check.py`
gained `--pin` / `--auth` today (`36d58d34`) for exactly this, and the 2 became
24 on the first run.

**This is the silent-failure shape applied to a gate rather than to a feature:**
every write to each of those 24 tables answers **503 NOT_PROVISIONED** into a
console nobody is reading, and the client treats `provisioned:false` as
"nothing to hydrate" and carries on. From inside the app a never-run migration
looks exactly like a practice that has not entered any data yet.

---

## THE SQL ACTIONS — MICHAEL

**EIGHTEEN FILES, FIVE APPS. Every one is `create table if not exists`
throughout and is safe to re-run.** I checked that per file rather than assuming
it: a first pass flagged five as "not fully idempotent" and **that was a defect
in my counter, not in the files** — a comment in each of them contains the words
`create table if not` / `exists` split across two lines, which my `create table`
count read as a second statement. Re-read directly: **all 18 are idempotent.**

| app | run this file | creates |
|---|---|---|
| StoneDesk | `sql/stonedesk_locations_schema.sql` | `sd_locations` |
| SAIRNgrounds | `sql/sairngrounds_caddie_schema.sql` | `grd_rounds`, `grd_cart_orders` |
| SAIRNdental | `sql/sairndental_gfe_schema.sql` | `dnt_gfe` |
| SAIRNdental | `sql/sairndental_recall_schema.sql` | `dnt_recall_outreach` |
| SAIRNdental | `sql/sairndental_treatment_plans_schema.sql` | `dnt_txplans` |
| SAIRNmechanical | `sql/mech_credentials_schema.sql` | `mech_credentials` |
| SAIRNsenior | `sql/sairnsenior_applicants_schema.sql` | `sen_applicants` |
| SAIRNsenior | `sql/sairnsenior_authorizations_schema.sql` | `sen_authorizations` |
| SAIRNsenior | `sql/sairnsenior_branches_schema.sql` | `sen_branches` |
| SAIRNsenior | `sql/sairnsenior_franchise_schema.sql` | `sen_franchise_agreements` |
| SAIRNsenior | `sql/sairnsenior_payer_contracts_schema.sql` | `sen_payer_contracts` |
| SAIRNsenior | `sql/sairnsenior_referrals_schema.sql` | `sen_referrals`, `sen_referral_sources` |
| SAIRNsenior | `sql/sairnsenior_training_schema.sql` | `sen_training_records`, `sen_training_rules` |
| SAIRNroofing | `sql/sairnroofing_entities_schema.sql` | `rf_entities` |
| SAIRNroofing | `sql/sairnroofing_prequal_schema.sql` | `rf_bonding`, `rf_prequal_documents` |
| SAIRNroofing | `sql/sairnroofing_safety_schema.sql` | `rf_job_hazard_assessments`, `rf_safety_equipment` |
| SAIRNroofing | `sql/sairnroofing_supplier_documents_schema.sql` | `rf_supplier_documents` |
| SAIRNroofing | `sql/sairnroofing_warranties_schema.sql` | `rf_job_warranties`, `rf_warranty_tiers` |

### HOW, and the two steps that go missing

1. **Paste each file WHOLE into the Supabase SQL editor. Do not retype it and
   do not run it in pieces.** A multi-statement paste can truncate silently and
   half-apply while reporting success — that has happened on this platform and
   the confirm query below is what catches it.
2. **Run the confirm query after each app's files**, not at the end of all 18.
   A single query over all 24 names cannot tell you WHICH paste truncated.

```sql
-- after the SAIRNsenior files, as the example. Swap the name list per app.
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'sen_applicants', 'sen_authorizations', 'sen_branches',
    'sen_franchise_agreements', 'sen_payer_contracts',
    'sen_referrals', 'sen_referral_sources',
    'sen_training_records', 'sen_training_rules')
order by table_name;
```

**Nine rows is the pass for SAIRNsenior.** Fewer means a paste truncated —
re-paste that file and re-run the confirm. Do not assume.

The full 24, for the final sweep:

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'sd_locations',
    'grd_rounds', 'grd_cart_orders',
    'dnt_gfe', 'dnt_recall_outreach', 'dnt_txplans',
    'mech_credentials',
    'sen_applicants', 'sen_authorizations', 'sen_branches',
    'sen_franchise_agreements', 'sen_payer_contracts',
    'sen_referrals', 'sen_referral_sources',
    'sen_training_records', 'sen_training_rules',
    'rf_entities', 'rf_bonding', 'rf_prequal_documents',
    'rf_job_hazard_assessments', 'rf_safety_equipment',
    'rf_supplier_documents', 'rf_job_warranties', 'rf_warranty_tiers')
order by table_name;
```

**24 rows is the pass.** Then re-drive the machine check, which is the part that
does not depend on anybody's reading of a result cell:

```
python tools/schema_provisioning_check.py --app sairnsenior \
    --schema sql/sairnsenior_training_schema.sql --key SEN-PINNACLE-2026 \
    --pin 90128473 --auth sen-auth
```

Exit 0 with `MISSING: 0` is the answer. **`--auth` takes the endpoint NAME with
no leading slash** — Git Bash rewrites `/api/sen-auth` into a Program Files
path, and the tool refuses that by name rather than failing obscurely.

### DO NOT ADD A `delete` GRANT to any of these files while fixing anything in
them. `sql/unused_delete_grant_revoke_2026-08-24.sql` revoked it platform-wide
across 134 tables, and several of these files carry that warning themselves.

---

## TWO APPS CANNOT BE CHECKED AT ALL, AND EACH NEEDS ITS OWN ACTION FIRST

These are **59 of the remaining 64 refusals** and neither is a code problem.

### SAIRNvet — 42 resources, and the PIN is dead

`SV-PINNACLE-2026`'s PIN is recorded **DEAD 2026-09-25** in the credentials
document, and `bootstrap` is **permanently closed** on that licence by design —
it only works against an empty `sv_employee_auth`, and one account was minted
through it on 2026-09-23. So there is no way to hold a SAIRNvet session from a
clone today, and **42 declared tables — including `sv_controlled`, the
DEA-relevant controlled-substance register — are UNANSWERABLE rather than
confirmed.** Further accounts go through `setup`, which itself needs a session.
**This needs a decision, not a SQL file:** either a credential minted through
`setup` by somebody who already holds one, or a new demo licence.

### SAIRNfreedom — 17 resources, and the auth table has never been created

`/api/sf-auth` answers **503 NOT_PROVISIONED** because
**`sql/sairnfreedom_employee_auth_schema.sql` has never been run.** Open-work
row 156 already records this, and it is worth restating what it blocks: the 17
include `sf_operators` (a felony flag and a gambling disqualification on a named
volunteer), `sf_gaming_expenses` and `sf_disbursements` (ORC 2915 payee
records), `sf_donations`, and `sf_youth_participants` (**minors**). The resources
are gated correctly — every one answers 403 without a session — and the
consequence is that **nobody, including this check, can confirm their tables
exist.**

> **MICHAEL: run `sql/sairnfreedom_employee_auth_schema.sql`.** Then a PIN can
> be minted and the 17 become answerable.

---

## FIVE REFUSALS SURVIVED A SUCCESSFUL SIGN-IN — named, not diagnosed

Signed in as `sairn-demo-owner` with an owner role and **still 403**:

| app | resource |
|---|---|
| SAIRNmechanical | `mech_insurance_policies` |
| SAIRNroofing | `rf_claim_agreements`, `rf_claim_photos`, `rf_photos`, `rf_proposals` |

A session was held and the read was still refused, so the gate on these is
**narrower than "any signed-in employee"** — a role the demo owner does not
have, or a second condition. That is the right direction for a gate to fail in
and it is not a finding here. **I did not read the dispatcher to find out
which**, because a guess about an access-control decision is worse than an
unanswered question.

---

## 25 UNREACHABLE — a different problem with the same symptom

Declared in a `sql/` file and **not registered** in `api/_resources`, so neither
this check nor the app can ask for them. Many are deliberate — auth tables,
rate-limit tables and witness-token tables are reached by bespoke endpoints
rather than the generic dispatcher, and `sairndental_employee_auth`,
`sairnvet_employee_auth` and `sairnmechanical_employee_auth` are all in that
class.

**`sairnlaw` has 10 and is the one worth a read:** `cl_case_cache`,
`cl_citing_treatments`, `cl_court_cache`, `cl_coverage`, `cl_feedback_log`,
`cl_rate_limit_log`, `fcl_rate_limit_log`, `law_deadline_rules`, `law_holidays`
and one more. `law_deadline_rules` and `law_holidays` are the deadline engine's
own tables and are written by `api/legal-deadlines.js` rather than by
`api/sd-data.js`, which explains them; the `cl_*` family is a cache layer.
**Named rather than diagnosed** — none of this was read today.

---

## WHAT THIS STILL DOES NOT ESTABLISH

- **That a write succeeds.** Every request here is a read. The tool's own header
  says a pass means the table exists, the resource is registered, the handler
  branch is reached and the licence resolves — not that a row comes back, and
  not that the id column matches what the client sends.
- **That the 289 provisioned tables are RIGHT.** Existence is not shape.
- **Anything about the 64 refusals and 25 unreachable.** Those are
  COULD-NOT-TELL, and 77% answerable means 23% unanswered, not 23% fine.
- **That `docs/MASTER-PLAN.md`'s Gate 1 table should now be filled in.** It
  takes HUMAN ATTESTATIONS by design and this is a machine result. Whether the
  gate gains a "mechanically confirmed, read-only" column is a decision for
  whoever owns that document — **but a gate that cannot see 289 confirmed
  tables is now understating itself by a lot.**
