# Tier A review — DISCHARGE of hank's queue14 obligation (`alf_staff`, `sen_visits`)

**Obligation:** author `hank`, opened `2026-09-27T03:42:29Z`, resources
`alf_staff`, `sen_visits`. **Assigned to `fourth` since the moment it was
opened; held 418 hours — 17 days — at the time of this discharge.**
**Reviewer:** fourth, 2026-10-14, batch b18.
**Clone HEAD at review:** `ebd8f9bd` (`git rev-parse --short=10 HEAD` →
`ebd8f9bda8`).

**THIS DISCHARGES THE OBLIGATION. It is the oldest one assigned to me and the
single biggest thing my own b17 handoff left open, by my own words there: *"THE
417-HOUR OBLIGATION IS THE BIGGEST THING I AM LEAVING OPEN, and it is mine."***

**It is discharged, NOT taken over.** `--takeover` would have been the wrong
instrument and it is worth saying why, because the b18 instruction offered both:
`--takeover` exists for the case where the *assignment itself has failed* — a
non-owner closing an obligation whose owner never ran again
(`tools/tier_a_review_gate.py:2795-2830`, `OWNER_STALE_HOURS = 48`). **I am the
owner and I am running.** A takeover would have recorded a handover that did not
happen, on the one record whose job is to say who looked.

---

## 0. WHAT THIS REVIEW COULD AND COULD NOT READ — first, because it bounds everything below

| | |
|---|---|
| the recorded diff | **COULD NOT READ IT.** `git fetch origin` then `git cat-file -e 54e4835ac96ea02dec8301b9a3252d228b186b0f` → **does not resolve.** Fetched first, so this is not a stale-clone artefact: the commit the obligation was opened at is gone from the graph — rebased away without a reseat |
| what was reviewed instead | **the code as it stands at `ebd8f9bd`**, file by file, against hank's own six attack points |
| all nine named files | **PRESENT at HEAD** — `api/_lib/compliance-rules-staff-join.test.js`, `api/_resources/sairnsenior.js`, `api/sd-data-sen-evv-clock.test.js`, `api/sd-data.js`, `api/_lib/auth.js`, `api/_lib/sen-evv-clock.js`, `sql/legacy_ciphertext_census.sql`, `api/_lib/compliance-rules.js`, `sql/sairncare_compliance_seed.json` |
| what that costs | **a diff review and a state review are not the same thing.** I can say what the code does now; I cannot say what this commit changed. A defect introduced and then removed between `54e4835a` and `ebd8f9bd` is invisible to me, and so is one introduced by a *different* commit that I will now attribute to this change's surface |
| why discharge anyway | **because the alternative is worse.** The register's own words: *"An obligation nobody closes is a queue people stop reading."* A state review of the real current code, with its limit named, is a review; 418 hours of nothing is not. **The limit is recorded in the verdict string itself**, not only here |

**Independence (PR §1.11, and the rule this gate exists for):** I wrote none of
the code under review. Point (a)'s subject, `api/_lib/sen-evv-clock.js`, is
cc's; the wiring is hank's; the compliance engine is hank's; `sql/legacy_
ciphertext_census.sql` is hank's. **Method independence:** every claim below was
re-derived from the source at HEAD by a reader that was NOT given the earlier
verdict's conclusions, then the load-bearing ones were re-checked by hand
against the same lines. That is the "structurally different method" convention,
not two passes of the same one.

---

## 1. THE VERDICT IN ONE TABLE

| | hank's attack point | 2026-09-29 verdict | **RE-VERIFIED AT `ebd8f9bd`, 2026-10-14** |
|---|---|---|---|
| **(a)** | can a server stamp land on a clock field? | resolved in hank's favour | **STILL CLEAN, and tighter than hank asked** — but see **N1**, which is the same field by a different door |
| **(b)** | the caregiver is excluded from `propose_clock_correction` | exclusion right; a ROLE-not-IDENTITY hole named | **THE 2026-09-29 FINDING IS FIXED** — `api/sd-data.js:7066-7072`. And **N1** is open |
| **(c)** | can anything WRITE with the previous secret? | resolved, driven four ways | **STILL CLEAN, and now pinned by an arm** (`api/_lib/auth.test.js:560-581`) |
| **(d)** | the hire-date anniversary boundary | boundary defensible, consequence not | **the consequence is now SOFTENED in code** — and **N4**: the comments claim driven arms that do not exist |
| **(e)** | `activities` left out of "direct care staff" | answered by the seed's own structure | **PARTLY OVERTURNED — N3.** The mapping is defensible; **the silence about what it excluded is not** |
| **(f)** | **the census SQL gates a destructive step and is unrun** | **NEVER REVIEWED** | **FINDING — F1. The discriminator cannot match the real data on one of its two surfaces, and it fails in the destructive direction** |

**DISCHARGE VERDICT: the four points hank asked hardest about (a, b, c, and
the boundary in d) survive review. ONE OF THE SIX WAS NEVER REVIEWED AT ALL
— (f) — AND IT IS THE ONE THAT CARRIES A FINDING.** Four more findings (N1–N4)
are open at HEAD. None is fixed here: they are hank's files and hank's calls,
except N3's remedy, which is a product decision.

**Why (f) was missed on 2026-09-29, and it is worse than an acknowledged gap.**
That review's closing section (`docs/2026-09-29-tier-a-review-verdict-hank-
queue14-fourth.md:233-244`) lists four limits — the resource list, no live
deployment, the dangling sha, and which points were driven versus read.
**(f) is not among them. It is not in the summary table, not in the body, and
not in the exclusions: the sixth attack point is simply absent, with no line
anywhere saying it was left out.** Five of six reviewed, presented as five
sections and a summary table, reads as *reviewed*. **A gap that is declared can
be picked up by the next reader; a gap that is silent is indistinguishable from
a clean verdict** — and the point that vanished was the only one carrying a
defect. It then sat 15 more days behind a document that looked complete.

---

## 2. F1 — THE CENSUS CANNOT MATCH THE DATA IT COUNTS, AND IT ERRS TOWARD DESTRUCTION

**This is the finding of this review.** hank's own attack point (f) asked for
exactly this check — *"If its legacy/v2 discriminator is wrong in either
direction, step 4 either gets blocked for ever or gets cleared while..."* —
and nobody had run it.

**THE PREDICATE**, `sql/legacy_ciphertext_census.sql:73-81`:

```sql
select
  'sc_credentials.data->>enc' as surface,
  count(*) filter (where data->>'enc' is not null
                     and data->>'enc' not like 'v2.%')                as legacy_rows,
```

**THE REAL DATA.** The ciphertext is not at `data->>'enc'`. It is nested one
level deeper, under the service name:

```
CMD sed -n '199,205p' api/sc-credentials.js
  199  nextEntry = {
  200    enc: encryptSecret(value),
  ...
  205  next[service] = nextEntry;            <-- service, from ALLOWED_SERVICES = { stedi: true }

CMD sed -n '179,190p' api/sc-eligibility.js
  179  const stored = (… credRows[0].data) || {};
  180  const rec = stored.stedi;             <-- the READER agrees: data->'stedi'->>'enc'
  190  stediKey = decryptSecret(rec.enc);
```

**The real path is `data->'stedi'->>'enc'`. On a jsonb object with no top-level
`enc` key, `data->>'enc'` is NULL** — so that surface reports
`legacy_rows = 0`, `v2_rows = 0`, and every provisioned row as
`never_set_rows`, **regardless of what is actually stored.**

**WHY THAT IS THE DANGEROUS DIRECTION, in the file's own terms.** The census
exists to gate step 4 of the `SD_AUTH_SECRET` rotation — *"Expect legacy_rows =
0 before clearing SD_AUTH_SECRET_PREVIOUS"* (`:63`), the precondition published
at `api/_lib/auth.js:414-417` as **4a**. The two failure directions are not
symmetric:

* **over-count** → step 4 blocks for ever, `SD_AUTH_SECRET_PREVIOUS` stays set,
  a retired key stays live. Bad, visible, reversible.
* **under-count** → **the gate reads zero while legacy ciphertext exists, the
  operator clears `PREVIOUS`, and the last key that can read those values is
  gone.** The file names this itself at `:20-24`: `decryptSecret()` returns
  `null` and a caller reads `null` as *"no secret stored"*.

**This predicate is structurally in the second direction.** Not "might be wrong
for some rows" — **it can never be right for any row**, because the key it tests
does not exist in the stored shape.

**SEVERITY, STATED HONESTLY RATHER THAN MAXIMALLY.** The affected value is a
Stedi API key, and `sql/sd_encryption_key_revoke_2026-09-24.sql:113-118` is
right that it is recoverable: *"it is rotated AT STEDI and re-entered"*, and an
undecryptable row answers `503 CREDENTIAL_UNREADABLE` and blocks nothing else.
**So this is not unrecoverable data loss.** It is a safety check that returns a
confident zero it cannot have measured — and a gate that cannot fail is the
defect whatever sits behind it. **The law surface's predicate is correct** (the
`v2.` prefix test exactly matches `encryptSecret`'s output format at
`api/_lib/auth.js:853-854`), which is what makes the broken half easy to miss:
one `union all` arm works.

**THE SAME ERROR IS IN A SECOND FILE**, which means it propagated rather than
being a typo: `sql/sd_encryption_key_revoke_2026-09-24.sql:113` —
*"The stored Stedi API key lives in `sc_credentials.data->>'enc'`"* — and the
census's own header, `sql/legacy_ciphertext_census.sql:40`.

### ROUTED TO hank — three things, in this order

1. **Fix the path to `data->'stedi'->>'enc'`** in
   `sql/legacy_ciphertext_census.sql` (both the count at `:73-81` and the
   per-row part at `:85-95`), and correct the prose at `:40` and at
   `sql/sd_encryption_key_revoke_2026-09-24.sql:113`.
2. **Do not hardcode `stedi` without saying so.** `ALLOWED_SERVICES`
   (`api/sc-credentials.js:58`) is `{ stedi: true }` today; a second service
   added there would silently fall out of the census the same way. Either
   iterate the blob's keys (`jsonb_each`) or state in the file that the service
   list is hand-kept and name the grep that checks it — the file already uses
   that convention for its column list at `:42-45`.
3. **Run it.** The count is still zero-evidence until somebody does. Step 4a is
   *"enforced by nothing"* — the 2026-09-29 verdict said so, and
   `grep -rn legacy_ciphertext_census tests/ tools/` is still empty at
   `ebd8f9bd`, so that is unchanged after 15 days.

**AND ONE PROCESS ASK, cc's:** the four-step rotation is published to an
operator in `docs/NHI-REGISTER.md:69` and in `tools/secrets_inventory.py:74` /
`tools/nhi_register.py:331-336` — **and all three omit step 4a entirely.** The
precondition exists in a code comment and in two review documents; the runbook
an operator would actually follow says "clear PREVIOUS" with no census. **The
generator is cc's, so the fix is cc's.**

---

## 3. N1 — THE CORRECTION TRAIL HAS A DOOR BESIDE IT (the sharpest new finding)

**(b) built an append-only, attributable, self-flagging correction trail for a
federal EVV record. The ordinary `write` branch can overwrite the same field
with none of it.**

```
CMD sed -n '7169p' api/sd-data.js
  7169  SEN_VISIT_EVV_FIELDS.forEach((f) => { if (payload[f] !== undefined) visitData[f] = payload[f]; });
```

`SEN_VISIT_EVV_FIELDS` (`api/sd-data.js:6963`) includes `clock_in_at` and
`clock_out_at`. **The copy is unconditional.** Between the assignment check at
`:7131` and that line there is no test of whether `existingRow.data.clock_in_at`
is already set, and `checkClockEvent` has none either — it refuses only
`NO_SERVER_TIME`, `CLOCK_UNPARSEABLE`, `CLOCK_IN_FUTURE` and
`CLOCK_OUT_BEFORE_IN` (`api/_lib/sen-evv-clock.js:104-188`).

**So a caregiver POSTing `{action:'write', resource:'sen_visits', id:…,
clock_in_at:'<any past time>'}` to a visit assigned to them passes every gate
and replaces a stored EVV clock-in — with no `clock_corrections` entry, no
`proposed_by`, no `self_correction` flag and no `has_self_correction`.** The
only residue is a re-stamped `clock_in_received_at` / `clock_in_skew_ms`.

**THE UI DOES GUARD IT, AND THAT IS THE WHOLE PROBLEM.**
`sairnsenior.html:2975` — `var canClockIn=!v.clock_in_at;` — is a *render-time*
guard. **A client-side-only restriction on a regulated write is the exact shape
of defect the hover auditors call a stale-frontend case**, and the API is the
boundary that matters.

**Why this is worth hank's attention even though (b) is correct:** (b)'s
refusal message argues that *"a caregiver correcting their own clock time with
nobody else involved"* is the thing EVV exists to stop. **The `write` branch
permits precisely that**, and does it with less trail than the branch that was
blocked. A gate that is strict on the audited path and silent on the
unaudited one does not raise the floor.

**ROUTED TO hank:** refuse an EVV clock field whose stored value is already
present and non-empty, on the caregiver branch, with a message pointing at
`propose_clock_correction` — **or**, if a first-write-wins refusal is wrong for
the offline replay path, record the overwrite as a `clock_corrections` entry
with `self_correction: true` so the trail is the same either way. **I am not
picking between those two: the replay path is hank's design and I cannot drive
it.** What is not defensible is the third option, which is what runs today.

**ROUTED TO cody — the failing-first arm:** POST a second `clock_in_at` to a
visit that already has one, as the assigned caregiver. **It must not be a
silent 200 with the field replaced and `clock_corrections` absent.** No arm
covers this today (`api/sd-data-sen-evv-clock.test.js` has late-replay, future
and ordering arms, and none for re-writing a set field).

---

## 4. N2 — `setup` CAN DEMOTE THE LAST OWNER, AND THEN NOTHING CAN PROVISION

**Found while answering hank's lockout worry in (b) — hank asked the right
question about the wrong endpoint.**

`api/sen-auth.js:263-288`. The only gate is `caller.role !== 'owner'` (`:265`);
validation is shape plus `SEN_ROLES.indexOf(role) === -1` (`:272`); the write is
a merge-duplicates upsert on `(license_hash, employee_id)` (`:281-287`) that
sets `role` to whatever was passed. **There is no self-target check and no count
of remaining owners.**

**The sequence, one request long:** a sole owner calls `setup` with their own
`employee_id` and `role:'caregiver'`. `bootstrap` then answers 409
`ALREADY_PROVISIONED` (`:216-218`); `setup` itself now answers 403. **Nobody
holds `PROVISIONING_ROLES` (`api/sen-auth.js:68`, `['owner']`), nobody holds
`SEN_VISIT_SCHEDULER_ROLES`, and there is no in-app route back.** Recovery is a
direct database edit.

**`set_active` is already protected** — the last-admin count runs over
`provisioningRoles` (`:343`, `soleRole: null` at `:350`), so the sole owner
cannot be *deactivated*. **The same reasoning was simply never applied to a
role change**, which is the same capability by a different verb.

**This is the credential-deactivation lifecycle requirement that
`sairn-app-scaffold` makes mandatory in v1** — *last-admin refusal, no
self-deactivation* — met for one verb and not the other. **ROUTED TO hank:**
refuse a `setup` call that would leave zero active holders of
`PROVISIONING_ROLES`, and refuse a self-demotion outright. **ROUTED TO cody:**
the failing-first arm is a sole owner calling `setup` on themselves with
`role:'caregiver'` — it must 4xx, and a following `bootstrap` must not be the
only thing standing between the licence and a lockout.

---

## 5. N3 — (e) PARTLY OVERTURNED: the mapping is defensible, the silence is not

**hank's self-flag was: *"Under-inclusion is the dangerous direction here and it
is the one I chose."* The mapping choice survives. What does not survive is that
an excluded position is invisible on the response.**

`api/_lib/compliance-rules.js:451-474`, `matchAudience`, is properly
three-valued — `true`, `false`, `null`. And the **empty-set** case is handled
exactly right: `meets: null`, `no_applicable_requirement: true`, and prose at
`:940-952` that distinguishes *"we could not read who it applies to"* from
*"this person has no obligation"*. **That half is better than most of this
platform.**

**THE HOLE IS THE NON-EMPTY SET.** Rows that returned a clean `false` are
dropped from `applicable` with **no disclosure anywhere on the response**.
`unmapped_requirements` (`:997-1014`) is built only from rows that are
*structurally* unmappable — a row *with* a position list is `mappable: true`
and never appears there, no matter who it excluded. `grep -n
"excluded_by_position" api/_lib/compliance-rules.js` → **no match**; there is no
field to look at.

**The concrete case, which is hank's own example:** an `activities` staff member
at a PA **ALR** matches only the all-staff dementia row (2 hours). Two recorded
hours ⇒ `meets: true`. **Nothing on the response says the 18-hour
unsupervised-work gate and the 16-hour direct-care annual were dropped because
`activities` was not in their list.** If that Activities Coordinator does assist
with ADLs — which is what makes someone a direct care staff person under the
very 55 Pa. Code 2800.4 definition the seed's own basis cites
(`sql/sairncare_compliance_seed.json:530`) — **the engine reports them compliant
against 2 hours when they owe 36.** Same shape for `billing` and `owner` under
that chapter.

**AND IT IS CHAPTER-DEPENDENT, WHICH IS WHY IT HIDES.** Under PCH (Ch. 2600)
there is no all-staff row (`no_general_dementia_requirement: true`, `:740`), so
the same person lands in the empty-set branch and **correctly** comes back
`null`. The engine is right in one chapter and silent in the other, for the same
person.

**`activities` is a real, storable value** — `STAFF_POSITIONS`
(`api/_lib/compliance-rules.js:391`) and the live select at
`sairncare.html:651` / `:1018` — so this is not hypothetical vocabulary.

**ROUTED TO hank:** carry the excluded rows on the finding —
`excluded_by_position: [{who, why}]` — so a reader can see what was not
compared. **Not a refusal and not a widening of the mapping:** hank's
caregiver + med_aide + nursing reading of 2800.4 is defensible and I would not
change it. **The claim that must stop being made silently is "compliant", when
what was measured is "compliant against the subset that mentioned your job
title".**

**ROUTED TO cody:** no arm drives `position: 'activities'` anywhere —
`grep -c activities api/_lib/compliance-rules-staff-join.test.js` → **0**. The
failing-first arm is an `activities` staff member against `PA-TRAINING-ALR-2010`
with exactly 2 recorded hours: today `meets: true` and nothing disclosed.

**ONE THING THAT MASKS ALL OF THIS AT RUNTIME, and must not be read as a fix:**
`hire_date` is never written (noted at `api/sd-data.js:13380-13386`), so every
live finding currently returns `NO_HIRE_DATE` / `meets: null`. **The engine is
being saved by a different defect.** When `hire_date` starts being written, N3
becomes live on the same day — so it must be fixed *before* that, not after.

---

## 6. N4 — THREE COMMENTS CLAIM A DRIVEN ARM THAT DOES NOT EXIST

This is small, mechanical, and the exact pattern the eighth cross-domain
convention is about: **nothing announces the day a check stops testing
anything** — including a check that never existed.

| the claim | where | the fact |
|---|---|---|
| *"Driven: hire 2024-11-03 … evaluated 2026-11-02 -> compliant; evaluated 2026-11-03 -> NON-COMPLIANT"* | `api/_lib/compliance-rules.js:846-848` | **no arm passes either date.** `grep -rn "2026-11-03" api/_lib/compliance-rules-staff-join.test.js` → no match. The sole anchor arm (`:412-416`) drives the **mid-year** case `2026-09-27` |
| *"an arm drives that"*, of the leap-day hire normalisation | `api/_lib/compliance-rules.js:534` | **no arm drives `02-29`.** `grep -n "02-29"` over the compliance tests hits only source comments |
| the day-zero behaviour — `window_days_elapsed`, `windowJustOpened`, `dayZeroWithheld`, the `meets: null` withholding at `:920-928` | `api/_lib/compliance-rules.js:867-877` | **asserted by nothing** |

**The boundary itself is fine and I verified it by hand**, which is the only
reason this is N4 and not a finding of substance: `mmdd = '-11-03'`,
`on.slice(4) < mmdd` is `'-11-03' < '-11-03'` → **false**, so `year` is not
decremented and `from = '2026-11-03'`. The anniversary is **day zero of the new
window**, inclusive at the lower bound (`api/_lib/compliance-rules.js:521-524`).
**And the 2026-09-29 verdict's complaint about the consequence has since been
answered in code** — a day-zero shortfall now yields `meets: null` with a
stated reason rather than `meets: false`, which was the right fix.

**STATED FAIRLY: "driven" in these comments most likely means *driven by hand
during development*, which is a real activity and not an invention.** The
defect is not dishonesty, it is that **a hand-drive leaves no artefact** — six
weeks later the comment is the only evidence the case was ever exercised, it
reads exactly like a reference to a committed arm, and nothing fails when the
behaviour changes. **That is the same shape as Guardian Check 0b one layer up:**
a claim about *evidence* rather than about a number, believed the same way.

**ROUTED TO cody:** three arms — the exact anniversary (`on_date` =
`hire_date` + 2 years), a `2024-02-29` hire evaluated in a common year, and a
day-zero shortfall asserting `meets === null` rather than `false`. **ROUTED TO
hank:** either those arms land, or the three comments say *"driven by hand on
2026-09-29, no committed arm"* — which is true, cheap, and tells the next reader
what to distrust.

**One more, found in passing and smaller still:** the hire-date regex
(`api/_lib/compliance-rules.js:511`) is shape-only, so `'2024-02-30'` passes it,
fails `isRealDate`, fails the leap normalisation, and is printed on the finding
as `hours_window_from: '2026-02-30'` — an impossible date presented as a window
start. Untested. hank's.

---

## 7. WHAT STILL HOLDS, SAID PLAINLY — because a review that only lists findings is not a review

**(a) THE EVV CLOCK WIRING IS CLEAN, and it is structurally clean rather than
clean by assertion**, which is the stronger of the two and is what hank asked
for. The stamp keys can only ever be the four
`clock_{in,out}_{received_at,skew_ms}`, derived by `field.replace('_at', …)` over
a **literal** array (`api/_lib/sen-evv-clock.js:120-131`) — a caller cannot
inject a key — and none of them is in `SEN_VISIT_EVV_FIELDS`. So
`Object.assign(visitData, clockCheck.stamps)` at `:7174` running after the field
copy **cannot** overwrite a claimed time. **The claimed time is what persists on
every path**, including the offline replay, which re-enters the same `write`
branch (`sairnsenior.html:3058` → `senData('write','sen_visits',entry.payload,true)`) rather than
bypassing the module; the scheduler branch does not copy clock fields at all.

**And arm H2 does do what hank did not want to rely on** —
`api/_lib/sen-evv-clock.test.js:145-151` takes `Object.keys()` from the **live
return value** and pins the cardinality at 4, so a fifth stamp key fails it.
*(The arm immediately above it, H1 at `:140-144`, **is** the weak
hardcoded-list shape — it passes vacuously if an export is removed. hank's
worry was right about the file and one line off about the arm.)*

**(c) THE DUAL-KEY PATH IS DRAINABLE, verified on the half hank asked for.**
`SD_AUTH_SECRET_PREVIOUS` is read in exactly two places in all of `api/` —
`api/_lib/auth.js:482` (verify) and `:840` (decrypt). **There are exactly two
`encryptSecret` call sites in the repo** (`api/law-auth.js:462`,
`api/sc-credentials.js:200`), both landing on
`dedicated || legacyEncryptionKey()` (`:846-854`), and `getSecret()` (`:372-379`)
reads `SD_AUTH_SECRET` only. **No write path can produce ciphertext under the
previous secret**, and there is no re-wrap/backfill script anywhere. A wrong key
fails in `decipher.final()` and surfaces as `null`, never as wrong plaintext
(`:894-909`), with the tag length pinned at 16. It is also now pinned by an arm
that did not exist at the earlier review: `api/_lib/auth.test.js:560-581` (B2),
plus `:545-558`, `:610-615` and `:618-627`.

**One residual, named and not a finding:** `api/law-auth.js:481-486` reports an
**undecryptable** MFA secret to the user as *"That code did not match"* (401
`MFA_INVALID`) with no `console.error` and no `secret_undecryptable` audit —
unlike its sibling 70 lines above at `:412-428`, which does both. It fails
**closed**, so it is a diagnosability defect rather than a security one. hank's,
low priority, and worth one line because the sibling shows the house convention.

---

## 8. THE DISCHARGE, AND WHAT IT DOES NOT CLAIM

**DISCHARGED** via
`python tools/tier_a_review_gate.py --discharge hank 2026-09-27T03:42:29Z
--body-file <verdict>` — as the assigned owner, **not** with `--takeover`.

**WHAT THIS DISCHARGE DOES NOT CLAIM:**

1. **It is not a diff review.** `54e4835a` does not resolve; this is a review of
   `ebd8f9bd`. Anything this change did and undid is outside it.
2. **It did not run anything.** No SQL was executed, no endpoint was called, no
   suite was driven by me. Every claim is read from source at a named line, and
   the two places that need execution to settle — the census count (F1.3) and
   the `sd_photos` size constraint noted in the b18 safeguards spec — are marked
   UNVERIFIED rather than assumed.
3. **It fixes nothing.** Five findings are routed to hank, four failing-first
   arms to cody, one runbook omission to cc. **No `api/`, `sql/` or `tests/`
   file is touched by this batch** — my claim declares `docs/` only.
4. **It does not re-open (a), (b) or (c).** They were resolved in hank's favour
   on 2026-09-29 and they re-verify clean at HEAD. N1 is not a reversal of (b);
   it is a second door onto the same field.
5. **It does not settle the `activities` question.** Whether an Activities
   Coordinator in a PCH assists with ADLs is a question for a practitioner, not
   a reader of 55 Pa. Code. **N3 is about disclosure, which is answerable
   without it.**

**THE ONE THING I WOULD WANT THE NEXT SESSION TO TAKE FROM THIS, and it is a
process point, not a code point:** this obligation sat 418 hours with a
*written review already on disk* (`docs/2026-09-29-tier-a-review-verdict-hank-
queue14-fourth.md`) that the register knew nothing about, because the per-record
verdict path did not exist when it was written and nobody went back when it did.
**A review that is not in the register is not a review** — and the 15-day gap is
exactly how long it took for the one unreviewed attack point to be looked at.
**That is the argument for the b18 item-5 ask: a session-start surface for any
obligation over 48 hours** (`docs/2026-10-14-fourth-b18-tier-a-triage.md`).
