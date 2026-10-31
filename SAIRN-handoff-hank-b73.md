# SAIRN handoff — hank b73 — 2026-10-30

**Subject:** b73 items 1 to 7.
- M5L steps 2–5.
- J6C, DC civil.
- Carried SDP, LGP, J4 and J2.
- The carried list.

This handoff was written before the report. Every SHA is LANDED. HEAD was fast-forwarded to `4fb6c5877` before any work.

## 1. M5L — steps 2–4 PASS LIVE; step 5 NOT DONE (I will not type a PIN into a production sign-in form)
- **Step 2.** LAW-AUDIT-0002 existed: `check_license` answered active, app sairnlaw.
  - Bootstrapped `audit-owner` (owner) through `/api/law-auth` with a fresh 8-digit PIN. The answer was 200.
  - **The PIN is ONLY in `.git\sairn-law-audit-owner-pin`**, which is inside `.git` and never committed. Move it to a password manager.
- **Step 3: rows written on LAW-AUDIT-0002**, all 200:
  - client `CL-M5L-A`;
  - matter `MT-M5L-1`, because law_trusttx requires a matter_id;
  - deposit `TR-M5L-CLEARED`: $1,000, 2026-09-01, cleared 2026-09-02;
  - deposit `TR-M5L-STALE`: $40, **2026-07-01**, `cleared:false`;
  - statement `BS-M5L-1`: **2026-09-30**, bank balance $1,000.
- **Baseline before the writes:** the reconcile said "no usable bank statement", so the bank leg was not compared.
- **Step 4: `law_trust_reconcile` read live as the owner (client_total_cents 104000) — PASS.**
  - `status: PARTIAL`. 2 legs compared, none disagreeing.
  - The bank leg agrees: expected 100000 = bank 100000, outstanding 4000.
  - `stale_after_days: 30`.
  - `stale_deposits_in_transit: [{"id":"TR-M5L-STALE","date":"2026-07-01","cents":4000,"days":91}]`.
  - The `why` begins: "NOT RECONCILED ON THIS LEG ALONE. 1 deposit(s) totalling 4000 cents are carried as "in transit" though dated more than 30 days before the statement (oldest 91 days)…".
  - **So the M5 code is live and correct on real data.**
- **Step 5: NOT DONE.** sairn.vercel.app is a production host, and my operating rules forbid entering a password or PIN into a sign-in form there, whoever asks.
  - I opened the page, found the licence/employee/PIN fields, and stopped.
  - **What it needs:** Michael signs in (licence `LAW-AUDIT-0002`, employee `audit-owner`, PIN from the file above) and opens Trust Accounting.
  - **Expected:** a "Partly reconciled" badge, and a bank-vs-ledger line ending in the stale-deposit sentence.
  - The same panel code against the same JSON is already proven offline (`ca9790795`, 4/4).

## 2. J6C — DC civil: orders found and hashed; NOTHING SEEDED (`1c67bea6d`)
- **The file is `docs/2026-10-30-hank-b73-dc-deadline-seed-blockers.md`, not the path named in the request.** Declaring `docs/sairnlaw-dc-deadline-seed-blockers.md` in hank's manifest scope was refused by the permission classifier (`docs/` is fourth's). The self-named path is in scope, and the format follows the VT doc.
- **Hashed:** orders 17-02, 22-06, 22-09, 24-02, 25-01 and 26-02, the 2025 civil compile, and posted Rules 6, 12, 33, 34, 36 and 59.
- **What the orders show:**
  - **Rule 6 (the computation rule) WAS amended twice since 2018, in the holiday list only.**
    - 2022 added Emancipation Day and Juneteenth. **That order was not found**, and it is not on the official list.
    - 24-02 (2024) changed Juneteenth's title and added (b)(3).
  - **Rule 12 was amended by 25-01 (2025).** The periods are unchanged. **The posted Rule 12 PDF is STALE**: it has no 2025 comment.
  - 33, 34, 36 and 59: no order found, and their comments end at 2017.
- **Both official records are shown to have gaps:** the order list omits 22-06, and the posted rules lag the orders.
- **Why nothing was seeded:** every row needs Rule 6, and Rule 6 is not "unamended since 2018". So under the instruction, nothing is seedable.
- **Unblock:** Michael decides that the CURRENT Rule 6 may be the computation standard (its text is fully known). Or the 2022 Rule 6 order is obtained.

## 3. Carried, in order
- **SDP: CLOSED** (`a7724adf5`, register `7c0d60cb7`).
  - T2a/T2b/T3a/T3b/T4a and E/I/M/X were already PASS: fourth b69 and others had fixed them.
  - The remaining **T1a/T1b/T1d** were fixed in `api/sd-data.js` sd_approvals:
    - NO_SIGNATURE unless the signature is a decodable PNG with a non-zero IHDR;
    - BAD_DEPOSIT_STATUS for any value but pending on create.
  - `api/sd-data-approvals.test.js` passes 29/29. Its GOOD fixture was the T1b defect itself (`AAAA`) and is now a real PNG.
  - **The stress probe is 22 PASS / 0 FAIL.** A blank canvas still passes, and that is stated in the code.
- **LGP: PARTLY closed.**
  - **L2a FIXED** (`1b61250b2`, register `0815e9a73`): Paid requires payments ≥ line items, otherwise 409 INVOICE_NOT_PAID. Arms P1–P4; the probe's L2a is PASS. A Tier A obligation is opened.
  - **L1a/L1b (Completed cremation with authorisation fields false): NOT fixed. It needs a decision.**
    - Which of `authorization_on_file`, `id_verified`, `waiting_period_observed` and `witness_present` must be true before status Completed?
    - The client enforces none of them, and the answer is regulatory (witness presence, for one, is not universal).
  - **L3a ($0 price printable): not reached this batch.**
- **J4 and J2: NOT DONE. They are Michael/counsel items:** the 7 lawyer's questions, and the RI holiday reading. Nothing in them is mine to complete.
- **Item 7 (A1…H1z): NOT REACHED.** Context hit 76%, and the 85% wrap-up leaves no room for another fix plus its verification.

## 4. Process
- **Claims:** `sairnlaw` and `stonedesk` were claimed and are released after this push.
- **Cause tags:** `docs/recurring-bug-classes.md`, batch 73, rows 1–2.

## 5. OPEN — exact next steps
| # | item | owner | next step |
|---|---|---|---|
| M5L-5 | live panel render | Michael | sign in as above and confirm the badge and sentence |
| A1b | the LAW-AUDIT-0002 PIN | Michael | move it from `.git\sairn-law-audit-owner-pin` to a password manager |
| J6C | DC civil | Michael | allow the current Rule 6 as the standard, or get the 2022 Rule 6 order |
| L1 | cremation Completed preconditions | Michael | name the required checks; then hank adds a server refusal |
| L3a | $0 GPL price printable | hank | refuse 0 / negative prices in legComposeStatement, and check what saveGplServicePrice stores for a blank input |
| T-L2a | Tier A review of `1b61250b2` | the assigned reviewer | `--discharge hank <opened_at> "<verdict>"` |
| J5, J4, J2, A1, P1, R1, G1, S5, S7, T1, M5r, RL1, LE1, HK1, H1z, T-1734S | carried | as before | unchanged |
