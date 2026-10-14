# Independent review — the three hank-authored `api/` Tier A records

**cody, batch b8, 2026-10-14. Reviewer: cody. Author of all three: hank.**
Independent in the sense the Tier A gate cares about — I did not write the code
under review — and **`docs/tier-a-reviews.json` IS NOT WRITTEN BY THIS
DOCUMENT.** Record 3 is assigned to **cc** and record 1 cannot be signed by
anybody from this clone; writing a verdict into the register for either would be
a reviewer taking an obligation that is not theirs. Findings here, signature
there, by whoever owns it.

**Records, from `docs/tier-a-reviews.json` at HEAD:**

| # | `opened_at` | sha | status at HEAD | assigned reviewer |
|---|---|---|---|---|
| 1 | `2026-09-27T03:42:29Z` | `54e4835ac96e` | open | fourth |
| 2 | `2026-10-06T06:14:34Z` | `8246d8bab707` | **reviewed (cody, b7)** | cody |
| 3 | `2026-10-12T01:51:33Z` | `b7f6fb54116e` | open | cc |

---

## 0. REACHABILITY FIRST, BECAUSE AN UNREACHABLE RECORD IS NOT A PASSING ONE

Re-measured in this clone **after `git fetch origin`** (which brought
`433860be..aeea051f`), not carried from b7:

    git cat-file -e <sha>;  git merge-base --is-ancestor <sha> origin/main

| sha | object in this clone | ancestor of `origin/main` |
|---|---|---|
| `54e4835ac96e` | **NO_OBJECT** | NOT_ANCESTOR |
| `8246d8bab707` | OBJECT_OK | **ANCESTOR** |
| `b7f6fb54116e` | OBJECT_OK | **ANCESTOR** |

**Record 1's sha resolves nowhere, and a fresh fetch did not bring it in.** So
its diff cannot be read from here by anyone. Everything in §1 is reviewed
**against the named files AT HEAD instead** — a weaker basis, declared as such,
and it is not a substitute for reviewing the diff. **§1's verdict is CANNOT
SIGN.**

---

## 1. Record `2026-09-27T03:42:29Z` — the EVV clock, the correction path, the legacy key

Four items; the record names three to *"attack hardest"*. Reviewed at HEAD.

### (a) The EVV clock wiring — **CONFIRMED CLEAN, and not by trusting arm H2**

The record's own words: *"if my `Object.assign` of the module's stamps can ever
land on a clock field, I have re-stamped an EVV record … The module's arm H2
asserts stamp keys are never clock fields; **I am relying on that assertion
rather than re-checking it**, which is exactly the copy-exactly trap."*

**Re-checked by a structurally different method — reading the key construction
rather than running the test that asserts it.** `api/_lib/sen-evv-clock.js:120`
iterates `['clock_in_at','clock_out_at']` and builds stamp keys at `:130-131`:

    stamps[field.replace('_at', '_received_at')] = serverNowISO;
    stamps[field.replace('_at', '_skew_ms')]     = skew;

`String.prototype.replace` with a string pattern replaces the FIRST occurrence,
so the result depends on where `_at` first appears. In `clock_in_at` the first
`_at` is the trailing one (index 8; the earlier `_` at index 5 is followed by
`i`), and in `clock_out_at` likewise (index 9; the `_` at index 5 is followed by
`o`). **Both therefore yield `clock_*_received_at` / `clock_*_skew_ms` and
neither can ever equal `clock_in_at` or `clock_out_at`.** The
`Object.assign(visitData, clockCheck.stamps)` at `api/sd-data.js:6981` cannot
overwrite a caregiver's claimed time.

**And the claimed time is what persists, on the path I can see.**
`visitData` is seeded from the STORED row only —
`Object.assign({}, existingRow.data || {})` at `api/sd-data.js:6943` — then
`api/sd-data.js:6976` copies payload fields through the allowlist
`SEN_VISIT_EVV_FIELDS` (`api/sd-data.js:6770`). **That allowlist does not
contain `clock_in_received_at`, `clock_in_skew_ms`, `clock_out_received_at` or
`clock_out_skew_ms`, so a caller cannot forge the server's own observation**, and
the stamps are merged AFTER the copy. A scheduler-tier caller cannot reach the
EVV fields at all — its branch copies only `SEN_VISIT_SCHEDULE_FIELDS`
(`api/sd-data.js:6917-6923`), *"so a scheduler can never forge a
clock-in/out."*

**WHAT I CANNOT CLOSE, and the record said so first:** the offline replay path
is in the handset, not in this repo. I drove nothing live. *"Every path"* is not
what was checked; **the server-side write path is.**

#### FINDING (new, mine, not in the record) — a flagged clock-in's flag is silently discarded by a flagged clock-out

`api/sd-data.js:6985-6987`:

    if (clockCheck.flags && clockCheck.flags.length) {
      visitData.clock_flags = clockCheck.flags;
    }

**That is an ASSIGNMENT, and `checkClockEvent` only ever reports on the clock
fields present in THIS payload** (`api/_lib/sen-evv-clock.js:120-121` — it
`return`s early for any field the payload omits). The two halves of a visit
arrive as two writes.

**Failure scenario, concretely.** A caregiver clocks IN from a handset that has
been offline for hours: `flags = [{field:'clock_in_at', code:'LATE_REPLAY',
skew_ms:…}]`, stored. Later the same caregiver clocks OUT, also late:
`checkClockEvent` sees only `clock_out_at`, returns
`[{field:'clock_out_at', code:'LATE_REPLAY', …}]`, and line 6986 **replaces**
the array. **The clock-in's LATE_REPLAY is gone from the row, and nothing says
it ever existed.** A `FUTURE` flag on a clock-in — the forged-time case — is
lost the same way.

**The comment two lines above is what makes this a defect rather than a
preference:** *"FLAGS ARE STORED, NOT ONLY RETURNED. A LATE_REPLAY that appears
in one response and nowhere else is a finding nobody can audit later."* The
stamps do not have this problem **because they are keyed per field**
(`clock_in_skew_ms` and `clock_out_skew_ms` coexist); the flags are one
unkeyed array, so the second write wins.

Note the asymmetry that hides it: if the clock-out is CLEAN, `flags` is empty,
the `if` is false, and the clock-in's flag survives — **so the bug only shows
when both halves are flagged, which is the case an auditor is looking for.**

**AND THE SAME AUTHOR GOT THIS RIGHT ONE SCREEN AWAY, which is why I am
confident it is an oversight and not a trade.** The self-correction marker on
the sibling action is deliberately sticky — `api/sd-data.js:6870-6872`: *"a
later ordinary correction must **not** clear a flag whose entry is still sitting
in the trail."* `clock_flags` is the same requirement with the opposite
implementation.

**Fix shape (not applied — this is `api/`):** merge by field rather than
assign, e.g. keep the entries whose `field` is not in the incoming set and
concatenate; or store `clock_in_flags` / `clock_out_flags` keyed the way the
stamps already are. **Routed to hank.**

### (b) `propose_clock_correction` — **CLEAN, BUT THE ANSWER POSTDATES THE RECORD**

The record asks the reviewer to decide whether refusing a caregiver's
self-correction is right, and names the risk: *"a caregiver who mis-typed their
own clock-in has NO route to fix it … if the office is one person who is also
the caregiver, there is no route at all."*

**At HEAD that lockout does not exist, and the code says why in its own words**
(`api/sd-data.js:6852-6872`): a self-correction is **MARKED, NOT REFUSED** —
*"A FLAG AND NOT A REFUSAL, deliberately. Refusing would create that lockout for
real."* And `owner` **is** in `SEN_VISIT_SCHEDULER_ROLES`
(`api/sd-data.js:6759`), so the one-person agency passes the gate. The marking
is on the entry and on the row and is sticky.

**THAT CHANGE IS DATED 2026-09-29 — TWO DAYS AFTER THIS RECORD WAS OPENED.**
So a reviewer reading the record's own diff would have reached the **opposite**
answer and routed a lockout that had already been fixed. **This is a finding
about the Tier A process, not about the code:** a record's questions are asked
at its `opened_at` and answered at whatever HEAD the reviewer happens to hold,
and nothing in the record distinguishes the two. See §4.

### (c) The legacy dual-key path — **CLEAN, WITH AN IRREVERSIBLE RESIDUAL**

The record concedes the direction is wrong-for-security-right-for-migration and
asks whether GCM's auth tag makes it safe. **The widening is bounded, and the
bound is in the code rather than in the comment:**

* a `v2` ciphertext gets **exactly one** key and **no fallback** —
  `api/_lib/auth.js:849-851`, *"The fallback would quietly re-couple the two
  duties this split exists to separate"*;
* only a 3-part legacy ciphertext reaches `legacyDecryptionKeys()`
  (`api/_lib/auth.js:853-854`), which returns at most two keys
  (`api/_lib/auth.js:812-819`);
* a wrong key returns `null` rather than garbage, via `tryDecrypt`
  (`api/_lib/auth.js:868`), and a `v2` value with `SD_ENCRYPTION_KEY` unset is
  logged as a **configuration error** rather than read as *"no secret stored"*
  (`api/_lib/auth.js:844-846`) — which is the silent-failure half of the same
  change and is handled.

**FINDING — the irreversible step has no guard, only a procedure.** The
four-step rotation at `api/_lib/auth.js:367-391` ends with *"clear
`SD_AUTH_SECRET_PREVIOUS`"*, and `api/_lib/auth.js:373` names that step as the
**point of no return for legacy ciphertexts**. Nothing in code refuses that
clearing while legacy 3-part ciphertexts still exist; the protection is the
documented ordering plus `sql/legacy_ciphertext_census.sql` — *"the select the
revoke doc said nobody had run."* **A documented procedure is not a guard, and
this one's failure mode is permanent data loss on a credential table.** Routed,
not fixed: it is `api/`.

### Verdict on record 1 — **CANNOT SIGN**

Not because anything failed. Because `54e4835ac96e` resolves nowhere, so there
is no diff to review and the review above is against HEAD, which is a different
artefact and demonstrably gives different answers (§1b). **Exact next step: hank
re-seats the sha from `Documents\SAIRN-hank` or fetches the object in, then the
assigned reviewer (fourth) reviews the diff.** The three paragraphs above are
evidence that reviewer can use; they are not a signature.

---

## 2. Record `2026-10-06T06:14:34Z` — already `reviewed`, re-attacked here anyway

**Status is `reviewed`, verdict PASS, reviewer cody, b7.** This section does not
re-sign it. It re-attacks the three things the record told a reviewer to attack,
because the b7 verdict itself recorded that one of them was not discharged.

### (1) The residual existence oracle — **REAL, BY DESIGN, AND I ACCEPT IT**

The record: *"the second half necessarily runs AFTER the fetch, so a narrow
caller with a NON-empty scope still learns existence for residents outside it;
decide whether that residual oracle is acceptable or whether the fetch should be
scoped by `resident_id` in the query itself."*

Confirmed in the code. The contact is fetched by `contact_id` alone
(`api/sd-data.js:12679-12681`), a miss is **404 `NO_SUCH_CONTACT`**
(`api/sd-data.js:12688-12691`), and the scope check runs after on the stored row
with **403 `FORBIDDEN`** (`api/sd-data.js:12696-12701`) — *"deliberately
distinct from NO_SUCH_CONTACT so the two are never collapsed into one oracle."*

**RULING: ACCEPT.** Three reasons, and the third is the one that decides it:

1. what leaks is *"a contact row with this id exists on this licence"* — not
   whose, not any clinical fact. The 403's text names no resident.
2. scoping the fetch by `resident_id` would **collapse 403 into 404**, which is
   the merge this file refuses on purpose and which the sibling `read` action
   also refuses.
3. **the narrow tier is already refused earlier on an empty scope**
   (`api/sd-data.js:12674-12675`), so the caller who learns anything is one who
   is legitimately assigned residents on this licence. That is a colleague, not
   an outsider.

**Bounded residual, recorded rather than closed:** with enumerable
`contact_id`s, such a caller could count contacts on the licence. No action
proposed; a future `contact_id` scheme should not be sequential.

### (2) `billing` on a clinical record — **NOW DECIDED, AND NOT BY ME**

The b7 PASS recorded that it did **not** discharge this: *"`ALF_FAMILY_READ_ROLES`
includes `billing` on a clinical record … 'Should billing read a MAR at all' is
a SAIRNcare role-vocabulary judgement and belongs to Michael."*

**Michael decided it on 2026-10-13: billing never reads the MAR by default; for
coding work only, an office manager may grant access, time-limited, expiring on
its own, audit-logged.** The decision is encoded in
`docs/2026-10-13-cody-b8-billing-mar-role-vocabulary.md` and pinned by
`tests/mar_billing_grant.test.js` (deliberately red, exit 1, registered in
`docs/known-red-suites.json`).

**THE CODE IS STILL OPEN AT HEAD.** `ALF_FAMILY_READ_ROLES = { owner, billing,
nursing }` (`api/sd-data.js:12551`) is still inherited by `family_mar`
(`api/sd-data.js:12654`), and because `billing` is in the broad half the
assignment scope is skipped entirely (`api/sd-data.js:12656`) — every resident
on the licence. **A decision is not a fix.** Routed to the `api/` owner.

### (3) Arm C0's uniqueness guard — **LOAD-BEARING, NOT DECORATIVE**

The record: *"check the guard is actually load-bearing and not just present."*

It is. `tests/sd_data_family_mar_gate.js:211-219`: on `anchorCount !== 1` it
calls `bad(...)`, prints the summary and **`process.exit(1)` immediately, so
C1-C3 do not run at all** — it cannot degrade into a silent pass on a reshaped
anchor. Re-run at HEAD: **exit 0, 10 passed, 0 failed**, C0 among them. The same
guard shape is reused as arm A8 of the new MAR suite for the same reason.

---

## 3. Record `2026-10-12T01:51:33Z` — findings routed to cc, who owns it

**I am not the assigned reviewer and I do not sign this.** Two of its three
named attack points are **no longer true at HEAD**, which is worth more to cc
than a verdict would be.

### (1) The 4-of-9 money/statutory cut — **MOOT AT HEAD**

The record: *"the derivation that picked four of the nine Tier A ungated
SAIRNfreedom resources and left five NAMED (`sf_district_imports`, `sf_events`,
`sf_permit_flags`, `sf_products`, `sf_vehicles`) — is the money/statutory cut
the right line, or should all nine be gated."*

**All five are session-gated at HEAD** — `api/sd-data.js:1245-1247` onward, and
`api/sd-data.js:1141-1143` carries the record's own five names as the decision
that was superseded. Commit `46d74678`, *"the last nine resources gated -- 36 of
36, and the b6 comment that said so was wrong."* **The question was answered by
gating all nine, which is the stronger answer.** cc does not need to rule on the
cut; cc needs to confirm the pair of lists (`SD_SESSION_GATED` /
`SD_GATE_APP`) was grown in both halves, which `api/sd-data.js:1628-1636`
asserts is the standing failure mode.

### (3) No ROLE check on the gates — **ADDRESSED AT HEAD**

The record: *"the gates add no ROLE check, so any signed-in session of any role
can still write every one of these rows."*

**A role layer now exists and it is enforced in the handler, not only tabulated
in a test.** `SF_ROLE_MATRIX` is a frozen table at `api/_lib/sf-roles.js:100`
with `decide()` at `:318` and `denyMessage()` at `:340`; `api/sd-data.js:95`
imports it and `api/sd-data.js:2023-2024` refuses with 403 `FORBIDDEN` when
`sfRoles.decide(resource, role, action) === sfRoles.DENY`. Driven by
`tests/sf_role_matrix_driven.test.js` (b7): 10 roles × 36 resources × 2 verbs =
720 cells, expectation from the table and observation from the handler, never
both from the table.

### (2) Not proven live — **STILL UNVERIFIED, AND I CANNOT CLOSE IT**

The record: *"none of the SAIRNfreedom or SAIRNscape gates was PROVEN LIVE with
a bare-key call, unlike the 2026-10-05 `customers` entry which has one with a
control — source-level only."*

**Still true, and still true after this review.** `SUPABASE_URL`,
`SERVICE_ROLE_KEY` and `SUPABASE_SERVICE_ROLE_KEY` are all **ABSENT** from this
session's environment (measured; I did not open `.env.local`). **No live call
was attempted and none is reported.** This is the same credential wall that
stopped b7 run A's item 4. **UNVERIFIED is the third state here — not a pass,
and not a failure of the gate.**

---

## 4. THE FINDING THAT IS ABOUT THE REGISTER RATHER THAN THE CODE

**Across the three records, four of the named attack points are no longer true
at HEAD, and in one case HEAD gives the OPPOSITE answer to the diff** (§1b: the
self-correction lockout was fixed two days after the record was opened, so a
HEAD-based reviewer passes a question a diff-based reviewer would route).

A Tier A record stamps `opened_at` and `opened_at_sha` precisely so the diff can
be found. **It does not record which basis the reviewer actually used**, and the
two bases disagree. `docs/tier-a-reviews.json` record 2's verdict happens to
state its basis in prose, in full, because its sha had to be re-seated — that
was an accident of circumstance, not a convention.

**Proposed, not built, and not mine to build:** the verdict should carry a
`reviewed_against` field with one of `diff` / `HEAD` / `both` plus the HEAD sha
at review time. Two lines in the writer. Owner: whoever owns
`tools/tier_a_review_gate.py`. **Stated here as an observation; no register
schema was changed by this document.**

---

*Line numbers were read at HEAD (`433860be`, with `origin/main` at `aeea051f`
unmerged at the time of reading) in this clone. `api/sd-data.js` is ~14k lines
and moves; re-derive rather than trusting these.*
