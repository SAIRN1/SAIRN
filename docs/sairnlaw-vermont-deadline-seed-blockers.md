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
