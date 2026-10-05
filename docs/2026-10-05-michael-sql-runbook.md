# Michael's SQL runbook — 20 files, 26 tables, and a snapshot re-capture. Ready now.

**2026-10-05 (Cody). NOTHING HERE NEEDS A DECISION. Every file already exists in
`sql/`, every one is idempotent, and the order, the confirm queries and the
after-check are all written.** Prepared before being asked so the only thing
left is the pasting.

**Three artefacts, and they do different jobs:**

| artefact | what it answers |
|---|---|
| the 20 files in `sql/` | the migration itself — **already written, never run** |
| `sql/zz_confirm_2026-10-05_missing_tables.sql` | does POSTGRES have the table, the grants and RLS |
| `python tools/gate1_verify.py` | **can the APP reach it** — a different question |

> **WHY THE LAST TWO ARE BOTH NEEDED AND NOT REDUNDANT.** A `CREATE TABLE` that
> lands while its `GRANT` block does not leaves a table `information_schema`
> reports happily and which `api/sd-data.js` answers **503 NOT_PROVISIONED** on
> — the identical answer to a table that was never created. **The catalogue and
> the app can disagree, and only running both finds out.**

---

## BEFORE YOU START — the baseline is recorded, so progress is measurable

Driven live today, signed in on all six demo licences:

```
python tools/gate1_verify.py
  ...
  PRESENT : 0
  MISSING : 26
  asked about 26 of 26 expected tables
  exit 1
```

**All 26 confirmed absent from the app's side as of 2026-10-05.** Re-running that
one command after the pastes is the whole after-check.

---

## THE ORDER, AND WHY IT IS THIS ORDER

**Smallest app first, largest last.** Not for tidiness: the first paste is the
one most likely to reveal a problem with the procedure rather than with the
file, and finding that on SAIRNgrounds' two tables costs less than finding it on
SAIRNsenior's nine.

**PASTE EACH FILE WHOLE. DO NOT RETYPE IT AND DO NOT RUN IT IN PIECES.** A
multi-statement paste can truncate silently and half-apply while still reporting
success — that has happened on this platform, and the confirm sections are what
catch it.

**RUN THE CONFIRM SECTION FOR AN APP IMMEDIATELY AFTER THAT APP'S FILES**, not
all of them at the end. A total at the end cannot tell you *which* paste
truncated, which is the entire point of confirming.

| # | app | paste these, in this order | tables | then run |
|---|---|---|---|---|
| 1 | SAIRNgrounds | `sql/sairngrounds_caddie_schema.sql` | 2 | confirm **section 3** → expect **2** |
| 2 | SAIRNmechanical | `sql/mech_credentials_schema.sql` | 1 | confirm **section 5** → expect **1** |
| 3 | StoneDesk | `sql/stonedesk_locations_schema.sql`, `sql/sd_approvals_schema.sql` | 2 | confirm **section 1** → expect **2** |
| 4 | StoneDesk | `sql/sd_supplier_lead_times_schema.sql` | 1 | confirm **section 2** → expect **1** |
| 5 | SAIRNdental | `sql/sairndental_gfe_schema.sql`, `sql/sairndental_recall_schema.sql`, `sql/sairndental_treatment_plans_schema.sql` | 3 | confirm **section 4** → expect **3** |
| 6 | SAIRNroofing | `sql/sairnroofing_entities_schema.sql`, `sql/sairnroofing_prequal_schema.sql`, `sql/sairnroofing_safety_schema.sql`, `sql/sairnroofing_supplier_documents_schema.sql`, `sql/sairnroofing_warranties_schema.sql` | 8 | confirm **section 7** → expect **8** |
| 7 | SAIRNsenior | `sql/sairnsenior_applicants_schema.sql`, `sql/sairnsenior_authorizations_schema.sql`, `sql/sairnsenior_branches_schema.sql`, `sql/sairnsenior_franchise_schema.sql`, `sql/sairnsenior_payer_contracts_schema.sql`, `sql/sairnsenior_referrals_schema.sql`, `sql/sairnsenior_training_schema.sql` | 9 | confirm **section 6** → expect **9** |

**Then sections 8, 9 and 10 once, at the end:** the total (26), the grants, and
RLS.

**FEWER ROWS THAN STATED MEANS A PASTE TRUNCATED.** Re-paste that one file and
re-run that one section. Do not carry on and do not assume.

### Two things that are safe and worth knowing

- **Every one of the 20 is `create table if not exists` throughout, so
  re-running any of them is safe.** Checked per file — and a first pass flagged
  five as not idempotent, which was **a defect in my counter, not in the
  files**: each contains a comment with the words `create table if not` /
  `exists` split across two lines, which a `create table` count read as a second
  statement. All 20 are idempotent.
- **DO NOT ADD A `delete` GRANT to any of them** if you end up editing one.
  `sql/unused_delete_grant_revoke_2026-08-24.sql` revoked it platform-wide
  across 134 tables and several of these files carry that warning themselves.
  Confirm section 9 fails if one appears.

---

## AFTER THE PASTES — one command

```
python tools/gate1_verify.py
```

**Expect `PRESENT : 26`, `MISSING : 0`, exit 0.** It signs in on each app's own
auth endpoint and reads each resource through `api/sd-data.js`, so a pass means
the table exists **and the app can reach it**. Per app if you prefer:
`python tools/gate1_verify.py --app sairnsenior`.

**It distinguishes four verdicts and only two of them are answers.** PRESENT and
MISSING are answers; **REFUSED** (a session or dispatch refusal) and
**UNREADABLE** (a bot challenge or transport failure) mean the question was not
answered, and neither is folded into MISSING — otherwise it would send you to
re-run a migration that is already there.

**An EMPTY table reads PRESENT, which is the one thing to expect and not be
alarmed by:** all 26 will be empty the moment they exist. "No rows" and "no
table" are the same screen in an app and different facts here.

---

## THE SNAPSHOT RE-CAPTURE — separate, and do it LAST

`db/schema_snapshot.json`'s own `_generated_at` is **2026-09-13 18:39:55 UTC —
22 days old**, it holds 380 tables, and **51 tables that exist live are absent
from it.**

**Why it matters:** `tools/gate_column_check.py` answers *"does this column
exist"* from that file, and **a column missing from a stale capture is
indistinguishable from a column that does not exist.**

**One piece of good news, measured:** the error is **one-directional**. Zero
tables the snapshot claims exist are actually missing. It under-reports and
never over-reports, so nothing has been cleared on its word that should not have
been.

### The four steps, and steps 3 and 4 are the ones that went missing last time

> 1. Run **`sql/schema_snapshot_query.sql`** whole in the Supabase SQL editor.
> 2. Copy the **single JSON value out of the one result cell**.
> 3. **Save it over `db/schema_snapshot.json`.**
> 4. **Commit it.**
>
> On 2026-09-10 the query was run and the committed file was still the
> 2026-09-02 capture. Steps 1 and 2 happened; 3 and 4 did not, and nothing
> noticed for days.

**DO THIS AFTER THE 20 FILES**, so the capture includes the 26 new tables and
does not immediately need repeating.

**Then confirm the capture landed:**

```
python tools/schema_snapshot_freshness.py
```

Whatever still shows as absent after a fresh capture is the genuine never-run
set rather than a measurement artefact — which is the whole reason the
re-capture is worth doing rather than living with.

---

## WHAT IS **NOT** ON THIS LIST, and was until today

- **`sql/sairnfreedom_employee_auth_schema.sql` — NOT OWED. I was wrong about
  this earlier today and corrected it the same day.** Driven: `/api/sf-auth`
  answers **401 INVALID_CREDENTIALS** on a login and a role-shaped **403** on
  `roster`, and `api/sf-auth.js` returns 503 `NOT_PROVISIONED`/`NOT_GRANTED` for
  exactly the two conditions it is *not* returning — **so that table exists with
  privileges.** I had quoted open-work row 156 instead of asking the endpoint.
  What SAIRNfreedom actually needs is a **credential decision**, not a paste.
- **SAIRNvet.** 42 resources unanswerable because `SV-PINNACLE-2026`'s PIN is
  dead and `bootstrap` is permanently closed on that licence by design. **A
  decision about a credential, not a SQL file.**
- **`firebase-admin` 12.7.0 → 14.5.0.** A dependabot HIGH, two major versions,
  on the SDK that mints SAIRNcash's auth tokens. **An engineering decision with
  a named next step, not a paste** — see
  `docs/2026-10-05-dependabot-high-triage.md`.

---

## WHAT THIS RUNBOOK DOES NOT ESTABLISH

- **That a write to any of the 26 succeeds.** Every check here is a read. A
  table can exist, be reachable, and still reject a write on a column mismatch.
- **That the tables' SHAPE is right.** Existence is not shape, and nothing here
  compares a live column list to the schema file.
- **That 26 is the final count.** 134 of 147 schema files in `sql/` have been
  swept; the other 13 declare no tables, which was checked but is printed by no
  tool. The sweep that produced this list was itself reading 113 of 147 until
  today, so the figure is a floor with a date on it rather than a total.
