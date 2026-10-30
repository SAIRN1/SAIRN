# SAIRNlaw — District of Columbia (Superior Court, Probate Division) deadline seed gate

hank b70, 2026-10-30. Michael's b70 item 2: "seed Washington D.C. Superior Court probate rules next, same sourcing standard as VT". Item 5 asks for the primary-source URL of every rule or statute seeded, and each one appears in full below.

**Verdict: PASS for 5 rows, Probate Division only. The rows are built and tested, but they are not yet pushed or loaded (see §7).** The DC *civil* rules (J6's original 6/12/33/34/36/59) are not seeded by this gate.

## 1. Sources — every one read directly from the official site on 2026-10-30

| what | primary-source URL | bytes / sha256 |
|---|---|---|
| Rules of the Superior Court index ("Last Updated : 02/13/2026") | https://www.dccourts.gov/superior-court/rules | — |
| **Superior Court Rules of the Probate Division, compile EFFECTIVE 8-22-2022** (the source of every row) | https://www.dccourts.gov/sites/default/files/superior-rules/Superior-Court-Rules-of-the-Probate-Division-EFFECTIVE-8-22-2022.pdf | 421,115 / `cd045c1e333347528524adcc6378da1937a567d2738c158dc3d46771f11a44b9` |
| Rules and Promulgation Orders list (66 orders, 2004 to Promulgation Order 26-04 of 2026-09) | https://www.dccourts.gov/superior-court/superior-court-resources/superior-court-orders?search=&order_type=Rules+and+Promulgation+Orders | — |
| D.C. Code § 28-2701, for the observed day | https://code.dccouncil.gov/us/dc/council/code/sections/28-2701 | — |
| Civil Rule 6, read for comparison only, not seeded | https://www.dccourts.gov/sites/default/files/rules-superior-court/Civil%20Rule%206.%20Computing%20and%20Extending%20Time%20Time%20for%20Motion%20Papers.pdf | 98,864 / `df0cc0b9cf2f0ed09243927bc39c0d8031872005fdd618dec3cc29aa1a5030d9` |

**Current-through basis.** VT failed this standard. DC meets it in three steps:
1. The newest Probate Division compile on the official rules page is effective **2022-08-22**. The page also links "Probate Division (Cases Prior to August 22, 2022)", which confirms 2022-08-22 as the cut-over date.
2. The official promulgation-order list runs to Promulgation Order 26-04 (2026-09). It carries **no order amending the Probate Division rules after 2022**; the last probate orders on it are 10-03 (2010) and 09-06 (2009).
3. So the rules seeded here are the current rules **as of the list's newest entry, 2026-09**.

A second "Download All Rules" file, `Superior Court Rules of the Probate Division.pdf`, carries PDF metadata dated 2017-05-09. It is the pre-2022 set and was **not** used.

## 2. Computation — Prob. R. 128(a)

The rule is the federal text. Quoted verbatim:

> "(A) exclude the day of the event that triggers the period; (B) count every day, including intermediate Saturdays, Sundays and legal holidays; and (C) include the last day of the period, but if the last day is a Saturday, Sunday, or a legal holiday, the period continues to run until the end of the next day that is not a Saturday, Sunday, or legal holiday."

(a)(5) adds that the "next day" counts backward when a period is measured before an event.

Encoded as `dc_probate_r_128a`, using `impl: 'frcp_6a'`.

## 3. Holidays — Prob. R. 128(a)(6), an express list

The rule's text:

> "(A) the day set aside by statute for observing New Year's Day, Martin Luther King Jr.'s Birthday, Washington's Birthday, Memorial Day, Juneteenth, Independence Day, Labor Day, Columbus Day, Veterans' Day, Thanksgiving Day, or Christmas Day; and (B) any day declared a holiday by the President or Congress, or observed as a holiday by the court."

**How the calendar applies it:**
- **Encoded:** the eleven days (A) names, on "the day set aside by statute for observing" each one. D.C. Code § 28-2701 and 5 U.S.C. 6103(b) both move a Saturday holiday to the Friday before and a Sunday holiday to the Monday after.
- **New Year's Day 2028** falls on a Saturday, so it is observed **Friday 2027-12-31** and is filed under the 2027 calendar.
- **Columbus Day** is the day D.C. Code § 28-2701 now names Indigenous Peoples' Day. Both fall on the second Monday of October.
- **NOT encoded, EARLY:**
  - DC Emancipation Day (April 16) and Inauguration Day. § 28-2701 makes both holidays "for all purposes", but (A) does not name them. They count only if the court observes them under (B), and the court's observed list was not read.
  - Any other day falling under (B).
  - An inaccessible clerk's office under (a)(3).

  Each omission can only make a computed date EARLIER than the true deadline.

## 4. Mail — Prob. R. 128(d)

The rule's text:

> "When a party may or must act within a specified time after being served and service is made by mail or leaving with the clerk, 3 days are added after the period would otherwise expire under this Rule 128(a)."

**No seeded row runs from service**, so no row carries a service extension.

## 5. Seeded (5 rows). Every row's `authority.url` is the compile URL in §1.

| rule_id | citation | count | trigger |
|---|---|---|---|
| dc-probate-r105c2-response-to-petition-or-objection | Prob. R. 105(c)(2) | 14 days | the petition or objection is FILED |
| dc-probate-r112c1-inventory | Prob. R. 112(c)(1) | 90 days | appointment (or an order for continuing supervision) |
| dc-probate-r112c2-conservator-inventory | Prob. R. 112(c)(2) | 60 days | appointment of the conservator |
| dc-probate-r113-demand-for-formal-audit | Prob. R. 113(e)(6)(B) | 20 days | approval of the final account |
| dc-probate-r125c2-reconsideration-after-final-account | Prob. R. 125(c)(2) | 20 days | entry of the order approving the final account |

**NOT seeded, and why:** Prob. R. 125(c)(1), the general motion for reconsideration.
- Its rule: "no later than 28 days after entry ... and prior to the entry of the order approving the final account".
- That second cut-off is an event this engine cannot see. Any date it gave could be LATE, so the row is excluded.

## 6. Verification
- **`api/_lib/deadline-dc.test.js` passes 21/21.** Every expected date was derived by hand before the engine ran. The cases include:
  - the observed Independence Day 2026 (Fri 07-03 → Mon 07-06);
  - Emancipation Day as a working day (2026-04-16 stays 2026-04-16, EARLY by design);
  - Christmas 2027 observed on a Friday;
  - the cross-year New Year shift (2027-12-31 → 2028-01-03).
- **Ablation:** with the shift entries removed, two of those cases move onto the holiday itself.
- **Every other deadline suite still passes.** The 16 per-state suites that pin the coverage key list now include `dc`.

## 7. Standards push only. The seed is NOT pushed and NOT loaded this batch
**This follows the ND pattern: standards push, then load, then verify, then the seed push.**
- The push gate refuses a seed file that the live licence does not yet hold (LAW-PINNACLE-2026: 5 rules and 6 holiday calendars MISSING).
- The load needs a SAIRNlaw licence key, an employee and a PIN, and this session has none of them.
- So this push carries only the standard (`dc_probate_r_128a`), the `JURISDICTION_COVERAGE.dc` entry, the labels and this gate.

**Three files are built, tested 21/21, and PARKED** outside the repo until the load:
- `sql/sairnlaw_deadline_seed_dc.json`
- `sql/sairnlaw_deadline_calendars_dc.json`
- `api/_lib/deadline-dc.test.js`

**Next, in order:**
1. Deploy the standard.
2. With the licence credentials, run `python tools/load_deadline_seed.py dc --dry-run`, then the real load. The load is an upsert.
3. Verify a CHANGED result on identical inputs: a dc/probate compute goes from NOT_PROVISIONED to the dates in §6.
4. Commit the three parked files and push.
