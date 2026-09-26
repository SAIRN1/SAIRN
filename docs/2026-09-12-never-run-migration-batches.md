# The never-run migrations — the send order, and what was checked before sending

> ## ⚠ CORRECTED 2026-09-12, HOURS AFTER THIS FILE WAS WRITTEN
>
> **The counts below are AS OF THE 2026-09-11 15:42 UTC CAPTURE, not as of now,
> and at least batch 1 is already done.** Michael ran
> `stonedesk_public_surface_schema.sql` after that capture;
> `tools/stonedesk_storefront_live_check.py` now answers **LIVE** for
> `sd_public_rate_limits`, `sd_public_shop` and `sd_order_links` against
> production, where CC measured 503 `UNAVAILABLE` / `NOT_PROVISIONED` for the
> same probes earlier. `sd_quote_requests` and `sd_customers` are not reachable
> by any unauthenticated probe and are therefore **unverified, not
> contradicted**.
>
> **The mistake was mine and it was not a stale file.** The analysis used the
> newest capture committed anywhere in the repo — `3d603dd0`, byte-identical
> local and origin, verified. The rule it applies excludes *"the snapshot is
> behind"* relative to the **CREATE date**. It said nothing about **now**. A
> migration run after the capture makes a never-run verdict wrong, and I stated
> the verdicts in the present tense with no expiry on them.
>
> `schema_snapshot_freshness.py` now scopes every verdict to the capture
> instant, prints the capture's age, warns above 12 hours, and carries
> `verdict_as_of` in its JSON. Held by section 4b of
> `tests/run_schema_verdict_probe.py`.
>
> **Do not act on the table below until the snapshot is re-captured.** Every row
> needs re-deriving; batch 1 is struck through on the evidence above.

**2026-09-12 (Hank).** `tools/schema_snapshot_freshness.py` resolved 89 tables
declared in `sql/` as NEVER RUN **as of the 2026-09-11 15:42 UTC capture**.
**31 of them are queried by live `api/` code** — that is the set below. The
other 58 are real but no shipped code path reaches them yet.

Skill used: **`sairn-grant-sweep`**, specifically *"grant only the verbs the code
actually calls"* and its note that `create table if not exists` files are safe to
re-run.

**Nothing here can be run from a session.** Every one needs the Supabase SQL
editor as the owner role. This file exists so the batching survives the session
that produced it.

## What was checked on every file before it was sent

Mechanically, then read by hand where the mechanical answer was surprising:

- **Idempotent** — every `create table` / `create index` / `create extension`
  carries `if not exists`, so a re-run is safe and a partial run can simply be
  re-run. **True of all 21.**
- **No unused `DELETE` grant.** **True of all 21** — none grants `delete`.
  This matters beyond tidiness: these tables carry RLS `using (false)` and
  `service_role` bypasses RLS entirely, so the grant is the only layer between
  a leaked service key and irreversible row loss.
- **The verbs match what the code calls.** Checked per table against its real
  consumers. `sd_approvals` grants `select, insert` only and is append-only in
  `api/sd-data.js` — correct, not an omission. `sd_public_rate_limits` uses
  `?on_conflict=` in `api/_lib/stonedesk-public.js`, so it needs `update`, and
  has it — the verb whose absence took `sairncash_waitlist` down on 2026-08-26.
- **Foreign-key prerequisites.** None of the 21 declares a FK to a table that is
  not already live. The two apparent hits were prose — *"zero references across
  all of api/"* and *"how every other rf_ table references its siblings"*.
- **Credential-row recoverability** (push protocol §3.4).
  `mech_credentials_schema.sql` names `mech_employee_auth` but declares
  technician licences, not credential rows. `employee_auth_guard_check.py`:
  27 writers, 0 unguarded.

**A false positive in my own pre-flight, recorded because of what it was.** The
throwaway script that ran the checks above reported
`sairngrounds_caddie_schema.sql` as carrying a non-idempotent `create` and three
tables where it has two. It was counting **the file's own comment** — *"Idempotent
(create table if not exists), safe to re-run"* — as a `CREATE` statement. That is
`docs/SAIRN-PROCESS-RULES.md` §1.2, in a script written minutes after that rule
was filed. The file is genuinely idempotent; confirmed by reading it.

## Send order — highest exposure first

| # | Files | Tables | App | Sent |
|---|---|---|---|---|
| ~~1~~ | ~~`stonedesk_public_surface_schema.sql`~~ | ~~5~~ | StoneDesk | **RUN — 3 of 5 confirmed LIVE 2026-09-12; `sd_quote_requests` and `sd_customers` unverified, no unauthenticated probe reaches them** |
| 2 | `sd_approvals_schema.sql`, `stonedesk_locations_schema.sql`, `sd_supplier_lead_times_schema.sql`, `stonedesk_intake_photos_2026-09-03.sql` | 4 | StoneDesk | — |
| 3 | `sairnroofing_prequal_schema.sql`, `sairnroofing_safety_schema.sql`, `sairnroofing_warranties_schema.sql`, `sairnroofing_entities_schema.sql`, `sairnroofing_supplier_documents_schema.sql` | 8 | SAIRNroofing | — |
| 4 | `sairnsenior_authorizations_schema.sql`, `sairnsenior_branches_schema.sql`, `sairnsenior_franchise_schema.sql`, `sairnsenior_payer_contracts_schema.sql` | 4 | SAIRNsenior | — |
| 5 | `ledger_schema.sql`, `accounting_connector_schema.sql` | 4 | shared | — |
| 6 | `sairngrounds_caddie_schema.sql`, `mech_credentials_schema.sql`, `mech_site_assets_schema.sql` | 4 | SAIRNgrounds, SAIRNmechanical | — |
| 7 | `sairn_style_profiles_schema.sql`, `sairnscape_org_intel_schema.sql` | 2 | shared, SAIRNscape | — |

**Why StoneDesk first:** it is the flagship, and its public storefront has had
no tables since it shipped 2026-09-02 — `stonedesk-catalog.html` is live and
every request against it fails. Batch 1 is also the only one independently
verified by a second session: CC traced every column, filter, `on_conflict`
target and grant verb to a declaration across all four consumers in `58465572`,
zero mismatches, and confirmed the absence live with 503 `UNAVAILABLE` /
`NOT_PROVISIONED` probes.

**Why batch 7 is last.** Both files carry a caveat rather than a defect:

- `sairnscape_org_intel_schema.sql` is **the only one of the 21 that does not
  enable RLS**, and its header says why — SAIRNscape has no licence or auth
  system at all, so the file matches the app's real posture instead of
  pretending a boundary exists. Deliberate and documented. The residual question
  is whether the project's `ALTER DEFAULT PRIVILEGES` baseline grants `anon` or
  `authenticated` anything on a new public table; **that needs a live
  `pg_default_acl` read and has not been done**, so it is stated as open rather
  than assumed safe.
- `sairn_style_profiles_schema.sql` is a cross-app table whose consumers should
  be re-read before it lands.

## What running these does NOT prove

A table existing is not a working feature. `schema_provisioning_check.py` can
confirm the table is reachable through the API afterwards, but a passing read
does not prove a write succeeds, that the id column matches what the client
sends, or that a row comes back. Those need a real write against a real licence.

## The lesson, which is not about this tool

**A verdict with no stated expiry gets read as a fact about now.** That is the
whole of it. The rule was sound, the data was the newest available, the
arithmetic was right, and the answer was still wrong for five tables within
hours — because "NEVER RUN" was printed in the present tense about a measurement
taken a day earlier, on a platform where four sessions and a human run
migrations by hand.

This is `sairn-memory-curator` §2 — *a fact with a tense needs a read* — applied
to a tool's OUTPUT rather than to a document. The same discipline that stops a
CLAUDE.md line going stale has to apply to anything a checker prints, and it is
easier to miss there because a freshly-computed number feels current by
construction. **It is only as current as its oldest input.**

Filed as `docs/SAIRN-PROCESS-RULES.md` §1.10.

## The standing risk this set illustrates

`api/sd-data.js` answers a read against a missing table with
`provisioned: false`, and the client treats that as *"nothing to hydrate"*. So a
never-run migration is indistinguishable, from inside the app, from a customer
who has not entered any data yet — no error, no warning, and every write
answering 503 into a console nobody is reading. That is why these sat for ten
days without anyone noticing, and why the detection had to come from comparing
`sql/` against a live capture rather than from the app.

---

## Added 2026-09-26 (Hank) — SAIRNmechanical, two files, INDEPENDENT of the 2026-09-11 capture

**These two are not part of the table above and do not depend on its
re-capture.** They were written on 2026-09-25 and 2026-09-26 for features that
landed end-to-end in the same session, so their never-run status is a fact about
this week rather than a verdict derived from a stale snapshot.

| File | What it provisions | State |
|---|---|---|
| `sql/mech_site_assets_schema.sql` | **Re-run.** It already exists live; the file gained an idempotent `ALTER` adding `site_state` and `gwp_over_150` for the CARB limb (17 CCR 95380) | **NOT RUN.** Until it is, `carbScope()` answers `unknown_jurisdiction` for every asset — correct, and useless |
| `sql/mech_insurance_schema.sql` | **New table.** `mech_insurance_policies`, the business's own COI position | **NOT RUN.** Until it is, the endpoint answers `provisioned:false` and the panel says so rather than showing an empty board |

### What was checked here, and what was NOT

**CHECKED, mechanically, on both files:**

- `tools/sairn_sql_preflight.py` reports **0 findings** on each.
- Parens balanced, every statement terminated, no `drop`, no `truncate`, no
  `delete`.
- Idempotent throughout: 1 `create table if not exists`, 3 and 5
  `add column if not exists`, 3 `create index if not exists` apiece. **Both are
  safe to re-run**, which is what makes the `mech_site_assets` row above a
  re-run rather than a migration.
- Grants are exactly `select, insert, update` to `service_role` on each. **No
  `delete`** — a lapsed policy is part of the coverage history somebody may have
  to answer for, and an asset is a description rather than a disposable row.
- **Every column named in each file's own VERIFY block is declared in that
  file.** This is the one that would rot silently: a verify query naming a
  column that was renamed checks fewer rows and still prints a clean-looking
  result.

**NOT CHECKED, and it is not a formality:**

- **The SQL was never parsed by Postgres.** There is no `psql`, no `pglast` and
  no `sqlparse` in this clone, so "syntactically sound" here means *structurally
  sound by inspection*, not *accepted by the server*. The preflight itself exits
  **2**, printing its own reason: with no `--live` snapshot it compares against
  the repo's `CREATE TABLE` statements rather than the database, so *"a schema
  file written but never run looks PRESENT"*. That is a COULD-NOT-TELL and it is
  not being folded into a pass.
- Whether `mech_site_assets` in production already has the two CARB columns from
  some earlier hand-run. The `ALTER` is idempotent either way, so this is
  unknown rather than risky.

### Why a session cannot run them

Same reason as every row above: the Supabase SQL editor as the owner role. **The
verify blocks at the foot of each file are the acceptance test** — run them and
read the rows, rather than trusting that the editor reported success. Both files
say in their own text what a defaulted column would do in each direction, which
is the thing to check: a `site_state` with a default asserts a jurisdiction
nobody recorded, and a `gwp_over_150` or an insurance limit defaulted to
anything reads as coverage nobody has evidence of.

---

## Added 2026-09-26 (Hank) — SAIRNcare family contacts, also independent of the capture

| File | What it provisions | State |
|---|---|---|
| `sql/sairncare_family_contacts_schema.sql` | **New table.** `alf_family_contacts` — the family / responsible-party record, and the per-contact `mar_consent` flag | **NOT RUN.** Until it is, the endpoint answers `provisioned:false` and the Residents panel says so rather than showing an empty list |

**CHECKED:** `sairn_sql_preflight` 0 findings; parens balanced; no `drop`,
`truncate` or `delete`; idempotent (`create table if not exists` plus an
`add column if not exists` block); grant exactly `select, insert, update` to
`service_role` with **no delete**, because who had access to a resident's
medication status and when is a record a facility may have to produce; and
every column named in its own VERIFY block is declared in the file.

**THE VERIFY BLOCK IS THE ACCEPTANCE TEST HERE MORE THAN USUALLY.** Two of its
queries exist to catch a specific wrong outcome rather than a typo:

- `mar_consent` must come back **NO / false**. If `is_nullable` says YES,
  *"nobody has decided"* and *"decided no"* have become the same value, and the
  first reader that forgets `= true` discloses medication information.
- The `alffam_consent_has_a_date` constraint must exist. Its absence means a row
  can claim consent with no timestamp on it — a disclosure nobody can audit.

**NOT CHECKED:** the same limit as the SAIRNmechanical files above — no `psql`,
no parser, so this is structurally sound by inspection and **not** *accepted by
the server*.
