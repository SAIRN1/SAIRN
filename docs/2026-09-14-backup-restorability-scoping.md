# Item 65 — there is no recovery path, and that is the finding

> ## ANSWERED 2026-09-14 — Michael, directly: **Supabase FREE TIER, one-day log retention.**
>
> **Source: confirmed by the platform owner on 2026-09-14.** Not inferred from a
> dashboard, not read off an invoice, and not re-derivable from this repo —
> which is why it is recorded here with its date and its source rather than left
> as a fact somebody has to re-establish.
>
> **The free tier takes no automated database backups.** So this item is NOT
> "backup restorability is unverified". It is:
>
> ### There is no real recovery path beyond 24 hours for `sv_controlled`, `law_trusttx` and `dnt_charges`, among others.
>
> A DEA-relevant controlled-substance register, attorney client trust money, and
> dental charge history. The one-day log retention is **not** a recovery path —
> a log says what a request claimed, not what a row contained, and it cannot
> reconstruct a table.
>
> Everything below was written before that was confirmed. It is left standing
> rather than rewritten, because the *reasoning* that produced the question is
> what makes the answer readable, and because the sizing of 65a does not change.
> **What DOES change:** 65c is not blocked on a plan decision any more — there
> is nothing to restore, so the question is whether to create backups at all,
> which is a spend decision, not a testing one.

**Written 2026-09-14 (Fourth).** Scoped before building, and the measurement
moved the question before it moved the answer.

The ask was a periodic job that restores a real Supabase backup into a scratch
environment and checks the restored data for logical coherence. Half of that is
blocked on things that do not exist, and the other half turns out to be both
buildable and more necessary than it looks.

---

## What exists, measured

| Thing | State |
|---|---|
| Any backup mechanism in this repo | **none** |
| Any disaster-recovery or restore document | **none** |
| Any restore tooling | **none** — `grep` over `tools/` finds `restore` only in `condition_coverage.py`, which restores FILES it mutated during a probe |
| A scratch/second environment to restore INTO | **none** |
| `db/schema_snapshot.json` | **structure only** — 380 tables, column NAMES and `_constraints`. No data, no types, no row counts. Hand-pasted from `sql/schema_snapshot_query.sql`, and `docs/2026-09-13-stackup-traverse-drift-scoping.md` records that that human relay has failed at least twice |

**So there is nothing here that takes a backup, nothing that restores one, and
nothing that would notice either.**

---

## The reframe: "does the backup restore" presumes a backup

Nobody has established that one exists. Supabase's backup behaviour is a
**property of the plan**, not of this repo: the free tier takes no backups at
all, paid tiers take daily backups with a short retention, and point-in-time
recovery is a higher tier again. **Which plan this project is on is not written
down anywhere in the repo**, and it is not a thing to guess at.

That matters because the two possible answers are not variations of one finding:

- **If there is a paid plan with daily backups**, item 65 is what it says on the
  tin: the backups exist, nobody has ever restored one, and *a backup nobody has
  restored is a hypothesis*.
- **If this is the free tier, there is no backup at all** — and the finding is
  not "restorability is unverified", it is that a platform holding a
  DEA-relevant controlled-substance register, attorney trust-account balances
  and dental charge and payment history has no recovery path whatsoever. That is
  a different severity and a different conversation.

**This is the decision, and it is the first one: what does the Supabase plan
actually provide?** Everything below is sized against the first answer; under
the second, the item is not a checker at all.

---

## The half that is blocked, and precisely on what

A restore needs somewhere to restore TO. On Supabase that is a second project
(cost, credentials, and a decision about whether production data may be copied
into it at all — the register is DEA-relevant and the dental tables are PHI-
shaped). A local Postgres avoids the vendor cost and loses the thing being
tested: **restoring a Supabase backup into ordinary Postgres does not test
Supabase's restore, it tests `pg_restore`.**

So the target environment is a decision with a privacy dimension, not a
technical detail to pick quietly. **Copying production rows into a scratch
project is itself a data-handling act** and should be decided as one — the
honest default is to restore into a project nobody but the platform owner can
reach, and to say so in the DPA if it becomes routine.

---

## The half that is buildable now, and it is the one that matters

**Nothing would catch a bad restore even if one happened**, and this is the
finding that makes the coherence checker necessary rather than nice:

    foreign-key clauses across every schema file in sql/ :  1
    tables declared across the same files                : 459

**One.** `sairn_agents(id)`, and nothing else. Every other relationship on this
platform — a draw to its job, a controlled-substance entry to its licence, a
charge to its patient — is held by convention in application code, not by the
database.

The consequence for a restore is exact: **Postgres will accept a partial restore
without complaint.** There are no constraints for dangling references to
violate. A restore that silently dropped half of `rf_draws` produces a database
that starts, answers queries, and is wrong. The database cannot be the oracle
here, so an external checker is not a refinement of the restore test — it *is*
the restore test.

### And the audit checkpoints are already a restore oracle, for free

This is the direct continuation of the `sv_audit_log` work. `sql/audit_checkpoint
_schema.sql` and `api/audit-checkpoint.js` (item 35, built today) compute a
daily digest over every row in a closed window, chained on the previous digest.
That chain is **an independently computed fingerprint of history** — and a
fingerprint is exactly what a restore check needs, because it requires **no
baseline capture at restore time**. Point the verifier at the restored copy:

- Every window whose digest still matches was restored **byte-faithfully**.
- The first window that disagrees names **when** the restore diverged, and its
  row count says whether rows were **lost** or **gained**.

A row-count comparison would need a trustworthy count from the source at the
moment of the backup, which nobody has. The digest needs nothing but the
restored data and its own chain.

**The limit, stated so nobody over-reads it:** this proves the three AUDIT
tables restored faithfully. It says nothing about `sv_controlled`, the ledger, or
anything else — those need their own coherence checks, below.

---

## Sizing

| # | Work | Size | Blocked on |
|---|---|---|---|
| 65a | **The coherence checker**, pointable at any Supabase-shaped database via env override: runs the item 35 checkpoint verification, then cross-table referential coherence (every `license_hash` resolves, every `job_id` on a draw exists, every append-only table that should have history is non-empty) | **M** | nothing |
| 65b | A recorded **row-count baseline per table**, taken on a cadence from production, so a restore can be compared against something rather than only against itself | **S** | nothing |
| 65c | The restore job itself — fetch a backup, stand up the target, load it, run 65a | **M** | **the plan question AND the scratch-environment decision** |
| 65d | The control: restore a deliberately truncated copy and demand 65a find it. **Without this, 65a is a checker nobody has seen fail** | **S** | 65a |
| 65e | **The acceptance rubric — what a human decides when the restore job exits 0.** Written 2026-09-25: `docs/2026-09-25-restore-acceptance-rubric.md`. Six sections (volume, field variety, placeholder values, referential coherence, temporal shape, and a sabotage arm), a three-state verdict, and section 1 answers **COULD NOT TELL for every table** until 65b exists | **DONE** | nothing — and it is deliberately a CHECKLIST, not a tool, because there is no restore artefact to run one against |

**65a is worth building before 65c is unblocked**, and that is the recommendation
rather than waiting: it is the piece with no dependency, it is the piece the
database cannot do for itself given one foreign key in 459 tables, and it is
useful the day somebody does a restore by hand — which is what will actually
happen the first time it matters.

---

## The accidental safety net, measured — and it is thinner than it looks

With no database backup, the only other copy of anything is the one sitting in a
browser. Measured per table rather than assumed from the pattern, because the
three named tables came out **three different ways**:

| Table | Local copy | Recovery value |
|---|---|---|
| `sv_controlled` | in `SV_SYNCED` (`sairnvet.html:2046`) — synced, not purged | **partial, device-dependent**: whatever that browser last held |
| `law_trusttx` | written through `st('law_trusttx', …)` (`sairnlaw.html:2077`), and sairnlaw has no scoped-cache purge list | **partial, device-dependent** |
| `dnt_charges` | **none.** `dnt_charges_list` is a SCOPED CACHE in `DNT_SCOPED_CACHES` (`sairndental.html:1725`), **cleared on sign-out and whenever the person changes** | **nothing** |

**The app holding dental money is the one with no local fallback, and that is a
CORRECT decision that happens to remove the accidental net.** Dental's caches are
purged deliberately: on a shared operatory tablet an owner signs in, the caches
fill, a provider signs in next, and every panel reads the previous user's copy —
which defeats the financial gate and the patient scoping. The file says so at
length. The security fix and the recovery gap are in genuine tension here, and
the resolution is a real backup, not a weaker cache.

**And a device-dependent copy is not a recovery plan even where it exists.** It
is whatever one browser last synced, on a machine nobody is tracking, with no
statement of completeness. It is worth knowing about at 3am and worth nothing in
a plan.

## What this scoping does NOT claim

- **No claim that backups exist or do not.** The plan was not checked — it is not
  in the repo, and guessing at it is the whole point of raising it as a
  decision.
- **No production data was read.** The foreign-key and table counts come from
  `sql/*.sql` in the repo; the 380-table figure comes from the committed
  structure snapshot, which is itself hand-relayed and may be stale.
- **Nothing was built or changed.**
