# Tier A review verdict — hank's `alf_mar` / `mech_credentials` obligation

**Reviewer: Fourth. Obligation: hank, `2026-09-26T12:36:06Z`, 48h overdue.**
**Resources: `alf_mar`, `mech_credentials`. Files:
`api/_lib/alf-family-mar.js`, `api/sd-data-family-contacts.test.js`,
`api/sd-data.js`.**

**Why this is a document and not a ledger entry.** `docs/tier-a-reviews.json` is
under cc's active claim (*"discharge my five overdue Tier A review
obligations"*). Two sessions editing one JSON ledger is the collision PR §2.1
exists for, so the verdict lands here and moves into the ledger when the claim
clears or the per-record path exists. **The obligation stays open until it
does** — this document is the work, not the discharge.

The obligation asked for six attack points, hardest first. **Five are driven
below. Point 4 I cannot review**, and the reason is disqualifying rather than
inconvenient.

---

## Summary

| Point | Subject | Verdict |
|---|---|---|
| 1 | The allow-list is the only thing between a relative and the clinical record | **Sound — and stronger than the test shows** |
| 2 | A mislabelled row passes both filters | **Real, and it is an INTEGRITY risk, not a disclosure one** |
| 3 | The silent 500-row MAR truncation | **CLOSED since the obligation was written** |
| 4 | Every caregiver can list every family contact's phone number | **NOT REVIEWED — I wrote the fix** |
| 5 | `ALF_FAM` survives a role change | **Real, narrower than stated, one-line fix** |
| 6 | The schema was never run | **STILL NOT RUN, verified live today** |

---

## Point 1 — the allow-list. Sound, and the *shape* is a better answer than the arm

hank's worry: *"That arm can only ever test the fields I thought of."* Correct
about the arm, and it does not matter, because `familyRow()` is not a deny-list.

```js
const FAMILY_FIELDS = ['date', 'time', 'status'];
```

**Three literals.** Anything not named is absent by construction — `prn_reason`,
`refusal_reason`, `effectiveness_check`, `notes`, `administered_by`,
`supervisor_notified` and every field added after this was written. A test can
only sample; an allow-list of three is **complete**, and that is a stronger
claim than any arm could make.

**The other half of the question — "does anything else WRITE an `administration`
entry with a different shape" — is answered NO, driven.** The only other MAR
writer on the platform is `api/alf-pharmacy.js`, and it writes
`entry_type: 'medication_order'` (`:199`), which `FAMILY_ENTRY_TYPE` excludes.
The UI's own writer (`sairncare.html:3098-3105`) produces exactly
`id, medication_id, date, time, status, administered_by, prn_reason,
effectiveness_check, refusal_reason, supervisor_notified, notes` — of which
three survive.

**One finding of my own, on the same line, and it is not hank's subject.**
`administered_by` is set by the CLIENT:

```js
administered_by:(alfSession&&alfSession.employee_id)||''
```

and `alf_mar`'s write strips `['id','resident_id','entry_type',
'assigned_employee_id','created_at']` — **`administered_by` is not among them.**
Meanwhile `marData.reviewed_by = session.employee_id` on the same blob **is**
server-set. So one identity field on a medication administration record is
authoritative and the other is whatever the caller sent, in the same function.
`administered_by` never appears anywhere else in `api/sd-data.js`.

This does **not** reach the family view — `administered_by` is not in
`FAMILY_FIELDS`. It is recorded here because the obligation's subject is
`alf_mar` and because it is the same class as the `alf_incidents` attribution
spoof fixed on 2026-09-28. **Not fixed by this review.**

## Point 2 — the mislabelled row. Real, and narrower than feared

hank is right that both filters test the **label**: the query filters
`entry_type=eq.administration` and `familyRow()` re-checks
`entry.entry_type !== FAMILY_ENTRY_TYPE`. A count written with
`entry_type: 'administration'` by any path, now or later, passes both. The
schema's check constraint restricts the **vocabulary**, not the correspondence
between label and content.

**The decision hank asked for: it does not need a content refusal, and here is
why.** The projection is an allow-list of `date`, `time`, `status`. A
mislabelled controlled-substance count would contribute a date, a time and a
status to the family view — it **cannot carry its count fields across**, because
they are not in the three.

So the exposure is **not disclosure**. It is **integrity**: a mislabelled row
lands in the adherence figure as a dose event, and the family member reads an
adherence percentage computed over something that was not an administration.
That is worth fixing and it is a **different, cheaper fix** than the
content-refusal hank proposed — the right place is the write path that could
mislabel, not a defensive filter in the read.

**Recommended, not blocking:** leave the projection as it is. Its narrowness is
what bounds this.

## Point 3 — the 500-row truncation. **Closed**, and hank closed it

The obligation says *"the 500-row limit is mine and it is silent… I did not
catch it until writing this."* It is no longer silent. Current source:

```
FAM_MAR_PAGE = 500;  FAM_MAR_MAX = 10000;
… pages ascending …
502 MAR_PAGE_UNREADABLE   — a page that could not be read
413 MAR_TOO_LARGE         — the ceiling, REFUSED rather than truncated
```

Three states, and the ceiling **errors instead of returning a short list**.
Ascending order is also the right choice and the file argues it: in
`created_at.asc` a concurrent insert lands after the last page and can only be
missed; in `desc` it shifts every later window, duplicating one row and skipping
another. **No action.**

## Point 4 — **NOT REVIEWED. I wrote the fix.**

hank asked whether the family-contact read should be narrowed to assigned
residents the way `alf_clients` is. **On 2026-09-27 I implemented exactly that**
— rows scoped to `alf_clients.assigned_employee_id`, consent-trail columns
removed from the `select`, a 403 rather than an empty list for a resident that
is not yours.

I cannot review my own change, and the standing rule is that a Tier A change is
reviewed by a session **other than the one that wrote it**, because the author
shares the blind spot that produced the code. I have direct evidence of that
this week: nine green, ablation-verified arms of mine missed a read-path
override that a live run found in one request.

**Who must discharge it: `cc` or `cody`.** Not hank — hank authored the
resource and the obligation. Not me.

**What that reviewer should attack**, since I can name the weak points even
where I cannot judge them: the extra `alf_clients` query per read; the row scope
applied **both** in the query and again in memory, which is deliberate
belt-and-braces and which a reviewer may reasonably think is one layer too many;
and the choice that an employee with no assigned residents receives an empty
list rather than a 403.

## Point 5 — `ALF_FAM` and the role change. Real, narrower, one line

`ALF_FAM` is a module global (`sairncare.html:2323`) and
`alfPurgeScopedCaches()` clears only `ALF_SCOPED_CACHES` localStorage keys — it
**does not** reset it. hank's concern stands.

**It is narrower than stated, and the reason matters.** `alfEnterApp()` calls
`alfPurgeScopedCaches()` then `init()`, and the family loader **replaces**
`ALF_FAM` on success (`:2398`) and **clears it to `[]` on every refusal path**
(`:2379`, `:2386`, `:2392`, `:2396`). So a role change *into* a role that is
refused does clear it — eventually.

What remains is a **window**: between `alfEnterApp()` and that fetch resolving,
`ALF_FAM` still holds the previous user's family list, and any render in that
window shows it. hank's own note that *"the tests do not cover this because the
probe reads localStorage keys"* is exactly right — a localStorage probe cannot
see a module variable.

**Fix: one line inside `alfPurgeScopedCaches()` — `ALF_FAM = [];`** — so the
purge is synchronous and does not depend on a later fetch. Not done here:
`sairncare.html` is outside this review's claim.

## Point 6 — the schema. **Still not run**, verified live today

hank: *"`sql/sairncare_family_contacts_schema.sql` NOT RUN, so nothing above has
executed against a real table."* Three days later that is unchanged. Driven
against the deployed endpoint on `ALF-AUDIT-2026` — an audit licence, created
after this obligation was written:

```
alf_family_contacts read -> 200  provisioned=False  rows=0
```

So the `alffam_consent_has_a_date` check constraint and the
`NOT NULL DEFAULT false` on `mar_consent` remain **asserted in a file and
verified by nothing**, and the file's own VERIFY block has still not been run.
**Everything in points 1, 2 and 4 is reasoning about a table that does not
exist.** That is the single most important line in this verdict.

**One small thing the live read exposed:** the un-provisioned branch returns
before `scoped_to_assigned` is set, so the response carries
`provisioned: false` and **no** `scoped_to_assigned` field at all. A client
reading that field to decide whether it is seeing a full roster gets
`undefined`, which is falsy — i.e. it reads as *"not scoped"*, the **broad**
answer, on a response that contains nothing. Harmless today because the list is
empty; worth not leaving that way.

---

## Reviewer's limits, stated

- **Point 4 is not reviewed and must not be counted as reviewed.** Five of six.
- I did **not** re-run `api/sd-data-family-contacts.test.js` or the 22-arm
  engine suite; the arm counts in the obligation are hank's and are **not**
  independently reproduced here.
- Points 1, 2 and 5 are read from source. Only points 3 and 6 are driven
  against live behaviour, and point 6 is the one that makes the rest
  provisional.

  **SUPERSEDED 2026-09-29 — see the re-drive at the end of this document.**
  `sairncare_family_contacts_schema.sql` has been run. Point 6 is CLOSED and the
  provisional marking on points 1 and 2 is LIFTED. Point 4 stays unreviewed for
  the unchanged reason: I wrote it. Read that section before acting on this
  line.
- I am **not independent of the class** in point 1's finding: I fixed the same
  caller-supplied-identity defect in `alf_incidents` the day before, so I came
  to this looking for it. That is why the `administered_by` finding is stated
  with its line numbers rather than argued.

---

# RE-DRIVE, 2026-09-29 — the table exists, and driving it found something the source read could not

The document above was written while
`sql/sairncare_family_contacts_schema.sql` had not been run, and said so: *"the
single most important line in this verdict"*. Michael has since run it. Every
claim that rested on the table's absence is re-driven here against the deployed
endpoint on `ALF-AUDIT-2026`, session `zz-audit-owner` (`owner`).

## Point 6 — **CLOSED**

```
read alf_family_contacts -> 200  provisioned=True  scoped_to_assigned=False  rows=0
```

**And the small finding in point 6 is moot on this path.** The un-provisioned
branch returned before `scoped_to_assigned` was set; on the provisioned path the
field is present in the response keys, value `false` for a broad-tier caller. The
un-provisioned branch is unchanged and would still omit it — worth fixing, no
longer reachable here.

## Points 1 and 2 — provisional marking LIFTED

Both reasoned about a table that did not exist. It exists. Neither verdict
changes: point 1's `FAMILY_FIELDS = ['date','time','status']` is still complete by
construction, and point 2's mislabelled-row exposure is still integrity rather
than disclosure. What changes is that they are now statements about a real table.

## Point 4 — **STILL NOT REVIEWED, and the reason is unchanged**

I wrote that fix. The table existing does not make me independent of it. It must
be discharged by **cc, cody or hank** — not by me, and not by the author of the
resource.

## The check constraint: present, and UNREACHABLE THROUGH THE API

Point 6 said the `alffam_consent_has_a_date` constraint was *"asserted in a file
and verified by nothing"*. It is now in the database. Driven through the endpoint
it still verifies nothing, and the reason is worth writing down rather than
recording a pass:

```
write mar_consent=true with NO consent_granted_at -> 200 ACCEPTED
  stored: mar_consent=true  consent_granted_at=2026-09-29T11:22:21.621+00:00
                            consent_granted_by=zz-audit-owner
```

`api/sd-data.js` sets `consent_granted_at: famConsent ? famNow : null` — from the
server clock, never from the body — so a `true` flag always arrives with a
timestamp and the constraint **cannot fire on this path by construction**. That is
the right call for the field (*"who authorised a disclosure is not something the
caller gets to state"*) and it means the constraint is defence against a DIRECT
database write — a SQL editor, a migration, a future writer — and not against the
endpoint.

So: the constraint is real, it is doing a real job, and **an API-level test of it
would be a test that cannot fail.** Recorded that way instead of as a pass.

Also driven: `mar_consent` omitted stores `false`; `active` defaults `true`.

## NEW FINDING — an unrelated edit rewrites the consent date

Driven, twice, seventy-nine seconds apart:

```
BEFORE  consent_granted_at = 2026-09-29T11:22:22.530+00:00   phone = null
        write: change the PHONE only, mar_consent unchanged at true
AFTER   consent_granted_at = 2026-09-29T11:23:41.867+00:00   phone = 555-0101
```

The write is an upsert with `resolution=merge-duplicates` and rebuilds the whole
row, so `consent_granted_at: famConsent ? famNow : null` **re-stamps on every
update**. Correcting a family member's phone number moves the recorded moment of
consent forward.

**Why this matters more than it looks.** `consent_granted_at` is the auditable
fact about when a third party was authorised to see a resident's medication
administration record. It is the field a surveyor reads to settle whether consent
was in place on the date a disclosure happened — and it now answers with the date
of the last unrelated edit. `consent_granted_by` moves with it, so the row can
also name the wrong authoriser.

**The platform has already made this exact decision the other way, deliberately.**
`alf_incidents.recorded_by` is explicitly not re-stamped on update, with the
reason written at the line: *"the column answers who filed it, not who last
touched it, and a management follow-up would otherwise erase the reporter."* The
same sentence applies here word for word, and the opposite was done.

**The fix is not to trust the caller.** It is to stamp the consent pair only on a
TRANSITION — when `mar_consent` goes from false or absent to true — and to leave
it untouched when the flag is already true. That keeps the server as the only
author of the value and stops an edit rewriting it. `consent_revoked_at` has the
mirror problem in the other direction.

**Severity:** hank's resource and hank's decision; not changed here. I would rate
it above point 2 — point 2 is an integrity error a reader can spot, and this one
is a plausible, precise, wrong date.

## Residue on `ALF-AUDIT-2026`

Three `alf_family_contacts` rows, plus the `alf_mar` and `alf_clients` rows
recorded in `docs/2026-09-29-alf-incidents-live-verification-and-residue.md`. The
resource accepts only `read` and `write` — no delete verb — so these need the SQL
editor.

```sql
-- VERIFY FIRST. Expect exactly three rows.
select contact_id, mar_consent, active from public.alf_family_contacts
 where app_id = 'sairncare'
   and contact_id in ('ZZ-FC-BADCONSENT', 'ZZ-FC-OK', 'ZZ-FC-DEFAULT');

delete from public.alf_family_contacts
 where app_id = 'sairncare'
   and contact_id in ('ZZ-FC-BADCONSENT', 'ZZ-FC-OK', 'ZZ-FC-DEFAULT');
```

Delete these **before** the `alf_clients` row `ZZ-MAR-RESIDENT` they reference.
