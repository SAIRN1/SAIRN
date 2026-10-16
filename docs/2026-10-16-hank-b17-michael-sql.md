# b17 — the SQL package for Michael, and three re-derived facts

**Written 2026-10-16 by hank, batch b17.** Everything here needs a human in
the Supabase SQL editor or a decision only Michael can make. Nothing in it has
been run — this document is the request, not a report.

**Read §1 first if you are about to do the Stedi backfill.** Two of its three
items block that, and one of them is a decision rather than a query.

---

## 1. THE STEDI BACKFILL IS BLOCKED ON TWO THINGS, AND NEITHER IS A MIGRATION

### 1.1 Which licence owns the one legacy `sc_credentials` row

**The state, as of the last measurement anybody ran:** `legacy_rows = 1` on
`sc_credentials` — one Stedi API key still encrypted under
`sha256(SD_AUTH_SECRET)` rather than under `SD_ENCRYPTION_KEY`. Step 4a of the
key rotation (`api/_lib/auth.js`) gates clearing `SD_AUTH_SECRET_PREVIOUS` on
that count reaching zero, so the rotation cannot finish while it stands.

**`sql/legacy_ciphertext_census.sql` PART 2 already returns `license_hash` —
and a 64-character hex hash does not tell you which agency to call.** That is
the gap. The hash is `sha256(<the raw licence key>)`, so it can be joined back
to `license_keys` and named, and the census does not do that join.

**THE QUERY, and it adds nothing to the census's own privacy posture** — no
plaintext, no ciphertext, and no employee identity beyond the id the app
already uses as a key:

```sql
-- WHICH LICENCE OWNS THE LEGACY STEDI ROW(S).
-- Run against the SAME database the app reads. The jsonb path is the nested
-- one (api/sc-credentials.js writes next[service] = {enc: ...}), NOT a
-- top-level data->>'enc' -- that spelling reports a false zero for every
-- possible database state and is why this was unmeasured for weeks.
select c.license_hash,
       k.key           as licence_key,
       k.app_id,
       k.customer_email,
       k.status,
       c.credential_id,
       e.k             as service,
       'legacy'        as format,
       length(e.v->>'enc') as ciphertext_len   -- a length, never the value
  from public.sc_credentials c
  cross join lateral jsonb_each(coalesce(c.data, '{}'::jsonb)) as e(k, v)
  left join public.license_keys k
         on k.license_hash_cached = c.license_hash          -- see the NOTE below
 where jsonb_typeof(e.v) = 'object'
   and e.v->>'enc' is not null
   and e.v->>'enc' not like 'v2.%'
 order by c.license_hash, c.credential_id, e.k;
```

**NOTE ON THE JOIN, and it is the one thing I could not settle from here.**
`license_keys` is keyed by the RAW `key`, and `sc_credentials` by the HASH. I
do not know whether `license_keys` carries a cached hash column. **If the join
above errors with `column "license_hash_cached" does not exist`, use this
instead** — it computes the hash and needs `pgcrypto`, which this database
already uses elsewhere (`encode(digest(...))` appears in the b10 residue SQL):

```sql
  left join public.license_keys k
         on encode(digest(k.key, 'sha256'), 'hex') = c.license_hash
```

**If BOTH forms fail, the answer is still reachable** and does not need a join
at all — there are few enough licences to check one at a time:

```sql
-- Paste the hash the census returned into the second line.
select key, app_id, customer_email, status
  from public.license_keys
 where encode(digest(key, 'sha256'), 'hex') = '<the 64-char hash>';
```

**WHAT TO DO ONCE IT IS NAMED.** The Stedi key is re-enterable and an
undecryptable row answers 503 rather than corrupting anything, so the fix is a
conversation, not a migration: ask that agency to re-enter their Stedi API key
in the app, which writes it under the dedicated key in the `v2.` format, then
re-run the census and expect `0`. **Then and only then** clear
`SD_AUTH_SECRET_PREVIOUS`.

**`SD_AUTH_SECRET_PREVIOUS` HAS NOT BEEN CLEARED AND MUST NOT BE** until that
count is zero. Nothing in b16 or b17 touched it.

### 1.2 `SC-PINNACLE-2026` and the trial expiry — MEASURED, AND THERE IS PROBABLY NOTHING TO RUN

**This was dispatched as "SC-PINNACLE-2026 trial extension SQL (or exempt demo
licences from expiry)". Measured before writing any: the expiry gate is
INERT ON EVERY LICENCE ON THE PLATFORM, and has always been.**

`trial_ends_at` is **not a column** on `license_keys`. Two independent
measurements, neither of them mine:

* a run of `sql/demo_license_keys_seed.sql` failed with
  `42703: column "trial_ends_at" does not exist`
* `db/schema_snapshot.json`, captured live 2026-09-02, lists eleven columns
  and none of them is it

So `api/_lib/license.js` reads it as `null` (the query is `select=*`
deliberately, so a newly-added column is read if present), and all three gates
— `api/sd-data.js`, `api/sd-render.js`, `api/_lib/sd-store.js` — short-circuit
on `lic.trial_ends_at &&` and have **never reached the 402**.
`api/license-trial-gate.test.js` pins that as-is, so the day the column is
added that suite goes red and names all three handlers.

**THE DATE ON THIS FACT IS 2026-09-02 AND IT IS THE THING TO CHECK, not the
conclusion.** `sql/license_keys_trial_ends_at_2026-09-16.sql` exists in the
repo and would add the column; whether anybody ran it is not knowable from
here. **One query settles it:**

```sql
-- IS THE COLUMN THERE AT ALL? Expect ZERO ROWS -- that is the state the whole
-- of §1.2 assumes, and if it returns a row the rest of this section applies.
select column_name, data_type
  from information_schema.columns
 where table_schema = 'public' and table_name = 'license_keys'
   and column_name = 'trial_ends_at';
```

**IF IT RETURNS ZERO ROWS: there is nothing to run and nothing expiring.** The
demo licences are not at risk and `SC-PINNACLE-2026` does not need extending.
Stop here.

**IF IT RETURNS A ROW**, then one of these two, and the choice is yours:

```sql
-- OPTION A -- EXTEND THE ONE LICENCE. Narrow, reversible, and has to be
-- redone every time the date passes.
select key, app_id, status, trial_ends_at        -- LOOK FIRST
  from public.license_keys
 where key = 'SC-PINNACLE-2026';

update public.license_keys
   set trial_ends_at = timestamptz '2027-12-31 23:59:59+00'
 where key = 'SC-PINNACLE-2026';

select key, status, trial_ends_at                -- CONFIRM
  from public.license_keys
 where key = 'SC-PINNACLE-2026';
```

```sql
-- OPTION B -- EXEMPT EVERY DEMO LICENCE, by nulling the date rather than
-- pushing it out. `trial_ends_at IS NULL` is the condition all three gates
-- already short-circuit on, so a null is a permanent exemption and needs no
-- code change and no second visit.
--
-- LOOK FIRST. This is the row set about to change -- read it before running
-- the update, because a predicate is only safe once you have seen what it
-- does NOT match.
select key, app_id, customer_email, status, trial_ends_at
  from public.license_keys
 where key like '%-PINNACLE-2026' or key like '%-AUDIT-2026'
 order by key;

update public.license_keys
   set trial_ends_at = null
 where (key like '%-PINNACLE-2026' or key like '%-AUDIT-2026')
   and trial_ends_at is not null;

-- CONFIRM: expect zero rows.
select key, trial_ends_at from public.license_keys
 where (key like '%-PINNACLE-2026' or key like '%-AUDIT-2026')
   and trial_ends_at is not null;
```

**I RECOMMEND OPTION B AND THE REASON IS NOT TIDINESS.** Option A sets a date
that will pass, on a licence used for live verification probes — and the
failure mode when it passes is a **402 on every demo request**, which reads
exactly like a broken deployment to whoever hits it next. The demo and audit
licences are not trials; a trial date on them is wrong data, and nulling it
says so. **Option B's predicate is a `like` over key names and that is its
one weakness** — read the `select` above and confirm the row set is the one you
mean before running the `update`.

**WHAT I DID NOT DO: run any of it.** No SQL was executed, no row was read
from production, and the "zero rows" expectation in the first query is a
prediction from a 2026-09-02 snapshot, not a measurement taken today.

---

## 2. THE PROBE ROW: `ZZ-B12-SIZE-PROBE` IS IN `public.sd_photos`, NOT `leg_custodylog`

**Named here because the two b12/b10 probe rows get conflated, and the
difference decides whether a human is needed at all.** Re-derived 2026-10-16
by reading the record written by the run that created each one.

| row | table | id column | licence | removable by the app? |
|---|---|---|---|---|
| `ZZ-B12-SIZE-PROBE` | **`public.sd_photos`** | `photo_id` | `SD-AUDIT-2026` | **YES** |
| `ZZ-B10-APPEND-PROBE` | `public.leg_custodylog` | `custodylog_id` | `LEG-PINNACLE-2026` | **NO — human only** |

**`leg_custodylog` is the one that needs the SQL editor, and it is NOT the b12
row.** `sql/sairnlegacy_data_schema.sql` gives `service_role` no DELETE on
`leg_custodylog` and the handler refuses an edit to every role including the
owner, so that row cannot be removed by the API, by any tool, or by any probe.
That is the append-only rule working as designed and the cost of having proved
it live.

**`sd_photos` is not like that.** It carries a `soft_delete` verb
(`api/_resources/stonedesk.js`) and `service_role` holds DELETE on the table,
so the b12 row does not need a human — though the SQL below is unambiguous and
does not depend on a session, which is why it is given anyway.

```sql
-- SELECT FIRST. Expect EXACTLY 1. Anything else means something other than
-- the b12 probe wrote here and the delete below is wrong.
select photo_id, license_hash
  from public.sd_photos
 where photo_id = 'ZZ-B12-SIZE-PROBE';

-- THEN:
delete from public.sd_photos where photo_id = 'ZZ-B12-SIZE-PROBE';

-- CONFIRM. Expect 0.
select count(*) from public.sd_photos
 where photo_id = 'ZZ-B12-SIZE-PROBE';
```

**AND THE b10 ROW, which does need you.** The full SELECT-then-blast-radius
-then-DELETE sequence is in
`docs/live-residue/2026-10-14-hank-b10-live-gate-probe.json` and is not copied
here, because a destructive predicate copied by hand into a second document is
how the two came to be confused in the first place. **Run it from that file.**

**Both rows are harmless where they are.** Neither is on a paying customer's
licence and neither affects any computation. This is housekeeping, not a fault.

---

## 3. TWO SCHEMA FILES b17 NEEDS RUN, AND WHAT REFUSES UNTIL THEY ARE

Both are in the repo and **neither has been run.** Until they are, the
pay-period freeze cannot be used at all — and it refuses loudly rather than
failing quietly, which is the point.

### 3.1 `sql/sairnsenior_period_closings_schema.sql` — NEW in b17

The append-only ledger of pay periods closed and reopened. Replaces the
`sen_settings.payroll_closed_periods` key, which the app now refuses by name
because that path **replaces** a settings row and could silently un-freeze
wages already paid (fourth's b26 finding H3, driven through the real endpoint).

**Until it is run:** any attempt to close a period answers
`503 NOT_PROVISIONED` naming the file. A pay run still works and simply reports
nothing as frozen, which is true — no period has ever been closed.

**The file carries its own verification block, and step 2 is the one that
matters:** the grants must come back as **exactly `INSERT, SELECT`**. An UPDATE
or a DELETE there reopens H3 through the door the table exists to close.

### 3.2 `sql/sairnsenior_audit_log_schema.sql` — EXISTS, STILL NOT RUN

b17 adds two event types to its CHECK constraint: `pay_period_closed` and
`pay_period_reopened`.

**Until it is run:** closing or reopening a period answers
`503 AUDIT_UNAVAILABLE` and names this file. **That is deliberate and it is a
departure from how the rest of the platform audits.** `api/_lib/audit.js` is
best-effort for credential grants on purpose — a logging outage must never lock
somebody out of their own app. The trade runs the other way for a wage freeze:
it is not urgent, it is retryable a minute later, and the entire reason it is
audited is that it moves money. **A freeze nobody is recorded as having made is
worse than one that has to be retried.**

### 3.3 Order, and the one thing to check after

Run **3.2 first, then 3.1** — a close needs the audit row to land before the
ledger row is written, so a provisioned ledger with no audit table refuses
every close and looks like a broken feature.

Then confirm live, which is the real proof — a clean SQL run is not evidence
the app can reach it:

```
POST /api/sd-data  {"action":"read","resource":"sen_period_closings"}
  with a valid SEN- licence and an OWNER session.
  Before: 503 / provisioned:false
  After:  200 {"ok":true,"data":[],"provisioned":true}
```

**The FLIP is the evidence, not the absence of an error.**

---

## 4. A CITATION RE-DERIVED, recorded because it was routed as an item

**`set_active:343`.** fourth's b18 verdict in `docs/tier-a-reviews.json` says
*"while set_active:343 already does this check"*, pointing at
`api/sen-auth.js`. Re-derived at HEAD on 2026-10-16:

* `api/sen-auth.js:343` is a **PIN and role validation line**, not `set_active`
* `set_active` is at **`api/sen-auth.js:439`**
* **the guard was never in that file at all** — it is the `LAST_ADMIN` refusal
  in `api/_lib/employee-lifecycle.js`, which every app's `set_active` goes
  through

**A citation that lands on a validation line reads as verified to anybody who
does not open it.** Same class as the `audit.js:40` citation corrected in
`api/sd-auth.js` this batch: `:40` had drifted onto a comment banner. Both are
now anchored to the **named constant** instead of a line number, which is the
form that does not rot.

**Nothing in the register was rewritten.** That verdict is a discharged review
by another session, and `docs/tier-a-reviews.json` is append-only across four
clones. The re-derivation is recorded here and in a comment at the branch
itself, where the next reader of the code will find it.

**AND THE FINDING THAT CITATION BELONGED TO IS CLOSED.** N2 — `setup` could
demote the last owner by a different door than `set_active` — is fixed in
`api/sen-auth.js`, and `api/_lib/setup-demotion-guard.test.js` drives it
(green at HEAD, 2026-10-16).

---

## 5. What this document does NOT claim

* **No SQL was run.** Not one query here has been executed against any
  database by me.
* **No production row was read.** Every count quoted is from somebody else's
  earlier measurement, with its date attached so you can distrust it on age.
* **The `license_keys` join in §1.1 is unverified** and three forms are given
  because I do not know which column exists. The first one may simply error.
* **§1.2's "expect zero rows" is a prediction**, from a schema snapshot taken
  2026-09-02. If it returns a row, the section's conclusion is wrong and its
  options apply.
* **Nothing here was live-verified after the fact**, because none of it has
  been run yet.
