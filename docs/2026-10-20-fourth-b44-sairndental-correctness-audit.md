# SAIRNdental correctness audit — GFE, denials, credentialing

**fourth / b44, 2026-10-20.** This is an AUDIT, not a fix: `sairndental.html`
is in 0 of this batch's commits for these findings. Each finding is marked:
- **REPRODUCED**: driven in Chromium against the page with `init()` called
  and `fetch` stubbed, or built in node from `api/_lib/dental-credentials.js`;
- **READ ONLY**: established from the code alone.

The research pass was delegated to a subagent. I re-read three of its
findings against the code myself, and those three are marked **[verified
by hand]**. Scratch evidence is in
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-fourth\fc1f8565-6013-48a4-b66b-d27902506016\scratchpad\b44\agent_dental\`
(`repro.py`, `board.js`, `regs\*.txt`).

**Rules read from source** (eCFR renderer API, HTTP 200):
- 45 CFR **149.610** (good faith estimates for uninsured / self-pay
  individuals) and **149.620** (patient-provider dispute resolution);
- 21 CFR **1301.12** and **1301.13** (DEA registration).

---

## 0. THE RESULT

| feature | confirmed defects | worst | correct as checked |
|---|---|---|---|
| **GFE** | 6 | **moderate ×3** | the timing tiers, weekends, the 2026 federal holiday list, the $400 / 120-day dispute figures |
| **Denials** | 1 | **moderate** | no rule-based deadline is claimed; codes are stored, never interpreted |
| **Credentialing** | 2 (one server-side) | **moderate** | every server status has a rendering; DEA 60-day window matches 1301.13(b) |

---

## 1. GOOD FAITH ESTIMATE

### Confirmed defects

1. **MODERATE — an estimate can be issued while its printed document shows
   the date of birth as "--". REPRODUCED.**
   - **The rule:** 149.610(c)(1)(i) says the estimate *"must include:
     (i) Patient name and date of birth"*.
   - **The code:** `saveGfe()` (`:5281`) stores `patient_dob` as a copy
     taken at save time, while `gfeMissing()` (`:5163`–`:5165`) checks the
     patient's *current* record. `openGfeDoc()` (`:5336`) then prints the
     saved copy. Patient name has the same shape, and the server check in
     `api/_lib/dental-gfe.js` also reads the current record.
   - **Driven:** with no DOB, the missing list was `["(c)(1)(i) patient date
     of birth"]`. After adding the DOB to the patient, the list was `[]` and
     the document still printed *"date of birth --"*.
2. **MODERATE — the dispute disclaimer leaves out two required elements.
   REPRODUCED.**
   - **The rule:** 149.610(c)(1)(x) says the disclaimer *"must include
     instructions for where an uninsured (or self-pay) individual can find
     information about how to initiate the patient-provider dispute
     resolution process and state that the initiation ... will not adversely
     affect the quality of health care services"*.
   - **The code:** `:5357`–`:5358` has the correct $400 and 120-day figures.
     The rendered text has no *adversely*, no *quality of*, no *how to
     initiate* and no CMS pointer.
3. **MODERATE — the separately-scheduled-items disclaimer falls short. READ
   ONLY.**
   - **The rule:** 149.610(c)(1)(vi) says it must sit *"directly above this
     list"*. It must state that separate estimates will be issued on
     scheduling or request, that codes, charges and provider identifiers *"do
     not need to be included"*, and it must give instructions for obtaining
     those estimates.
   - **The code:** `:5350`–`:5352` prints one sentence, and prints it
     *after* the list.
4. **LOW–MODERATE — the holiday warning points the wrong way. REPRODUCED;
   [verified by hand] at `:5244`.**
   - The text says that if holidays are not business days, *"the real due
     date is earlier"*.
   - Skipping a holiday while adding business days moves the date **later**.
     Example: a request on 2026-11-25 is due 2026-11-30 with Thanksgiving
     listed, but skipping Thanksgiving gives **2026-12-01**.
5. **LOW — a New Year's Day observed on 31 December is missed. REPRODUCED.**
   - `gfeHolidaysInWindow()` (`:5123`–`:5131`) loops only over the window's
     own calendar years.
   - Example: 2027-12-28 + 3 business days = 2027-12-31, with an empty
     holiday list, although `gfeFederalHolidays(2028)[0]` is 2027-12-31.
6. **LOW — the app's advice and its own deadline tracking disagree. READ
   ONLY.**
   - At 10 or more business days of lead time, `:5243` says *"Treat the
     earlier date as binding"*.
   - But the overdue count (`:5426`) and the late/on-time verdict (`:5443`)
     use the later date.

### Correct as checked

- **Timing tiers, 149.610(b)(1)(vi)(A)–(C). REPRODUCED.** Scheduling on
  2026-10-19:
  - 2 business days ahead: no deadline;
  - 3 business days: rule (A), due 2026-10-20;
  - 9 business days: rule (A);
  - 10 business days: rule (B), due 2026-10-22, with (A)'s date shown beside
    it;
  - on request: rule (C), +3 business days.
- **Weekends:** skipped.
- **Federal holidays for 2026:** match 5 U.S.C. 6103 with the weekend
  shifts. They are reported but deliberately not skipped.
- **Dispute figures:** $400 and 120 days match 149.620(a)(2)(ii) and
  (c)(1).

### Not built / could not determine

- **Not built:** the new-estimate obligations in (b)(1)(vii) and (ix), and
  the co-provider deadline in (b)(1)(v). The document says it covers one
  practice only.
- **Could not determine:** whether *"none applies"* for diagnosis codes
  satisfies (c)(1)(iv). That is a legal reading, not arithmetic.

## 2. CLAIM DENIALS

### Confirmed defect

1. **MODERATE — an appeal filed on time is shown as past its window.
   REPRODUCED.**
   - **The code:** `submitted` counts as an open stage (`:4365`). `:4399` and
     `:4422` compare **today** with the payer's appeal window and never with
     `submitted_on`. So a filed appeal reads *"closed N d ago"*, lands in the
     note saying an appeal *"can no longer be filed"*, and is counted in the
     14-day "closing" badge (`:4369`).
   - Nothing checks that `submitted_on` was on or before the deadline,
     although the toast at `:4235` says the submission date *"is what proves
     it was inside the window"*.
   - **Driven:** a 90-day window, denied 2026-06-01, submitted 2026-06-20,
     showed *"sent 2026-06-20 closed 51 d ago"* with the past-window note.

### Correct as checked

- The app claims no rule-based deadline. Windows are entered per payer with
  a required source; with none entered, it shows *"no deadline on file"*.
- CARC/RARC codes are stored as given and never interpreted.
- Calendar-day arithmetic is correct.

### Could not determine

- Whether each payer counts its window from the denial date or from receipt
  of the remittance. That depends on the contract.

## 3. CREDENTIALING (client, against the server's evaluate output)

### Confirmed defects

1. **LOW–MODERATE — an expiring payer revalidation renders as "undefinedd".
   REPRODUCED; [verified by hand].**
   - `cdStatusBadge()` (`sairndental.html:3078`) prints `item.days+'d'`.
   - For payer-enrolment rows the server sends `revalidation_days`
     (`api/_lib/dental-credentials.js:447`), not `days`.
   - Driven: a board built from the server module, then
     `rCredentials(board)`, read *"Effective undefinedd"*.
2. **MODERATE, SERVER SIDE (cody's file) — a second DEA registration replaces
   the first. REPRODUCED in node.**
   - **The code:** `latestByKey` (`dental-credentials.js:241`–`251`) keys
     DEA rows by provider only, and the client form records no DEA state.
     So a second registration retires the first, and if the first carried
     the MATE attestation, MATE becomes outstanding again.
   - **The rule:** 21 CFR 1301.12(a) says *"A separate registration is
     required for each principal place of business or professional practice
     ... where controlled substances are ... dispensed"*.
   - **Driven:** two rows, AB1 (attested) and XY2 (not), produced a board
     with only XY2 and MATE outstanding 1.

### Correct as checked

- Every status the server can return has a rendering, and the four named
  enrolment states have badges. Others show their raw code, which is
  cosmetic.
- **DEA 60-day warning:** matches 1301.13(b), *"not more than 60 days before
  the expiration date"*. Other records use a 30-day default, and the tile
  says so.
- The could-not-run and still-checking states show `--`, `?` and `…`, never
  zero (b40–b42).
- **LOW:** the "CE Behind Pace" tile (`:3257`) adds *behind* and *overdue*
  together, so the label is slightly wrong.

### Could not determine

- The MATE Act's 8-hour requirement is not in eCFR, so it was not checked
  from primary text.

## 4. EXACT NEXT STEPS (in order)

1. **Denials:** a filed appeal is decided against `submitted_on` ≤ deadline.
   Exclude `submitted` rows from the closing and past-window counts, and say
   *"filed inside the window"* or *"filed N d late"* instead.
2. **GFE DOB/name:** `gfeMissing()` and the server check read the
   **snapshot** that will print, or the snapshot is refreshed on issue.
3. **GFE disclaimers:** (c)(1)(x) gets its two missing elements; (c)(1)(vi)
   moves above the list and gets its full text.
4. **`cdStatusBadge`:** use `revalidation_days` for enrolment rows.
5. **The holiday sentence** says *later*. `gfeHolidaysInWindow` also checks
   next year's 1 January observance.
6. **Server (cody):** key DEA rows by provider + registration number, or by
   provider + state.
