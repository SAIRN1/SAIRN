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

## b69 (2026-10-29): the official Judiciary rules page was read directly. NEITHER condition can be confirmed there, so this stays NOT SEEDED

**Seeding requires both of these, by Michael's b69 instruction:**
1. the date the V.R.C.P. is current through;
2. whether e-service still gets +3 days under Rule 6(e).

The official page answers neither. Read at vermontjudiciary.org/attorneys/rules on 2026-10-29:
- **It does not host a compiled current V.R.C.P., and it gives no current-through date.** Its words are: "All Vermont court rules are available through LexisNexis. The Vermont Judiciary does not administer the LexisNexis website and does not have responsibility for the accuracy of the information provided there."
  - So the Judiciary's own designated source for current text disclaims accuracy.
  - That source is the advance.lexis.com container, which is a script-driven viewer. It cannot be read by tools/sairn_http.py.
- **The promulgated list is "Promulgated Rules Over the Last Two Years"**, in the page's own heading.
  - This confirms what b68 inferred from the years on the page.
  - The effective dates printed in the orders now listed run from 2022-10-01 to 2025-10-01.
- **Every VRCP and VREF order on that list was fetched and its text extracted** (14 PDFs):
  - VRCP: 4(c); 9.2; 11(e)/43/56; 16.2/26(f); 55(a); 65(b)(1); 79(a); 80.12/81(a).
  - VREF: 1(g)/2(h)/3/5(d)/6(c); 5 (emergency); 5(d)(1); 7(a)(7); 9(d); 11(f).
  - None of them mentions Rule 6(e), "three days", "3 days" or "additional time", and none amends Rule 5(b).
  - **That establishes no 6(e) change from about 2022-10 to 2026-10. It establishes nothing from 2018-01-01 to then.**

**Net result:**
- The 2018 text of 6(e), which adds 3 days for (4) electronic service, is the last text an official Judiciary page shows.
- An amendment between 2018 and 2022 can be neither confirmed nor ruled out from any official page.

**What would unblock it:** either of these from a human.
- A Lexis printout of V.R.C.P. 6, 12, 33, 34, 36 and 59 that shows its "current through" line.
- The Judiciary's own answer to two questions: were Rules 6/12/33/34/36/59 amended after 2018-01-01, and does 6(e) still add 3 days for e-service?

## b70 (2026-10-30): BLOCKED. The exact missing source, named

Michael's b70 instruction was to pull V.R.C.P. 6/12/33/34/36/59 directly from vermontjudiciary.org, not from Lexis, and to seed only if a current-through date is confirmed.

**Measured this batch:**
- **No V.R.C.P. rule text is hosted on vermontjudiciary.org.** I walked the site's own sitemap (https://www.vermontjudiciary.org/sitemap.xml, 9 pages). It lists 17,442 URLs, and none of them is a V.R.C.P. page or a VRCP promulgation order.
- **The site search** (/search, /search/node) returns 404.
- **The rules page** (https://www.vermontjudiciary.org/attorneys/rules) still says "All Vermont court rules are available through LexisNexis".
- **The promulgated list** (https://www.vermontjudiciary.org/attorneys/rules/promulgated) still covers "the Last Two Years". It names no order touching 6, 12, 33, 34, 36 or 59 (b69, 14 orders read).

**THE MISSING SOURCE:**
- an official Vermont Judiciary copy of the Vermont Rules of Civil Procedure, Rules 6, 12, 33, 34, 36 and 59, that carries an "as amended through" or "current through" date; **or**
- the Vermont Supreme Court promulgation orders for any amendment to those rules between **2018-01-01 and 2022-10**.

That window is the gap: no official page reaches it. The only official text of these rules is the 2018 order, which is LCJR material on legislature.vermont.gov (b67).

**Not used, by instruction:** Lexis.

## b71 (2026-10-30): retried on the Judiciary's own rules pages, not a sitemap crawl. Still NOT FOUND

**Read directly on 2026-10-30.** The sha256 is of the page bytes as served; the pages are dynamic, so it pins what was read, not a permanent file.

| page | bytes | sha256 |
|---|---|---|
| https://www.vermontjudiciary.org/attorneys/rules | 43211 | `6504b353e79e42893759549731e6ff83f516e2d5bd8f84fa923b43dbb2561c2f` |
| https://www.vermontjudiciary.org/attorneys/rules/promulgated | 132853 | `94c972167105ea396c82f7f20f9b721bc31e7b422638897f00524df39b9cff91` |
| https://www.vermontjudiciary.org/attorneys/rules/proposed | 40901 | `42d411b1ebea1d020618819abe0941fb20b075578fde6ad6cd3b393804dca56e` |

**What the pages hold:**
- **The rules page links only these:** LexisNexis (twice), "Proposed Amendments" and "Promulgated Rules Over the Last Two Years". It has no rule text and no current-through date.
- **The promulgated page** has no order that amends V.R.C.P. 6, 12, 33, 34, 36 or 59.
- **The proposed page** links only Lexis.
- **The obvious rules paths all return 404:** /court-rules, /rules, /attorneys/court-rules, /attorneys/rules/court-rules, /civil/rules, /attorneys/rules/civil and /about-vermont-judiciary/rules.

**EXACTLY WHAT WOULD UNBLOCK IT** (either is enough):
1. **A Vermont Judiciary-issued copy of V.R.C.P. 6, 12, 33, 34, 36 and 59 with a stated "current through" or "as amended through" date.** The likely sources are a PDF from the Court Administrator's Office or the Civil Rules Advisory Committee, or a Judiciary email answer that carries that date.
2. **The Vermont Supreme Court promulgation orders, dated 2018-01-01 to 2022-10, for any amendment to those six rules, plus a statement that there are no others.** The Court Administrator's Office holds them; the website lists only two years.

Option 1 is the cleaner of the two. With either in hand, the ND pattern runs as for DC.
