# SAIRN Platform — Handoff, 2026-08-24 (skills: credential lifecycle + env-var drift)

Written at ~1% context on instruction to stop all other work. Every claim
below was re-checked against the real repo immediately before writing.

**Repo HEAD at time of writing: `1a7a9cf`, and `origin/main` is the same
commit.** Working tree clean. Nothing local, nothing unpushed.

---

## 1. The task, as briefed

Two platform-wide patterns, each found independently in multiple apps rather
than once — which means nothing was checking for either:

1. **`sairn-app-scaffold`** — any new app with per-employee/per-account
   credentials should scaffold the credential-deactivation lifecycle by
   default: last-active-admin refusal, no self-deactivation,
   deactivated-caller re-check, audit log entry.
2. **`sairn-guardian-v2`** — a named check for the
   `RESEND_FROM_EMAIL` / `RESEND_FROM_ADDRESS` variable-name mismatch, so it
   is caught mechanically instead of app by app.

---

## 2. Exact current state — THE TASK IS DONE, NOT IN PROGRESS

The stop instruction said "do not continue" and asked whether either edit was
started, committed, or only local. Answering plainly, because "in progress"
would be the wrong word in both directions:

**Both skill files were read in full before editing. Both edits are written,
committed, and pushed.** Commit **`1a7a9cf`**, confirmed an ancestor of
`origin/main`. There is no partial work, no local-only change, and nothing to
resume.

Verified on `origin/main` at write time:

| Check | Result |
|---|---|
| `1a7a9cf` is an ancestor of `origin/main` | YES |
| Guardian carries the new check text | present |
| Scaffold carries the lifecycle section | present (3 mentions) |
| Working tree | clean |

### What actually landed

**`sairn-app-scaffold`** — the credential-deactivation lifecycle is now a
**required v1 component**, the file's second standing requirement. Frontmatter
and intro both updated so the file no longer describes itself as covering "a
single standing requirement". Four guards documented, each traced to a real
incident:

- Last-active-admin refusal (`409 LAST_ADMIN`). Recorded that StoneDesk marks
  this guard **unreachable by construction today and keeps it anyway**, because
  reachability is a property of the current rule set.
- No self-deactivation (`409 SELF_DEACTIVATE`).
- Deactivated-caller re-check (`403 CREDENTIAL_INACTIVE`) — the one that is
  easy to miss. A session token carries its role claim and stays valid for its
  full 12h life **after** the credential behind it is deactivated, so a
  just-removed admin can keep removing other people. Found live on SAIRNcode.
  Applies to `roster` as well as `set_active`.
- Audit on **every** outcome including refusals, with a `reason_code`.

Plus three things the real implementations get right: deactivate never DELETE;
`roster` must include inactive rows or nobody can be reactivated; a deactivated
credential must not become re-bootstrappable.

**`sairn-guardian-v2`** — new **Check 30**, env-var name drift. Count updated
to 30 in both the header and the frontmatter description.

---

## 3. A CORRECTION TO THE BRIEF — the third app is not SAIRNcash

The task named the pattern as proven on **StoneDesk / SAIRNcode / SAIRNcash**.
Verified against the code: **that is wrong.**

```
api/sd-auth.js   StoneDesk     set_active, retrofitted 2026-08-23
api/sc-auth.js   SAIRNcode     set_active, retrofitted 2026-08-23/24 (12c670c)
api/rf-auth.js   SAIRNroofing  set_active, shipped in v1
```

`grep -rln "set_active" api/*.js` returns exactly those three.
**`api/sairncash/` has no auth lifecycle at all** — the directory holds only
`checkout.js`, `firebase-config.js`, `trial-renew.js`, `trial-start.js`,
`trial-verify.js`, `verify.js`, `waitlist.js`. `api/rf-auth.js`'s own header
says SAIRNcash's trial equivalent "is still an open product decision."

This strengthens the case rather than weakening it: SAIRNroofing shipped the
lifecycle in v1 **specifically because** of the two retrofits. The correction
is recorded inside the scaffold skill so it does not propagate again.

---

## 4. Check 30, and why it is preventive rather than reactive

`api/alf-alerts.js` and `api/sairndental/send-reminder.js` both read
`RESEND_FROM_ADDRESS`. **That variable has never existed in this project** —
the sender is `RESEND_FROM_EMAIL`, configured since 2026-06-19. SAIRNdental's
reminder cron therefore never sent a single reminder: a 500 every hour for
months, from a feature everyone believed was working.

**Both instances are already fixed**, each with a regression test. So Check 30
is preventive — and it needs to be: the SAIRNdental email-reminders **design
doc still specifies `RESEND_FROM_ADDRESS` throughout**
(`docs/superpowers/plans/2026-08-11-sairndental-email-reminders.md`), so anyone
building from that doc writes the bug again. That is exactly how the second
instance happened.

The check also names the general class: a misnamed env var does not fail
loudly, it reads as `undefined`, and an `if (!process.env.X) return 500` guard
then reports it as a **missing secret** — symptom points at infrastructure,
cause is a typo in code. A previous session lost real time hunting a
`RESEND_API_KEY` that was present and correct throughout.

**Ran the check against the real repo before committing:** zero code hits for
the wrong name (one comment mention, which is expected and explicitly allowed),
and all 10 `process.env.RESEND` reads are the correct two names.

---

## 5. SAIRNdental photo-storage fix — CLOSED, nothing touched

Confirmed: **no file from that work was modified in this task**, and nothing
needs re-verification.

It was proven end to end earlier tonight, not inferred:

- Real booking through the real public endpoint: 3 photos, **921,597 bytes**,
  **14.1× the old 64 KiB ceiling** → `200 {"ok":true,"appointment_id":
  "AP-1787569259240-177"}`.
- Read back from the server: found, all 3 photos intact, 921,995 bytes stored.
- A row that size can only exist if the constraint is above 921 KB, which is a
  behavioural proof the migration took.
- Cleanup verified from a fresh server read: **no appointment in the practice
  carries any photo**, largest row now 531 bytes, totals unchanged at 12
  appointments / 9 patients.

**Still open, and it is not mine:** the `pg_constraint` verification query is
held for Michael in the Supabase SQL editor. Expect
`check ((octet_length((data)::text) <= 1291059))`, `convalidated = true`. The
booking result makes it confirmatory rather than load-bearing.

---

## 6. SAIRNlaw roadmap — CLOSED at 8 jurisdictions / 87 rules, nothing touched

No SAIRNlaw file was modified in this task. Coverage stands at:

```
us-federal 21   oh 7   mi 18   pa 11
in 7            il 6   fl 7    ca 10      = 87 rules, 8 jurisdictions
```

All live-verified. **Do not start a new state or a third domain without
Michael's explicit go-ahead** — that was stated twice and remains in force.

The next decision is his: more states, a third domain (family/probate/
criminal), or an Ohio-neighbour track.

---

## 7. Also in flight this session — do not re-derive

- **`docs/SAIRN-OPEN-WORK-INDEX.md` is the live queue.** It now carries the
  handoff-reading pass (all 46 files), a Contradictions section, and 28 rows
  added from handoffs. **Read it before picking up any work.**
- **One index row was closed in this same commit:** SAIRNdental's
  `send-reminder.js` was listed as broken with "verified still broken at lines
  37 and 75". **Another session fixed it hours after the sweep flagged it.**
  Moved to Recently closed. Worth internalising: a row that was true when
  written went stale within hours, on a repo with three concurrent sessions.
- **`SAIRN-ACTIVE-WORK.md` has been split per clone** —
  `-hank.md`, `-cc.md`, `-cody.md`, `-fourth.md`. The next index rebuild must
  read **all four**, not just the shared file. Historical entries stay in the
  original.
- **The delete-verb index row was corrected** (`4d18fae`): `delete` IS
  implemented for the 28-resource `SC_RESOURCES` family and absent everywhere
  else. The old wording said "any resource, any app", which would have sent
  someone building from zero when a working pattern exists to copy.
- **Guardian Checks 29 and 30 are both new tonight.** 29: any change touching a
  storage validator, schema constraint, or persisted payload shape needs a
  **real write**, not unit tests — from the California incident where 84/84
  isolation tests passed while all seven rows were unstorable. 30: env-var name
  drift, above.
- **Three synthetic rows were voided in the `DNT-PINNACLE-2026` demo practice**
  (photos emptied, identities cleared, status `Cancelled`). One of the three
  was a **prior session's** test row, not mine — my cleanup filter matched on
  *(has photos AND self-scheduled)* as well as my own note text. It was
  explicitly labelled "safe to delete", but it was not mine to void and that is
  disclosed rather than passed over.
- **Eight other test patients from earlier sessions remain** in that demo
  practice ("Jane Public", "Curl Test 3 Regression", "SYNC REGRESSION TEST
  Alpha", …). Left alone. Their accumulation is its own small cleanup job.
- **Concurrent-push traffic is heavy.** Expect to rebase; expect occasional
  conflicts in the shared active-work file; a push that returns no output has
  usually not landed — re-check `git ls-remote` rather than trusting silence.

---

## 8. Standard verification reminder

Verify `origin/main` HEAD, verify branch, and re-run the relevant checks before
trusting any claim in this document — **including this one**. Find the latest
handoff by **date and subject**, never by highest N; both naming patterns are on
disk and that is expected, not drift.
