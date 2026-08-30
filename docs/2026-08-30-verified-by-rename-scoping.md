# Renaming `verified_by` to `loaded_by`: what it would actually take

**2026-08-30 (Hank). Scoping only — nothing touched.** Deferred on 2026-08-29
when the field's comments were corrected to say what it records; Michael asked
for the real cost before any of it happens.

**Headline: the migration is trivial and the coordination is not.** 33 rows of
column data and a metadata-only DDL, against 7 production code sites, 3 test
files, 2 gate tools that subtract the field **by name**, and one case that is
not a column at all and is where the whole cost sits.

---

## 1. What the field is, in one paragraph

`verified_by` is stamped server-side from the caller's session on every write.
It records **who was signed in when the row was written**, not who verified the
content — the schema comments claimed the latter until they were corrected. The
real provenance already lives in `data.authority` (citation, url,
`read_on`/`retrieved_at`), which is required and validated. The Ohio HSSA
contingency rules loaded on 2026-08-29 carry `verified_by: 'rf-verify-admin'`, a
disposable verification account; nobody of that name verified Ohio's Home
Solicitation Sales Act.

## 2. The five columns — the easy part

| table | app | rows on the demo licence |
|---|---|---|
| `alf_compliance_rules` | SAIRNcare | 16 |
| `alf_payer_rules` | SAIRNcare | 6 |
| `dnt_cred_rules` | SAIRNdental | 6 |
| `rf_cert_rules` | SAIRNroofing | 3 |
| `rf_contingency_rules` | SAIRNroofing | 2 |

`alter table … rename column` is **metadata-only in Postgres** — no table
rewrite, no lock of consequence at this size, instantly reversible. 33 rows
total. The data volume is not the cost and never will be.

## 3. The sixth case is not a column, and it is the whole problem

SAIRNlaw does not have a `verified_by` column. It has
**`data.authority.verified_by`, a key inside the jsonb blob**, on
`law_deadline_rules` (293 rows) and `law_holidays` (133 rows).

Three consequences, and the second is the one that would bite:

1. **Renaming it is an UPDATE that rewrites every blob**, not a DDL. Still fast
   at 426 rows, but it is a data migration rather than a metadata change, and it
   is not reversible by re-running the inverse without care.
2. **IT CHANGES THE CONTENT HASH OF EVERY SAIRNLAW ROW.**
   `api/reference-fingerprint.js` and `tools/sairn_load_state_check.py` both
   compute a hash over the blob with `authority.verified_by` removed *by that
   name*. Rename the key and the strip silently stops matching, so the hash
   changes for all 426 rows and the load-state gate reports **every SAIRNlaw row
   STALE** on the next run. That is the exact cry-wolf failure the gate was
   built to avoid, caused by the fix for a different problem.
3. It is also the reason the field cannot simply be dropped: the strip has to
   keep working through the transition, under whichever name.

## 4. Every site that would have to change, counted

`grep` over `api/` and `tools/`: **32 references in 10 files.** One is a false
positive — `api/_lib/roofing-programs.js` has `verified_by_app`, an unrelated
disclosure flag. The real set:

**Writes (5)** — all stamp `session.employee_id`:
- `api/sd-data.js` — `rf_cert_rules` (3015), `rf_contingency_rules` (4126),
  `alf_payer_rules` (4942), `alf_compliance_rules` (5152), `dnt_cred_rules`
  (6033)
- `api/legal-deadlines.js` — both `add_rule` and `add_holidays`, into
  `data.authority`

**Reads (4)** — the field is named in the PostgREST `select=` list *and* in the
response-shaping line, so each read site is two edits:
- `api/sd-data.js` at 2974/2981, 4871/4881, 5089/5099, 5984/5991

**Response bodies (2)** — `sd-data.js` 4951 and 5161 echo `verified_by` back to
the client after a write.

**Gate tools (3)** — the by-name subtractions:
- `api/reference-fingerprint.js` — `INERT_COLUMNS`
- `tools/sairn_load_state_check.py` — `INERT_COLUMNS` **and** the
  `authority.verified_by` strip in `content_hash()`
- `tools/sairn_build_load_gates.py` — `INERT_COLUMNS` (superseded file, kept for
  provenance; would need updating or an explicit note saying it is frozen)

**Tests (3 files)** — `dental-credentials-endpoint.test.js`,
`roofing-agreements-endpoint.test.js`, `roofing-credentials-endpoint.test.js`
assert on the field.

**UI: ZERO.** No `.html` app renders it. `sairnroofing.html`'s single hit is
`verified_by_app`, the false positive above. **This is the single biggest cost
reduction in the whole exercise** — there is no user-visible surface, no label
to change, no customer to re-teach.

## 5. The ordering problem

A column rename and a code deploy cannot be atomic. Between the two, writes
naming the old column fail.

**Option A — rename and deploy fast.** One DDL, one push. Writes 400 for the
deploy window (~1–2 minutes on Vercel). Acceptable only because every affected
licence is a demo or verification tenant today; it would not be acceptable once
a paying customer is on any of these five tables.

**Option B — expand/contract, zero downtime.** Add `loaded_by`; deploy code that
writes both and reads `loaded_by` with a fallback; backfill; deploy code that
writes only `loaded_by`; drop `verified_by`. Four steps, two deploys, no window
where writes fail. This is the standard shape and is what a customer-bearing
table deserves.

**Either way the gate tools must change in the SAME step as the thing they
subtract**, or the load-state gate goes red platform-wide for a reason that has
nothing to do with load state.

## 6. What I would do

**Do it as Option B, bundled with the next migration any of those five tables
needs for another reason — not as a standalone change.**

Reasoning:

1. **The honesty problem is already fixed.** Every declaration and write path
   now says what the field records; the misleading claim is gone from the
   schemas and from `api/legal-deadlines.js`, which had the worst of it. What
   remains is a *name* that reads wrong, and a name is a smaller lie than a
   comment that asserted a verification which never happened.
2. **The risk is concentrated in the thing that would catch a real defect.**
   Both gate tools subtract this field by name. A rename that misses one of them
   turns the platform's only load-state check into noise — and the failure is
   silent and looks exactly like real drift.
3. **There is no user-visible surface**, so nothing is gained today by moving
   fast, and nothing is lost by waiting for a migration that is happening
   anyway.
4. **The line not to cross is a paying customer on any of the five tables.**
   Every affected licence today is a demo or verification tenant. Before the
   first real customer is provisioned on SAIRNcare, SAIRNdental or SAIRNroofing,
   this should be done — after that, Option A stops being available and Option B
   gets more expensive to schedule.

**What I would NOT do:** rename the jsonb key inside SAIRNlaw's `data` at the
same time as the five columns. They are different operations with different
risks — one is metadata, the other rewrites 426 blobs and moves every content
hash on the platform's largest reference table. If both are wanted, do the
columns first, confirm the gate is still green, then do the blob key on its own
with a deliberate reload afterwards.

## 7. Estimate

| piece | effort |
|---|---|
| 5 column renames (Option B: add, backfill, drop) | 3 short SQL files |
| `api/sd-data.js` — 5 writes, 4 read pairs, 2 responses | ~15 edits, mechanical |
| `api/legal-deadlines.js` — 2 writes | 2 edits, jsonb key only |
| 3 gate-tool sites | 3 edits, and the ones that must not be missed |
| 3 endpoint test files | ~6 assertions |
| live re-verification per app + gate run | the usual |

**Half a session for the columns.** The SAIRNlaw blob key is its own half-session
because it ends in a full reload of 426 rows and a gate run to prove the hashes
settled. *(Row count re-measured — see §8.)*

---

## 8. Re-check 2026-08-30, later the same day (Hank) — KEEP DEFERRING

**Verdict: the trigger has not arrived. Nothing was touched.** Michael asked
whether the "next migration those five tables need anyway" moment had come. It
has not, and one near-miss is worth naming so the next reader does not mistake it
for one.

### What was checked, and what it returned

| check | result |
|---|---|
| Commits altering any of the five schema files since §1 was written | **none** beyond the comment alignment itself |
| Pending SQL that `alter`s any of the five tables | **none** — the only `alter table` lines in those files are the original `enable row level security` statements |
| `sql/append_only_grant_audit.sql`, `unused_delete_grant_revoke_2026-08-24.sql`, `full_crud_truncate_sweep_2026-08-24.sql` — all three name the five tables | **all RUN 2026-08-25**, each file says so in its own header |
| `sql/sairncare_all_remaining_migrations.sql` — ten unrun SAIRNcare migrations | **real, still unrun, and NOT a bundling opportunity** — see below |
| UI surface | **still zero**, re-verified |

### THE NEAR-MISS, AND WHY IT IS NOT THE TRIGGER

`sql/sairncare_all_remaining_migrations.sql` is a genuine unrun migration paste
for SAIRNcare, and two of the five columns live on SAIRNcare tables. It looks
like the bundling opportunity this deferral was waiting for. **It is not**, on
two grounds:

1. **It does not touch either table.** Every `create table if not exists` in that
   file is for a table that does not exist yet — residents, staff, MAR, billing,
   incidents, the employee-auth table. `alf_compliance_rules` and
   `alf_payer_rules` appear in the file **only in its explanatory header**, as
   two of the four tables that already exist.
2. **Adjacency does not reduce the cost being deferred, and this is the point.**
   The DDL was never the expensive part — §2 says so. The cost is the code deploy
   and the two gate tools that subtract this field **by name**. Running a rename
   in the same SQL-editor session as an unrelated paste saves one paste and
   nothing else, while adding a second reason for that session to go wrong.

**The trigger is a migration that must ALTER one of the five tables**, not one
that happens to run near them.

### Two numbers in this document have already moved

Both are snapshots and should be re-measured rather than cited.

- **§7 says "a full reload of 426 rows". It is 490 today** — 352
  `law_deadline_rules` plus 138 `law_holidays`, read live from
  `rules_fingerprint`. Mississippi and New Mexico were seeded between the two
  measurements. **Every jurisdiction seeded adds rows carrying
  `authority.verified_by`, so the one-time blob rewrite grows with the seeding
  programme** — about 15% in a single day at the current pace. It is still
  trivial in absolute terms and it does **not** change the recommendation, but
  the direction is one-way and worth saying out loud.
- **§4 says "32 references in 10 files". Re-counted today with the
  `verified_by_app` false positive excluded, the real set is 37 references in 8
  files:** `api/sd-data.js` 19, `api/legal-deadlines.js` 6,
  `tools/sairn_load_state_check.py` 3, `api/reference-fingerprint.js` 2,
  `tools/sairn_build_load_gates.py` 1, and three endpoint tests (2 + 3 + 1).
  **The false positive is now 3 hits across TWO files, not one** —
  `api/_lib/roofing-programs.test.js` asserts on `verified_by_app` as well as the
  module that emits it. A careless `grep -l verified_by | xargs sed` would sweep
  both into the rename and break a passing test for no reason.

### One new piece of evidence, and it STRENGTHENS the case for waiting

§3.2 predicted that renaming the jsonb key would make the load-state gate report
every SAIRNlaw row STALE. That was a prediction; **it now has a same-day
precedent on the very same object.** Mississippi's first load stored all 11 rows
with a server-stamped `authority.retrieved_at`, because the seed rows omitted the
field and `add_rule` defaults it. `tools/sairn_load_state_check.py` reported
**all 11 as STALE within minutes of the load**. The dates were correct throughout
— the drift was provenance, not arithmetic — and the gate caught it anyway.

That is the gate working exactly as designed, on `data.authority`, today. It is
also a demonstration of how easily that object drifts: one absent field, and a
whole jurisdiction goes red. A rename of a key inside it is the same class of
event at 490 rows instead of 11, and it must land in the **same step** as the
change to the tools that strip it.

### The line not to cross — still uncrossed, on evidence I can actually stand behind

Every licence key named anywhere in the repo against the five tables is a house
tenant: `DNT-PINNACLE-2026`, `RF-PINNACLE-2026`, `ALF-TEST-2026`. "PINNACLE" is
the internal canonical tenant name used across every SAIRN app, not a customer.
The only two keys in the repo that look like third parties — `SD-PARTNER-2026`
and `BLD-INDUSTRIES-2026` — are StoneDesk and SAIRNbuild, neither of which has
any of the five tables.

**That is repo evidence, not a live tenant audit.** Nobody has queried
`license_keys` for a customer row on SAIRNcare, SAIRNdental or SAIRNroofing, and
that query is what would actually settle it. Stated plainly rather than rounded
up to "no customers", because this is the one fact the whole deferral rests on.

### Re-check when any ONE of these becomes true

1. A migration is written that must `alter` `alf_compliance_rules`,
   `alf_payer_rules`, `dnt_cred_rules`, `rf_cert_rules` or
   `rf_contingency_rules`.
2. A paying customer is about to be provisioned on SAIRNcare, SAIRNdental or
   SAIRNroofing. **This is the hard one** — after it, Option A stops existing and
   Option B gets more expensive to schedule, and nothing will announce it.
3. Either gate tool is being edited for another reason, since the by-name
   subtraction is the risk and touching it deliberately is cheaper than touching
   it incidentally.
4. Someone proposes reading `verified_by` into a UI. The zero-surface fact in §4
   is doing a lot of work in this recommendation and it would stop being true.
