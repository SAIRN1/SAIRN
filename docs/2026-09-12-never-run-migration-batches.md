# The never-run migrations — the send order, and what was checked before sending

**2026-09-12 (Hank).** `tools/schema_snapshot_freshness.py` resolves 89 tables
declared in `sql/` as NEVER RUN against the fresh 2026-09-11 capture. **31 of
them are queried by live `api/` code** — that is the set below. The other 58 are
real but no shipped code path reaches them yet.

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
| 1 | `stonedesk_public_surface_schema.sql` | 5 | StoneDesk | 2026-09-12 |
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

## The standing risk this set illustrates

`api/sd-data.js` answers a read against a missing table with
`provisioned: false`, and the client treats that as *"nothing to hydrate"*. So a
never-run migration is indistinguishable, from inside the app, from a customer
who has not entered any data yet — no error, no warning, and every write
answering 503 into a console nobody is reading. That is why these sat for ten
days without anyone noticing, and why the detection had to come from comparing
`sql/` against a live capture rather than from the app.
