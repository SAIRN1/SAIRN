# SAIRNlaw — Vermont deadline seed: NOT GATED (no reachable official current rule text)

**Run 2026-10-29, hank b64, fifth in Michael's J1 order. Verdict: BLOCKED ON SOURCE.** This is the Kentucky shape
(`docs/sairnlaw-kentucky-deadline-seed-blockers.md`, Blocker 1).

## What was tried (2026-10-29)
- The vtcourts.gov rules index (`/attorneys/rules/promulgated`, HTTP 200) lists individual **promulgation orders**,
  such as `PROMULGATED-VRCP4c--STAMPED`.
  - It has **no compiled current V.R.C.P.**
  - No promulgation order for the 2018 "Day is a Day" Rule 6 change appeared in the index fetched.
- `vtcourts.gov/court-rules`, `vermontjudiciary.org/court-rules` and `.../VRCP.pdf`: all HTTP 404.
- What is reachable and official:
  - `vtcourts.gov/.../List of All Changes Final.pdf`, a summary of the 2018-01-01 "Day is a Day" changes, for example
    "V.R.C.P. 12(a)(1)(A) … 21 days". It is a summary, not rule text.
  - A 2017 **RECOMMENDED** (draft) order hosted by the Legislature.
  - Neither is the rule in force, so neither may be quoted as the rule.
- Third-party copies (state-rules.com, courtrules.net, rulesofcivilprocedure.com) are not permitted primary sources
  for a gate.

## What is established (not enough to seed)
- 1 V.S.A. § 371 (legal holidays) is reachable at legislature.vermont.gov.
- Per the official change list, Vermont moved to the federal "day is a day" count on 2018-01-01. **The 3 days for
  certain service methods remain, under V.R.C.P. 6(e).**

## What would unblock it
- The promulgated order adopting current V.R.C.P. 6 (2018), and each period rule to be seeded, from vtcourts.gov.
- Or a Michael/counsel decision to accept the West/Lexis official compilation as the source.

## b65 (2026-10-29): the URL supplied as the compiled source is NOT the rules
- `https://www.vtcourts.gov/media/595` redirects to
  `https://www.vtcourts.gov/sites/default/files/documents/AR-2014_VRCP.pdf`.
- That is the **Advisory Committee on Rules of Civil Procedure 2014 Annual Report** (5 pages, 116,701 bytes). It
  contains no rule text. Its item III.6 says the Committee "will continue to develop amendments to V.R.C.P. 6".
- **Vermont is still not seeded.** The blocker is unchanged: the current V.R.C.P. text, as promulgated, is still needed.

## b66 (2026-10-29): the official index was searched as directed. There is no Rule 6 text on vtcourts.gov.
- `https://www.vtcourts.gov/attorneys/rules` ("Proposed and Promulgated Rules", HTTP 200) has **no compiled rules
  link**. For the compiled text it points to "LexisNexis - Vermont Statutes, Court Rules and Administrative Code"
  (advance.lexis.com, a script-driven app that cannot be fetched).
- `/attorneys/rules/promulgated` lists only recent orders, among them VRCP 65(b)(1), 16.2/26(f), 4(c) and 55(a).
  **None is a Rule 6 order.** The `?page=N` query returns the same page, so older orders (including the 2017/2018
  "Day is a Day" Rule 6 order) are not reachable this way.
- **Vermont is still not seeded.** The only official compiled source is the Lexis publication, which needs a human
  session. Unblock options:
  - Michael pastes the Rule 6 text, Rules 12/33/34/36/59 and the order's effective date from Lexis, with the
    retrieval date;
  - or supplies the direct vtcourts.gov URL of the 2017 Rule 6 promulgation order.

## b67 (2026-10-29): PRIMARY SOURCE FOUND — UNBLOCKED, to be seeded next batch
- **What it is:** the Vermont Supreme Court's promulgation order, filed with the Legislative Committee on Judicial Rules.
  - **URL:** https://legislature.vermont.gov/Documents/2018/WorkGroups/Judicial Rules/October 23, 2017 Meeting/W~Erik Fitzpatrick~Materials for Judicial Rules Meeting on October 24, 2017 ~10-23-2017.pdf
  - **Size:** 5,761,306 bytes, 1,450 extracted lines.
- **Promulgation clause** (extracted line 131): "That these rules and forms, as added or amended, are prescribed and
  promulgated effective January 1, 2018."
- **"RULE 6. TIME"** begins at line 189, with its Reporter's Notes at lines 270–297:
  - (a) is the "day is a day" rule, the federal language;
  - (a)(7) covers applicable statutes;
  - (e) adds three days, following FRCP 6(d) as of 2005.
- **Caveat for the gate:** this is the text AS OF 2018-01-01. Any later amendment to Rule 6 or Rules 12/33/34/36/59
  must be checked against vtcourts.gov's promulgated list before seeding.

## b68 (2026-10-29): the 2018 text READ; NOT seeded. Three named gaps, each with its unblock

**Source read.** The LCJR materials PDF (b67 URL) was fetched through `tools/sairn_http.py`. It is 5,761,306 bytes, 104 pages, sha256 `ddf5c7a29b5aef0128a38b699112e4b3ca1bc3f1e22a9f65a3754fd147d5be00`. Text was extracted with pypdf.
- The civil order starts on page 13: "VERMONT SUPREME COURT, SEPTEMBER TERM, 2017, ORDER PROMULGATING AMENDMENTS TO THE VERMONT RULES OF CIVIL PROCEDURE". It is promulgated effective January 1, 2018.
- **The PDF is a scan of a REDLINE.** OCR runs the struck value and the new value together, for example "20 21 days" and "4-0 14 days". So each figure below is the SECOND of its pair. Each one was confirmed against the Reporter's Note, which states the change in words.

**What the 2018 text says (V.R.C.P., as amended eff. 2018-01-01):**

| rule | period | trigger |
|---|---|---|
| 6(a)(1) | the federal "day is a day" text: exclude the trigger day; count every day; a last day that falls on a Saturday, Sunday or legal holiday runs to the next day that is none of those | -- |
| 6(a)(6) | "legal holiday" = (A) any day declared a holiday by the President or Congress; (B) any day declared a holiday by the State of Vermont | -- |
| 6(e) | **3 days are added after the period would otherwise expire under 6(a)** when service is made under 5(b)(2) mailing, (3) leaving with the clerk, **or (4) sending by electronic means** | service |
| 12(a) | answer: 21 days after service of the summons and complaint; reply to a counterclaim: 21; after notice of the court's action on a motion: 14 | service / notice |
| 33(a), 34(b) | answers / response: 30 days after service; a defendant may take 42 days after service of the summons and complaint | service |
| 36(a) | 30 days after service of the request; a defendant may take 42 days after service of the summons | service |
| 59(b), (d), (e) | motion for a new trial or to alter or amend: not later than 28 days after entry of judgment; opposing affidavits: 14 days | entry |

**The holiday referent is reachable and express.** 1 V.S.A. § 371(a), read at legislature.vermont.gov on 2026-10-29, lists 13 days:
- New Year's Day; Martin Luther King, Jr.'s Birthday; Presidents' Day; **Town Meeting Day** (the first Tuesday in March); Memorial Day; **Juneteenth** (added by 2023 No. 140, eff. 2024-05-30); Independence Day; **Bennington Battle Day** (Aug 16); Labor Day; Indigenous Peoples' Day; Veterans' Day; Thanksgiving; Christmas.
- § 371(b) moves a holiday that falls on a Saturday or Sunday, but only for "State departments, agencies, and offices". That is the same question as Rhode Island's J4 (7)(b).

**WHY THIS WAS NOT SEEDED.** Each gap below is one where a seed would have to guess.

1. **AMENDMENTS AFTER 2018 CANNOT BE RULED OUT FROM THE OFFICIAL LIST.**
   - vermontjudiciary.org/attorneys/rules/promulgated lists 139 links. Its VRCP orders are 4(c), 9.2, 11(e)/43/56, 16.2/26(f), 55(a), 65(b)(1), 79(a) and 80.12/81(a). **None of them amends 6, 12, 33, 34, 36 or 59.**
   - The page has no pagination, and it is a rolling window: the years it mentions run 2020 to 2026.
   - So it cannot show an order from 2018-01-01 to the start of that window. "Nothing on the page" is therefore not "no amendment".
2. **6(e)'s three days for ELECTRONIC service.**
   - The federal rule stopped doing this in 2016. Vermont's 2018 text still does.
   - Vermont's e-filing rules (V.R.E.F.) have their own promulgation orders, for example "VREF 1(g),2(h),3,5(d),6(c)" and "VREF 11(f)". An order of that kind could change e-service timing without being titled VRCP.
   - Whether +3 still applies to e-service decides every row triggered by service.
3. **§ 371(b) observed days** (above). The early direction is to treat the shifted Friday or Monday as a holiday.

**What would unblock it:**
- a current compiled V.R.C.P. 6/12/33/34/36/59 with an "as amended through" date, which a human can get from the Judiciary or the Lexis court-rules link on legislature.vermont.gov; or
- confirmation that the promulgated page is complete back to 2018. In either case, also answer whether e-service still gets +3.

**Then:** the ND pattern. Rows triggered by entry (59) and the holiday table can be seeded without settling gap 2. Rows triggered by service cannot.
