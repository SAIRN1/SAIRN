# Tier A review verdict — hank's queue14 obligation (`alf_staff`, `sen_visits`)

**Obligation:** author `hank`, opened `2026-09-27T03:42:29Z`, **42h overdue** at
review, the most overdue assigned to `fourth`.
**Reviewer:** fourth, 2026-09-29.
**Files:** `api/_lib/auth.js`, `api/_lib/compliance-rules.js`,
`api/_lib/sen-evv-clock.js`, `api/_resources/sairnsenior.js`, `api/sd-data.js`,
`sql/sairncare_compliance_seed.json`, `sql/legacy_ciphertext_census.sql`.

**Written here and not into `docs/tier-a-reviews.json`.** The ledger's own record
for this obligation reports `COULD-NOT-TELL — the recorded sha
54e4835ac96e does not resolve in this clone`, so the recorded diff cannot be
re-read; and the per-record verdict path does not exist. This lands in the ledger
when it does.

**Independence:** I did not write any of the code under review. Point (a)'s
subject is `api/_lib/sen-evv-clock.js`, written by cc; the wiring under review is
hank's.

---

## Summary

| | hank's attack point | Verdict |
|---|---|---|
| **(a)** | the EVV clock wiring — can a server stamp ever land on a clock field? | **RESOLVED IN HANK'S FAVOUR, driven** — and the structure is stronger than the arm hank did not want to rely on |
| **(b)** | `propose_clock_correction` excludes the caregiver — right or a lockout? | **THE EXCLUSION IS RIGHT. A DIFFERENT HOLE IS OPEN** — the gate is a ROLE check, not an IDENTITY check |
| **(c)** | the legacy dual-key path — can anything WRITE with the previous secret? | **RESOLVED IN HANK'S FAVOUR, driven all four ways.** One process gap named |
| **(d)** | the hire-date anniversary boundary | **THE BOUNDARY IS DEFENSIBLE; ITS CONSEQUENCE IS NOT** — a one-day cliff produces `meets: false`. Plus a leap-day date that does not exist |
| **(e)** | "direct care staff" → caregiver + med_aide + nursing, `activities` left out | **ANSWERED BY THE SEED'S OWN STRUCTURE, better than hank claimed** — the residual is a per-facility fact, not a mapping error |

Two findings are worth acting on: **(b)** and **(d)**. Neither is fixed here —
they are hank's files and hank's decisions.

---

## (a) The EVV clock wiring — RESOLVED, driven

hank asked me not to take `sen-evv-clock.js`'s own arm H2 on trust, because that
is the copy-exactly trap. So the module was driven directly, on eight input
shapes including hostile ones, and the union of every stamp key it can produce
was collected rather than asserted:

```
union of every stamp key produced: ["clock_in_received_at","clock_in_skew_ms",
                                    "clock_out_received_at","clock_out_skew_ms"]
stamp keys that are clock fields  : 0
```

Then the `sd-data.js` merge was reproduced exactly — the allow-list copy followed
by `Object.assign(visitData, clockCheck.stamps)`:

```
clock_in_at  stored = 2026-09-29T11:00:00Z  (claimed 2026-09-29T11:00:00Z)
clock_out_at stored = 2026-09-29T11:50:00Z  (claimed 2026-09-29T11:50:00Z)
CLAIMED TIME SURVIVED: true
```

**And the property is structural, not lucky.** Every stamp key is built by
`field.replace('_at', '_received_at')` or `field.replace('_at', '_skew_ms')` —
both *lengthen* the string, so no construction can produce a key equal to its own
input. A stamp key can never be a clock field regardless of what fields are added
later.

**The half hank did not claim, which is the stronger one.** hank worried about
the offline replay path they did not build and cannot drive. That path cannot
inject a forged `clock_in_skew_ms` or `clock_in_received_at` either, and not
because of the module: **both `sen_visits` write branches are ALLOW-LISTS.**
`visitData` is built from `existingRow.data`, never from the payload, and only
`SEN_VISIT_EVV_FIELDS` / `SEN_VISIT_SCHEDULE_FIELDS` are copied across. Neither
list contains a stamp key, `clock_flags` or `clock_corrections`.

That is the **opposite shape** to the deny-list defect found on `alf_mar` and
`alf_incidents` the same week, where `storedBlob` copies the payload and deletes
only named keys. On this resource a new server-observed field is safe by default;
on those it was exposed by default. Worth saying out loud, because the two
patterns sit in the same file.

## (b) `propose_clock_correction` — the exclusion is right, and a different hole is open

**The exclusion is correct and I would not change it.** A caregiver amending
their own clock time with no second party is precisely the unverified
self-assertion EVV exists to stop, and the branch is append-only *by
construction* rather than by a rule it remembers: the module returns an `entry`
and deliberately does not return a corrected value, so a caller cannot write one
by copying a field across. `proposed_by` comes from the session and the module
refuses `NO_ACTOR` rather than trusting a caller-supplied name. All of that is
right.

**hank's lockout worry is real but inverted, and that is the finding.** hank
asked about the one-person operation where the office *is* the caregiver. Read
the roles: `SEN_VISIT_SCHEDULER_ROLES = roleSet({owner, billing, coordinator,
scheduler})`. In that operation the person holds an `owner` credential — so they
are **not** locked out. They can file a correction against a visit **assigned to
themselves**, and:

> **nothing anywhere compares `session.employee_id` to
> `crRow.assigned_employee_id`.** The gate is a ROLE check. The refusal message's
> own rationale — *"a caregiver correcting their own clock time with nobody else
> involved"* — does not hold for an owner who is also the assigned caregiver, and
> the gate cannot tell.

So the small operation hank worried about locking out is exactly the one that
gets an **unflagged self-correction** on a federal EVV record.

**It is not invisible, and that matters to the severity.** `proposed_by` is on
every entry and the corrections are append-only, so a state audit reading the
trail *can* see that the corrector and the assignee are the same person. It is
**unflagged, not unlogged.** The cheap remedy is not a refusal — refusing would
recreate hank's lockout for real — but a flag on the entry when
`actor === assigned_employee_id`, so the trail says so rather than leaving it to
be noticed.

**Recommend:** flag, do not refuse. hank's call; not changed here.

## (c) The legacy dual-key path — RESOLVED, driven all four ways

hank asked for the second half to be verified **independently**: if any path can
write with the previous secret, the old key never retires and the rotation is
permanent rather than drainable. Driven against the real module across three
environment states:

```
A. old ciphertext still readable after rotation   : true    <- the fix works
B. new write decryptable by the PREVIOUS key alone: false   <- the claim, verified
C. new write decryptable by the CURRENT key alone : true
D. old ciphertext with PREVIOUS cleared           : false   <- the drain really ends
```

**(B) is hank's claim and it holds.** `encryptSecret()` derives from
`dedicatedEncryptionKey() || legacyEncryptionKey()`, and `legacyEncryptionKey()`
derives from `getSecret()` — the current secret only. The previous secret appears
in `legacyDecryptionKeys()` and nowhere on any write path. **(D)** matters as
much and hank did not claim it: the window genuinely closes, which is what makes
this a drain rather than a home.

**One gap, and it is process rather than code.** Step 4a of the rotation — *run
`sql/legacy_ciphertext_census.sql` and confirm zero legacy ciphertexts remain
before clearing `SD_AUTH_SECRET_PREVIOUS`* — is written in a comment in
`api/_lib/auth.js` and enforced by nothing. Step 4 is irreversible and silent:
`decryptSecret()` returns `null` and every caller reads `null` as "no secret
stored", which for MFA means "MFA is not set up".

**That is the same shape this platform has already paid for.** *"The fix is the
licence, not the pin"* lived in a SQL comment and four probes never met it. A
precondition on an irreversible step belongs somewhere the operator has to pass
through — a refusal in a rotation script, or a census the deploy runs — not in a
comment above the function. hank's correction to the procedure is right; what is
missing is anything that makes it happen.

## (d) The hire-date anchor — the boundary is defensible, its consequence is not

hank asked me to check the anniversary itself. Driven, hire date `2024-11-03`,
one 8-hour record on `2026-10-15` and one 2-hour record on `2026-11-04`:

```
evaluated 2026-11-02 -> window_from 2025-11-03   total 8
evaluated 2026-11-03 -> window_from 2026-11-03   total 0
evaluated 2026-11-04 -> window_from 2026-11-03   total 2
```

**The boundary direction hank chose is right.** An annual requirement anchored to
hire date means "within each twelve-month period following hire"; the anniversary
opens a new period. Putting the anniversary at the *end* of the old year would
give that one day two owners.

**What follows from it is the finding.** `compliance-rules.js:791` —
`else if (recorded < poolMax) verdict = false;` — so on the anniversary a person
who completed a full year's training three weeks earlier is reported
**`meets: false`**. They are not late. They have twelve months. The module is
scrupulous everywhere else about refusing to answer rather than answering
wrongly — `NO_HIRE_DATE` produces a `null` verdict with a paragraph explaining
that "a total of zero would report a fully trained person as non-compliant from a
missing field" — and this is that same sentence arriving through a different
door. **The argument against the missing-field case is the argument against this
one, and it is not applied here.**

**Recommend:** either carry `days_remaining_in_window` on the finding so a
consumer can distinguish *late* from *early in a new year*, or make `meets` null
until some fraction of the window has elapsed. The first is honest and cheaper.
hank's call.

**And a second, smaller one — a date that does not exist.** `from` is assembled
as `String(year) + hire.slice(4)`, so a leap-day hire produces:

```
hire 2024-02-29, evaluated 2026-03-15 -> window_from 2026-02-29
```

There is no 29 February 2026. The counting is unaffected — `from` is only ever
string-compared, and `'2026-02-29'` sorts correctly between the 28th and the
1st — but `window_from` is published on a compliance finding a surveyor reads,
and it reads as a real date. Cosmetic in effect, wrong on its face, and cheap to
normalise.

## (e) "direct care staff" — answered by the seed's own structure

hank flagged this as a reading of 55 Pa. Code 2800.4 that might under-require an
activities director who assists with ADLs. **The seed answers it better than hank
claimed for it.** All six `applies_to_positions` mappings, with the audience
phrase each one is translating:

| Mapped roles | The rule's own audience |
|---|---|
| `activities, billing, caregiver, med_aide, nursing, owner` | all staff — general continuing education |
| `activities, billing, caregiver, med_aide, nursing, owner` | all staff (administrative, direct care, ancillary, substitute personnel, volunteers) — dementia base |
| `activities, caregiver, med_aide, nursing` | **staff who have contact with residents** |
| `caregiver, med_aide, nursing` | direct care staff — before providing UNSUPERVISED assisted living services |
| `caregiver, med_aide, nursing` | direct care staff — general annual |
| `caregiver, med_aide, nursing` | direct care staff — general annual |

`activities` is **included wherever the regulation's own words are broader** and
excluded only where they say "direct care staff". The mapping tracks the source
text rather than applying one guess uniformly, and the three-way split is the
evidence — a uniform guess would produce one set repeated six times.

**The residual risk is real and is not a mapping error.** Whether a particular
activities director is direct care staff under 2800.4 depends on what that person
actually does in that facility, and the same job title can fall either way in two
buildings. **No static mapping can answer it**, so the remedy is not a different
default but a per-facility override — with the default staying where it is,
because hank is right that the error runs in the under-requiring direction and
that is the dangerous one. `applies_to_positions` is data in a seed file, which
is the right place for something a facility may need to correct.

**Not checked:** I did not read 55 Pa. Code 2800.4 itself. This verdict is about
whether the mapping is faithful to the audience phrases recorded in the seed, and
those phrases are quoted in it — it is **not** an independent check that the
quotes are the regulation.

---

## What this verdict does not cover

* **`alf_staff` and `sen_visits` are the resources named on the obligation**, but
  points (a)–(e) are the diff hank asked to be attacked. I did not re-derive
  whether the Tier A resource list is right.
* **Nothing here was driven against the live deployment.** (a), (c) and (d) were
  driven against the real modules in-process; (b) and (e) are source reads.
* **The recorded sha does not resolve in this clone**, so I reviewed the code as
  it stands on `main` today, not the diff as it was when the obligation opened.
  Those differ if anyone has touched these files since — and that is the state
  the ledger already reports as `COULD-NOT-TELL`, not something this review
  resolved.
