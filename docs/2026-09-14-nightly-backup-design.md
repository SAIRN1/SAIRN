# The nightly backup, and the restore that proves it is one

**Written 2026-09-14 (Fourth).** Michael's decision, same day. Supabase is on the
**free tier**: no automated database backups at all, one-day log retention.
Before this there was no recovery path for `sv_controlled`, `law_trusttx` or
`dnt_charges` — a DEA-relevant controlled-substance register, attorney client
trust money, and dental charge history.

**Files:** `.github/workflows/nightly-backup.yml`, `sql/backup_reader_role.sql`.
**Nothing has run.** Every secret it needs is absent and the role has not been
created. See *What is unproven* at the end, which is the section to read first.

---

## The shape

    pg_dump ──pipe──> age ──> R2 (encrypted, 30-day rolling)
                               │
                               └─> restore into a throwaway Postgres
                                   + PostgREST
                                   + tools/restore_coherence_check.js
                                   └─> a dump that cannot restore clean
                                       FAILS THAT NIGHT

**The second half is the point.** A dump that completed is not a backup; it is a
file. The only thing that makes it a backup is having read it back, and the only
useful time to discover otherwise is any night except the one where it matters.

**The nightly restore test is affordable because of item 35.** The audit
checkpoint chain is a fingerprint carried *inside the data*, so the restored copy
is checked against its own past — **no baseline has to be captured at backup
time**, and nobody has to maintain one. Without that, a nightly coherence check
would need a trustworthy row count from production at the moment of the dump,
which is a second thing to get right and a second thing to go stale.

---

## The three silent failures it is built against

**1. An empty dump that restores perfectly.** Every audit table on this platform
carries `enable row level security`. RLS applies to every role except a
superuser, the owner, and a role with `BYPASSRLS` — and `service_role` bypasses
it only because Supabase grants it that. **A fresh SELECT-only role does not.**
`pg_dump` run as one would emit the schema, emit **zero rows** for every
RLS-protected table, and **exit 0**. The file would look right in a listing and
restore without an error.

So `sql/backup_reader_role.sql` grants `BYPASSRLS` and says why at length, and
two independent things would catch it if the role were ever recreated without
it: a **50 KB size floor** on the encrypted dump, and the coherence check, whose
checkpoint digests cannot match an empty table.

**2. A dump nobody ever read back.** Addressed by restoring every night rather
than on demand.

**3. Plaintext on disk.** `pg_dump` is piped straight into `age`; the
unencrypted bytes never become a file, on the runner or anywhere else.
`set -o pipefail` is load-bearing here — without it the pipeline's exit status is
`age`'s, and a `pg_dump` that died half way through produces a perfectly valid
encrypted file containing half a database with a zero exit code.

---

## What the encryption protects, and what it does not

The `age` identity lives in a GitHub secret **because the same workflow has to
decrypt in order to run the restore test.** So:

- **It protects the dump at rest in R2** — against a leaked bucket credential, a
  misconfigured bucket, or R2 itself.
- **It does not protect against anyone who already has this repository's Actions
  secrets.** They can decrypt every backup.

That is a real limit and it is stated rather than implied by the word
"encrypted". Closing it means a key the CI does not hold, which means the restore
test cannot run unattended — and a backup nobody restores is the failure this
whole design exists to prevent. **The trade is deliberate and it is the right way
round**, but somebody should know it was made.

---

## The credential

A **new, dedicated role**, not the shared service-role key: `sairn_backup_reader`,
`LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT BYPASSRLS`, `SELECT` only,
member of nothing, with `ALTER DEFAULT PRIVILEGES` so tables created later are
covered too — **the half that is usually forgotten**, and whose absence is the
same silent-omission shape as the RLS one, arriving later.

### `FOR ROLE` is not optional, and leaving it off is the same bug one level in

**Corrected 2026-09-14 after review, before the role was ever created.**
`ALTER DEFAULT PRIVILEGES` **without** `FOR ROLE` applies only to objects created
by the role running the statement. Run it as `postgres` and it covers exactly
what `postgres` goes on to create — and nothing made by anything else.

On Supabase that is not a corner case: the dashboard's table editor, the
migration runner and several extensions create objects as `supabase_admin`. A
table created that way would carry no grant for the backup role, `pg_dump` would
skip it **without an error**, and the backup would be missing a table while
exiting zero — the identical shape as the RLS gap, arriving months later and
only for tables added after today.

Both grantors are now named explicitly, and **a `FOR ROLE` that cannot be applied
raises rather than continuing**: the clause requires membership in the target
role, `postgres` is not always a member of `supabase_admin`, and silently
skipping it would leave exactly the gap it was added to close. *Could not set it*
is a third state and it is not *set*.

**The verify block is what proves it took**, not the statement: query 2b reads
`pg_default_acl` and must return **one row per grantor**. A single row there is
the failure, not a pass — it means only the role that ran the file is covered.

**Why not reuse `service_role`:** a backup job needs to read everything and
should be able to do nothing else. `service_role` can write to every table on the
platform. A credential that leaks from CI should cost a disclosure, not a
database.

Creating it is the one step a human does by hand, deliberately: a workflow that
could mint its own database credentials would be a bigger hole than the one this
closes.

---

## Two choices that look like details and are not

**The restore decrypts the local file, not the R2 copy.** Pulling it back would
test R2 as well, and a step that tests two things cannot say which failed. The
R2 round trip deserves its own check; conflating them would make every network
blip read as a corrupt backup.

**Retention runs last, and only after the restore passed.** A bucket lifecycle
rule would delete on a schedule this job cannot see — so a month of failing
backups would quietly age out the last *good* one. Running it here means
retention only advances on a night that produced a dump which demonstrably
restores. The step also prints how many remain and fails if that is zero.

---

## What is unproven, and it is most of it

**This workflow has never run.** It cannot be run from a developer machine and
every secret is absent. In particular:

- **The restore step is the one most likely to need fixing.** A real Supabase
  dump may reference extensions, schemas or roles beyond the three created here
  (`service_role`, `anon`, `authenticated`). The first run's log is the only
  thing that will say which.
- `age-keygen` is assumed to ship with the Ubuntu `age` package. If it does not,
  the recipient derivation fails on the first run and is a one-line fix.
- The PostgREST container is given `PGRST_DB_ANON_ROLE=postgres`, i.e. the
  throwaway is fully open. That is acceptable for a container that exists for
  ninety seconds inside a job and holds a copy of data the job already has in
  plaintext — but it is not a pattern to copy anywhere else.
- **R2's free tier and egress terms are taken from the decision, not verified
  here.** The design leans on no-cost egress because restore-testing means
  pulling the dump down regularly.

**The first successful run is the thing to check, not this document.** Read the
restore step's output and the coherence verdict; a green tick on a job whose
coherence check exited 2 would mean nothing was verified, which is why the
workflow treats exit 2 as a failure rather than as "no findings".
