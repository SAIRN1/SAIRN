# fourth b25 — the two 400 observations, six citations re-derived, and a figure of my own withdrawn

**2026-10-15.** Every figure below names the command that produced it.
**MEASURED AT `1727fde6` and `12ffa069`; this file LANDED at `3b5fabb5`**
-- stated as two shas on purpose, because convention 35's third clause is
that a count is a function of the commit it was taken at. `api/sd-data.js`,
`sairnsenior.html` and `stonedesk.html` are byte-identical across all three
(`git rev-parse <sha>:<path>`), so every line number below holds at the
landing sha too. **Re-derive anything you mean to quote, including out of
this file.**

**THE ONE THING TO READ IF YOU READ NOTHING ELSE:** b24's **25** class-B
write-guarded branches is **WRONG and is withdrawn here. The number is 22**, and
the claim that *"the b23 routing list is short by three"* is withdrawn with it.
`api/sd-data.js` did not move between b23's HEAD and b24's — same blob sha — so
the two counts were two predicates over one file, and mine was the wrong one.
§3.

---

## 1. ITEM 1 — THE TWO 400 OBSERVATIONS, MADE

b24 parked this at a named blocker: every section returned `COULD NOT RUN:
SD_AUTH_SECRET not set in environment`. The fix was the one line b24 identified
— the env stub from `api/auth-license-app-scope.test.js:158-162`, set before
`_lib/auth.js` is required, restored on exit.

**Driver:** `<scratchpad>/drive_400_b25.js` → `drive_400_b25.log`. Loads a COPY
of `api/` in a tempdir with a stubbed `_lib/license` and a PostgREST mock
answering 400 with a real body. **The live tree was never written.**

**AND THE STUB WAS NOT THE ONLY BLOCKER.** With it in place the first run still
observed nothing: the payload carried `record_type: 'incident_review'` and the
handler refused it at validation —
`record_type must be one of: food_temp, sanitation, emergency_drill`
(`api/sd-data.js:14205-14207`) — **before any fetch**, so the injected failure
was never reached. **The control is what showed it**: the no-failure control
returned the SAME 400. Corrected to `record_type: 'sanitation'`.

### (1) A 23514 through a class-B WRITE branch — `alf_op_audits`, a TIER A resource

| | answer |
|---|---|
| AS SHIPPED, 400 + `23514` on the upsert | **HTTP 503 `NOT_PROVISIONED`** — *"The operational audit log is not set up yet — run sql/sairncare_op_audit_schema.sql in Supabase first."* |
| CONTROL, same branch, store healthy | HTTP 200 `ok:true`, the row echoed |
| COUNTERFACTUAL — the copy's guard rewritten to the shipped 3-argument `notProvisioned()` | **HTTP 400 `ROW_REFUSED`** — *"The database refused this record (23514). The table exists — the row itself was rejected, most often for exceeding the 64KB row cap. Nothing was saved"* |

The guard is `api/sd-data.js:14347`, `if (w.status === 404 || w.status === 400)`,
on the response of the upsert POST at `:14341`.

**SO THE OBSERVATION IS: A ROW REFUSED ON CONTENT IS REPORTED AS A MISSING
TABLE, on a Tier A compliance log**, and the operator is told to run a migration
that is already applied. The counterfactual proves the fix is a call-site change
and nothing else: the helper already exists and already answers correctly.

### (2) A 42703 through a class-C READ branch — `mech_site_assets`

| | answer |
|---|---|
| AS SHIPPED, 400 + `42703` on the GET | **HTTP 200 `ok:true`, `data: []`, `provisioned: false`** |
| CONTROL, same branch, store healthy | HTTP 200 `ok:true`, `provisioned: true`, with the board |

**A DROPPED OR RENAMED COLUMN RENDERS AS "NOT SET UP YET" WITH AN EMPTY LIST,
AT HTTP 200.** Nothing in the answer distinguishes it from a resource that was
never provisioned, and nothing is an error. That is the state a partial
migration leaves, which is the state this platform is in most often. The
control's `provisioned: true` is what makes the difference attributable to the
injection rather than to the harness.

---

## 2. ITEM 2 — THE SIX, RE-DERIVED AT HEAD. ONE IS CLOSED, FIVE ARE OPEN

Every citation below was taken at an earlier HEAD. **One of the six is FIXED and
five stand, with fresh `file:line`.** The four load-bearing claims were
re-checked by hand after being derived, not taken on trust.

### (a) b18 N1 — **CLOSED. Fixed 2026-10-14, and the fix names it.**

The cited line `api/sd-data.js:7179` is **NOT FOUND** as described: there is no
unconditional copy of the EVV clock fields anywhere in the file. What is there:

    api/sd-data.js:7214   // ── A RECORDED CLOCK TIME IS NOT OVERWRITABLE (2026-10-14, N1) ─────
    api/sd-data.js:7286-7295   THE COPY IS MADE WITH THE SUBMITTED FIELDS REMOVED
                               SEN_VISIT_EVV_FIELDS.forEach((f) => {
                                 if (payload[f] !== undefined && senSubmittedFields.indexOf(f) === -1) {

so a submitted `clock_in_at` is taken OUT of the copy loop rather than put back
afterwards. The assignment check MOVED `7142 → 7176` (**+34**). The render-time
guard MOVED `sairnsenior.html:2975 → :3154` (**+179**),
`var canClockIn=!v.clock_in_at;`, inside `renderClockView()` at `:3147`.

**N1 COMES OFF THE OPEN LIST.** It had been carried as open since b18 and across
b21–b24.

### (b) b21 F3 — the MAR grant bypass via `alf_clients`. **STILL OPEN.**

| was | is at HEAD | offset |
|---|---|---|
| `api/sd-data.js:8001` `ALF_MANAGEMENT_ROLES = roleSet({ owner: true, billing: true })` | **`:8268`**, text unchanged (read directly) | +267 |
| `api/sd-data.js:13274` `if (marGrant) {` — the `mar_access_read` audit write | **`:13541`** | +267 |
| *(never cited)* `assigned_employee_id: requestedAssignee` written verbatim | **`:8419`** | — |
| *(never cited)* `if (!isManagement && isBroadEdit) {` | **`:8382`**, present | — |
| *(never cited)* `} else if (!isManagement) {` | **`:8391`**, present | — |

Both guards still skip for management, `billing` is still management, and the
audit write is still conditioned on `if (marGrant)`. **Nothing about F3 has
changed except the line numbers.**

### (c) b21 F4 — the `rf_photos` AI claim never reaches the row. **STILL OPEN.**

* the `photoData` rebuild MOVED `8431 → 8698-8702` (**+267**), still the same
  three named fields;
* `grep -c "ai_source\|ai_approved" api/sd-data.js` → **1**, re-run by hand. It
  is the comment at `:2074`, **UNMOVED**, and there is no executable occurrence
  anywhere in the file;
* `aiFooter` MOVED `api/_lib/ai-safeguards.js:215 → :234` (**+19**). Lines
  215-220 now belong to a DIFFERENT function, `enforceAiApproval` (`:207`) —
  **a citation that still lands inside the file and inside plausible code is the
  worst kind to carry**, which is why it is spelled out.

### (d) `license_hash` never re-verified in memory. **STILL OPEN, now cited.**

    api/sd-data.js:13234-13235   const ALF_MAR_GRANT_COLS = 'grant_id,contact_id,resident_id,'
                                   + 'grantee_employee_id,granted_by,expires_at,revoked_at,created_at';
    api/sd-data.js:13376         ... '&license_hash=eq.' + enc(licHash) ...

`license_hash` is a FILTER and is not in the `select=` list, so the
belt-and-braces re-check cannot be performed on the tenant key. Confirmed as
described; it had no `file:line` before this.

### (e) No revoke action for a live grant. **STILL OPEN, now cited.**

    api/sd-data.js:13121-13123   actions: read, write, family_mar, mar_access_grant

No revoke. `revoked_at` is written for the MAR grant in exactly one place and
only as `null`, at creation (`api/sd-data.js:13650`). The only writes of a real
revocation timestamp anywhere in `api/` are other resources —
`api/dnt-bi.js:498`, `api/sen-portal.js:235`, `api/stonedesk-track.js:282`. So
the read path honours `revoked_at` and nothing in the app can set it.

### (f) b22 F1 and F2 — the `sd_photos` caller findings. **STILL OPEN, and ONE OF MY OWN CITATIONS WAS WRONG.**

* F1's line is **UNMOVED**: `stonedesk.html:26078`
  `data: small ? small.data : e.target.result,`
* **CORRECTION.** b22 said *"eighteen lines above it the function's own comment
  states the rule this line breaks."* The quoted comment — *"a downscaler that
  silently returns the original is how an oversized row reaches the server
  looking like a downscaled one"* — is at **`:26019-26020`**, **offset -54** from
  the cited `:26073-26077`, and it is the doc comment for
  **`sdDownscalePhoto` (`:26021`), a DIFFERENT FUNCTION**, 59 lines above. What
  sits at `:26073-26077` is an unrelated comment. **The finding is unaffected
  and the attribution was wrong**: the rule is stated by the downscaler's own
  documentation, not by the caller's.
* the idless-row skip is **UNMOVED** at `:2098`.
* the toast is at **`:26064`**, one occurrence, and the write it precedes is
  **`saveSD3Data()` at `:26097`** — so *"asserted BEFORE the write that would
  make it true"* is CONFIRMED (26064 < 26097). **But b22 named that write
  `st()`, and there is no literal `st(` in that function.** Mechanism right,
  name wrong.
* F2 now has lines: `var SD_PHOTO_DATAURL_BUDGET = 44000;` at **`:26012`** and
  the comparison `if (out && out.length <= SD_PHOTO_DATAURL_BUDGET)` at
  **`:26037`**. The quantity is **`out.length`, UTF-16 code units**, against a
  constraint counting octets — F2 confirmed at the line. `name: file.name` is at
  **`:26071`** and `handlePhotoFiles` (`:26049-26103`) applies **no cap** to it.

**The (d) `LATE_REPLAY` item was NOT driven in b25 and is still read-only
evidence.** It is named in b23's verdict as that verdict's weakest-evidenced
item and nothing here changes that.

---

## 3. ITEM 3 — CONVENTION 35, AND THE FIGURE IT COST ME

`docs/2026-09-13-cross-domain-disciplines.md` gains **convention 35**:
*a predicate has a SPAN as well as a PATTERN — and a re-count that disagrees
with a published count is a predicate disagreement until the SUBJECT is proved
to have moved.* Counted before assigning: **34 `## <n>.` headings at
`1727fde6`, 1-34, no gap, no duplicate**; the file is now 35, 1-35, no gap, no
duplicate, denominator heading moved to *"ELEVEN of the thirty-five"*, membership
question asked and answered NOT A MEMBER. Promotion row added to
`docs/METHODOLOGY.md` and its count block re-measured rather than overwritten.

**CITE IT AS `convention 35` OR `cross-domain-disciplines item 35`, NEVER AS A
BARE "item 35"** — `item 35` already means the hash-chained tamper-evident audit
log in the open-work queue.

### The withdrawal that paid for the third clause

b24 reported **25** class-B write-guarded branches against b23's **22** and
recorded the difference as the file having moved. **Both halves are wrong:**

    git rev-parse 5f5fcbad:api/sd-data.js 1727fde6:api/sd-data.js
    496593b2b753a5ad16fd0e4ee7a3ec47af932d64
    496593b2b753a5ad16fd0e4ee7a3ec47af932d64

**Byte-identical across 36 commits**, so nothing drifted. The real cause is a
span error in b24's own census: it decided a fetch's HTTP method from a **fixed
14-line window** after the assignment, and all three "new" branches are pre-write
**GET**s followed inside that window by the real upsert —

    api/sd-data.js:5061  const existingPhoto = await fetch(rest('grd_progress_photos?…'), { headers });
    api/sd-data.js:5072        method: 'POST',      <- a DIFFERENT fetch, 11 lines on

Re-counted with the span **bounded at the next `await fetch(`**
(`<scratchpad>/span_recount_b25.py` → `.log`), both numbers from one pass:

    class B, write-guarded -- b24 UNBOUNDED 14-line window : 25
    class B, write-guarded -- b25 BOUNDED-to-next-fetch    : 22
    dropped by bounding the span: [5062, 5935, 11241]
    added  by bounding the span: []

**THE CORRECTED LIST FOR hank, 22 entries, at `api/sd-data.js` as of `12ffa069`:**

    :2644  :3206  :3567  :4123  :4182  :4431  :4513  :4588  :8230  :9028
    :9223  :10552 :10699 :10898 :11017 :11187 :11264 :11515 :11594 :13659
    :13790 :14347

b23's own list is this set with each number from `:8231` onward **+1**, because
b23's census ran against a mid-batch tree (it reported 18,770 lines; this blob
is 18,769 by `split('\n')`, 18,768 by `wc -l`) and published under its
end-of-batch HEAD. Use the numbers above, not b23's.

`:3206` and `:11017` already read the body first and want the 4-argument preread
form — unchanged from b23.

---

## 4. ITEMS 4 AND 5 — THREE TIER A OBLIGATIONS DISCHARGED, AND WHAT HAD NO RECORD

**Discharged, all three that were assigned to fourth. `--list` now shows no
obligation assigned to me.** Full verdicts are on the records in
`docs/tier-a-reviews.json`.

| record | subject | verdict |
|---|---|---|
| `hank 2026-10-15T13:42:07Z` | sen_pay_rates, sen_visits — b23 F1 payroll `effectiveClock` | **CORRECT, driven.** 1 MODERATE finding |
| `hank 2026-10-15T12:24:35Z` | leg_custodylog, sen_visits — the append-only arm | **CORRECT and strictly stronger.** 1 MODERATE finding |
| `cody 2026-10-15T12:18:41Z` | quotes, sd_hr_certs, sd_hr_employees, sdn_projects — the blob-scope suite | **WELL BUILT, 3 of 4 checks pass.** 1 HIGH, 1 stale premise |

**WHAT THE DISPATCH NAMED THAT HAS NO TIER A RECORD, so there was nothing to
discharge and nothing is recorded as reviewed:** **b24 F3**, **b24 F4** and the
**class-B write branches** on hank's side, and the **b24 F1 probe re-anchor** on
cody's. Those are findings I routed; they become reviewable when the session
doing the work opens a record. Said plainly rather than stretching a different
record to cover them.

### F1 on hank's payroll record — MODERATE: the disclosure is one-directional

The fix is right and I confirmed the money by re-running my own b23 repro
**unchanged**: 300 minutes / 10000 cents, delta 0, where b23's run of the same
script printed 240 / 8000. Five suites green, exit 0 each (11/0, 10/0, 18/0,
4/0, 27/0).

`effectiveClock()` returns `pending`, `pending_count` and `pending_entries` on
every call. `api/_lib/sen-payroll.js` calls it twice per visit and **discards all
three** — `grep -n pending` over that file returns one line and it is a comment
(`:237`). So the output discloses `corrected_clock_visits` but cannot answer the
question a scheduler needs before closing a period: **how many visits carry a
correction awaiting approval, and what is it worth.** A period that closes over
an unapproved correction is the 60-minutes-unpaid case again by a slower route.
**NEXT STEP (hank):** `pending_clock_visits` beside `corrected_clock_visits`.
The values are already in hand.

**ALSO CHECKED AND SAFE, because it is on money now and was not before:** the
status-less-entry fail-open at `api/_lib/sen-evv-clock.js:116-118` is
**unreachable from a caregiver session**. Both sen_visits write paths start the
row from the server (`visitData = Object.assign({}, existingRow ? existingRow.data
: {})`, `api/sd-data.js:7181`), and `clock_corrections` is in **neither**
payload allowlist — `SEN_VISIT_SCHEDULE_FIELDS` (`:6973`),
`SEN_VISIT_EVV_FIELDS` (`:6974`). The create path starts from `{}` and a
caregiver cannot create. So only legacy rows reach it, exactly as the fix's
comment claims.

### F1 on hank's append-only record — MODERATE: a typed-in copy of a frozen list

`api/sd-data-leg-session-gate.test.js:170` keeps
`const APPEND_ONLY_WRITE = { leg_custodylog: 'APPEND_ONLY' }`, a duplicate of
`LEG_APPEND_ONLY` which `api/_lib/leg-roles.js:49-51` already freezes and
exports behind `isAppendOnly()` (`:178`, `:213-215`). **The failure it produces
is the failure this record is fixing, one resource later.** hank's own question
(c) answers: **no second LEG resource belongs in the list** — but the shape
exists one app over, `SV_APPEND_ONLY` / `sv_audit_log`
(`api/_lib/sv-roles.js:55`, refusal at `api/sd-data.js:14957`), and it is
**latent not live** because `api/sd-data-sv-session-gate.test.js:136` loops only
`['sv_patients','sv_soapnotes','sv_billing']`. **NEXT STEP (hank):** drive the
branch off `legRoles.isAppendOnly(resource)`, same for `svRoles` in the sibling.
Keep the code string `'APPEND_ONLY'` pinned literally — the contract should be
typed; the resource SET should not.

On hank's (a): **no independent spec pins the status.** The only document is
hank's own handoff (`docs/SAIRN-handoff-hank-b10.md:215`). **409 is right on the
merits** — it is a state conflict, not an authorization failure, and 403 would
collide with the role-matrix refusals. Keep it, and know it is pinned to an
implementation choice. On (b): **strictly stronger, verified on the assertion as
written** — the status assertion is first, so 401 and 403 both fail. Observed
green: `node api/sd-data-leg-session-gate.test.js` EXIT=0, 20 passed / 0 failed.

### F1 on cody's blob-scope record — HIGH: arm Z cannot fail, and it was ablated

    tests/sd_data_blob_scope_ten_routed_sites.js:347-351
      if (d.id !== undefined && s.idMustSurvive) { ok('Z ...'); }

No `else`. When `id` is missing — the one state arm Z exists to catch — the arm
emits neither `ok` nor `bad`. **It does not go red; it disappears.** Ablated
against a COPY in my scratchpad, one layer removed and nothing else, with the
suite's own `SAIRN_B15_SD_DATA` / `SAIRN_B15_SD_STORE` overrides pointed at the
live modules so the ablation is the only difference:

    BASELINE   EXIT=0   16 passed, 0 failed   arm Z present: 1
    ABLATED    EXIT=0   15 passed, 0 failed   arm Z present: 0

**Exit 0 with `id` stripped off every blob.** Convention 20, and a member of
item 8's cannot-fire group. **NEXT STEP (cody):** add the `else bad(...)` and
re-run that ablation — the arm does not count until it comes back RED.

### And the stale premise, which is nobody's carelessness

    8627f4e4  10-15 08:09  fix(blob): the ten routed conversions
    9f04ad39  10-15 08:11  test(b15): ... ten citations made runnable ...
    git merge-base --is-ancestor 8627f4e4 9f04ad39   ->  NO

hank's conversion landed **two minutes before** cody's suite was committed, on a
parallel branch. At HEAD the suite is **exit 0, 16 passed, 0 failed** — every A
arm green, no PRECONDITION failure, so the greens are measurements. The record's
*"ten arms are RED on purpose, the fix is routed to hank"* was true of the tree
it was measured on and false of the merged tree before the record was opened.

The same holds for the isolated-clone diagnosis, and this is the hard version:
`docs/known-red-suites.json` records this suite at `exit_code: 1`, 3 passed / 13
failed, sha `040cbfd9`, in a real `git clone --local`. `040cbfd9` resolves and
`git merge-base --is-ancestor 8627f4e4 040cbfd9` → **NO**. **The isolation was
real and the base was wrong.** Every isolation property the row claims is true.

**NEXT STEPS (cody):** the register row is **RECOVERED**, not red; and the
control arm's own message hardcodes *"so the ten failures above"* and prints it
on a run with zero failures — make it read off `failed.length`.

**A ROUTING FOR EVERY FAILING-FIRST SUITE, cheaper than the clone that missed
it:** `git merge-base --is-ancestor <fix> <diagnosis-sha>` separates *red because
the defect is there* from *red because my base is old*.

---

## 5. WHAT b25 DID NOT DO

* **The (d) `LATE_REPLAY` drive.** Not begun. Still read-only evidence.
* **The 33 server-only GETs.** Not re-classified; **CALLER remains a lower
  bound** and `branch_census_b23.py` was not extended to follow a variable back
  through its assignments. Convention 35 is the rule; the tool change is not
  done.
* **b24 F3, b24 F4, the 22 branches, and cody's probe re-anchor.** Routed, not
  reviewed — no Tier A record exists for any of them.
* **The EVV-readiness raw clock (b23 F2) and the one-person-agency
  self-approval question.** **HELD AT MICHAEL'S INSTRUCTION AND NOT ACTED ON.**
  I confirmed `api/_lib/sen-evv-readiness.js` is untouched by hank's b15 commit
  and made no judgement on it.
* **No production row read. No live deployment fetched. No table touched.** No
  file under `api/`, `sql/`, `tests/` or `tools/` was written.
