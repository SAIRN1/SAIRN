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
settled.
