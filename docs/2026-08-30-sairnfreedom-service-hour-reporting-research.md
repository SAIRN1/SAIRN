# SAIRNfreedom — national service-hour and charitable-giving reporting requirements

> **CANONICAL DOCUMENT IS ELSEWHERE.** This file is an APPENDIX. The
> decisions, the merged statutory findings and the reconciliation record live in
> **`docs/superpowers/specs/2026-08-30-sairnfreedom-research.md`** — read that
> first. This file is kept as source-of-record for the full per-organization
> detail, the verbatim quotes and the citation list behind the summary there.


**Researched 2026-08-30.** Gate 3: item 8 of the phase-1 scope was flagged as
the one feature not researched to the same standard as the rest, and therefore
the one most likely to generate invented compliance fields. This is that
research, run before any schema.

Every requirement below traces to a URL that was actually fetched. Anything that
could not be confirmed is in **UNVERIFIED**, not stated as fact. A wrong field
definition here becomes a compliance error in real software, so an honest gap is
the correct output and a plausible guess is not.

---

## The headline finding

**National reporting categories and Ohio charitable-gaming categories are NOT
alignable. Two independent taxonomies are required, not one.**

National reports measure *what the post did and gave, including its own program
costs.* Ohio Rev. Code Ch. 2915 measures *where gaming net profit went.* A
dollar can be fully reportable on the American Legion's Consolidated Post Report
and simultaneously an impermissible destination for bingo net profit. These are
not two views of one field. Detail in §6.

**Second finding: there is no shared period boundary anywhere in this set.**
Four different fiscal years, four different deadlines, four different cadences.
Any hardcoded reporting period will be wrong for at least three organizations.

---

## 1. The American Legion — VERIFIED in full

**Requires hours AND dollars: YES.**

**Vehicle:** the **Consolidated Post Report (CPR)**, form `30-010 (2026)`,
artwork `#71IA1125`. Established 1975 by Resolution No. 7 (Oct 1974). Filed at
**MyLegion.org**, or on paper to The American Legion, ATTN: IT/Member Support
Services, P.O. Box 1954, Indianapolis IN 46206, or scanned to
`CPRandCSRforms@legion.org`. Sons of the American Legion squadrons file a
parallel **CSR**.

**Period: June 1 – May 31.** Verbatim: *"documents each post's activities for
June 1–May 31."*

**Deadline: July 1.** Verbatim: *"July 1 is the final date for transmittal to
National Headquarters for post reports to be included in the national tabulation
for the specified reporting year."* The online form *"opens before the end of
November and remains available through July 1"* with save-draft. Departments may
set earlier internal deadlines (Iowa's is June 15).

**Units — the most heterogeneous of the five.** 126 numbered items mixing four
data types:

- **Checkbox (X = Yes)** — e.g. #11 has a VA Voluntary Service coordinator; #33
  maintained a website
- **Counts** — e.g. #7 cases handled by service officer(s); #27 wake, funeral or
  memorial honors provided
- **Dollars** — ~29 fields. Form instruction: *"Do not report cents; round to
  the nearest dollar."*
- **Hours — four separate, non-overlapping buckets**, the most important schema
  fact here:
  - `#9` volunteer hours recorded at VA hospitals
  - `#83` hours of Community Service (estimated)
  - `#96` volunteer hours for C&Y programs and activities
  - `#126` any volunteer hours not captured above
- **Miles** — exactly one field, `#112` miles through ALR events

**Category sections, verbatim:** `VETERANS AFFAIRS AND REHABILITATION` ·
`NATIONAL SECURITY` · `MEDIA AND COMMUNICATIONS` ·
`VETERANS EMPLOYMENT AND EDUCATION` · `AMERICANISM` · `CHILDREN & YOUTH (C&Y)` ·
`INTERNAL AFFAIRS & MEMBERSHIP`

**Modelling detail that matters for Ohio:** the CPR distinguishes *money given
away* from *money the post spent on its own program*. `#93` cash aid given to
benefit children and `#94` value of goods given to children sit alongside `#101`
cost to post for parties, dinners, prizes and gifts, and `#104` administrative
costs. There are ~15 "cost to post for X" fields. **These are not charitable
disbursements in the Ohio sense** — see §6.

**Consequence of non-reporting:** award/recognition only, as far as verifiable.
Departments at 100% post reporting get a plaque at National Convention; data
feeds the National Commander's congressional testimony under the federal
charter. **No charter-standing or financial penalty verified.** Blanks are
explicitly permitted: *"If your post did not participate in a listed program…
leave that section blank."* Estimates are explicitly permitted.

---

## 2. VFW — VERIFIED (national period/deadline); categories from a department source

**Requires hours AND dollars: YES — plus miles and member counts.**

**Vehicle:** online **"Program Reporting"** in the members-only area, tabulated
by the **National Programs Office**. Each Post has a Community Service chairman
who is *"the only comrade designated to complete the Post's CS reports"*; the
**Department Community Service Chairman is the sole approving authority.**
Individual comrades file paper forms which the Post chairman consolidates, along
with the Auxiliary's hours, miles and money.

**Period: July 1 – June 30. Deadline: June 30**, from VFW National's own
`Deadlines-for-VFW-Programs.pdf` (updated 8/8/2024), asterisked as *"Required
deadline (by VFW National Headquarters)"*:

> `*June 30, Community Service Reports Deadline.`

Guidance says report **as activities occur, or at minimum monthly** — a rolling
entry system with an annual cutoff, not an annual form.

**Units — four numeric per activity:** `HOURS`, `MILES`, `MEMBERS`, `DOLLARS`,
plus a Who/What/When/Where/Why narrative and a category + **sub-category**.

Three unit rules that directly constrain column types:

- **Hours are cumulative person-hours:** *"IF 5 comrades worked to install a
  handicap ramp… and it took 2 hours for EACH… the CUMULATIVE TOTAL for your
  report is 10 HOURS."*
- **Hours must be DECIMAL, not integer:** *"If 5 minutes, enter .08. hours (5
  divided by 60). 3 minutes becomes .05 hours."*
- **Miles are per-comrade round trip:** *"don't forget the mileage for EACH
  comrade to get there and back!"*

**Categories** (from the VFW **Department of South Carolina** Community Service
Guidelines, 2025 — a department-level document, see UNVERIFIED):
`COMMUNITY SERVICE` · `AID TO OTHERS` · `AMERICANISM/CITIZEN EDUCATION` ·
`YOUTH PROGRAMS` · `YOUTH ACTIVITIES` · `SAFETY` · `MILITARY SERVICE`

**Eligibility exclusions — hard business rules, not guidance.** Work benefiting
the Post itself is **not** community service: post-home maintenance or
beautification, cooking or serving a meal for a Post fundraiser, **working on
bingo night**, mowing the Post lawn, flying the flag at the Post. Also excluded:
passing out Buddy Poppies, hours working on a fundraiser, honor guard for a
member's funeral, service to one's own church.

- **Cap:** *"credit will only be given for a maximum of 1,000 hours to any single
  organization within a 12 month period."*
- **No double-reporting:** an activity may be filed under a second category for
  program credit, but the second filing must carry **zero** hours, comrades,
  money and mileage.
- Safety briefings: only the presenter counts, not the audience.

**Consequence:** National Community Service Post of the Year awards. Stated
institutional stakes: *"VFW national reports the number of hours and the monetary
value of all our donated time and money to Congress"* and *"Reports that are
inflated or are not within report guidelines can jeopardize our tax-exempt
status."*

**Award impact formula:** Dollars + Hours + Mileage = Total Impact, hours valued
at the Independent Sector rate and miles at the IRS charitable rate ($31.80/hr
and $0.14/mi cited on a department site). **Treat both rates as year-specific
and configurable, never constants.**

---

## 3. Elks (BPOE) — VERIFIED, and the Ohio layer is the surprise

**Requires hours AND dollars: YES.** Verbatim: *"you should supervise the entry
of **dollars, hours and other vital statistics** directly into
https://www.elks.org/clms2web."*

**Vehicle:** **CLMS2Web**. Charity figures are page 2 of the Grand Lodge Annual
Report. Working data accumulates in the **Pending Charity Report**. A paper
**Charity Records Workbook** is mailed to each Lodge annually.

**Period: April 1 – March 31.** Verbatim: *"As soon after the Fraternal year
ends March 31, and before April 30, your total charitable figures are required to
be filed directly into CLMS2Web."*

**Deadline: before April 30.**

**Consequence — the only real penalty found in this entire research:**

> *"Contents of this Annual Report are so important to the continued operation
> of the Order that Lodge failure or tardiness in filing the reports carries a
> **$100 fine and possible probation, or harsher penalties**."*

**Categories: NOT VERIFIED.** Charitable programs are chosen from a **numbered
dropdown**; exactly one example value was visible (`1001- Youth Scholarship`),
with an instruction to enter figures *"without commas (numbers and decimals
only)."* The full code list is behind the CLMS2Web login. **Do not guess it.**

### The Ohio-specific Elks requirement — a second, monthly report

Not national. The **Ohio Elks Association** requires, on top of the national
annual report:

> *"Lodge Secretaries, please download the Monthly Government Relations
> Charitable Reporting Form below. This form is due by the 10th of the following
> month, every month. **THIS IS REQUIRED BY ALL LODGES TO SUBMIT**"*

The per-event capture form is **"SURVEY OF VOLUNTEER, YOUTH, CHARITABLE AND
COMMUNITY SERVICE PROGRAMS"** and its lettered columns are effectively a
ready-made schema:

| Col | Field | Rule as printed |
|---|---|---|
| — | Chairman/Committee, Event, Date | header |
| (B) | TOTAL NUMBER OF PEOPLE WITH YOU | *"Count individuals traveling with you - Not couples, teams or groups"* |
| (C) | NUMBER OF ELKS – INCLUDE YOURSELF | **(C) + (D) must equal (B)** |
| (D) | NUMBER OF NON MEMBERS | |
| (E) | TOTAL ELK HOURS | *"if 2 Elks worked 6 hours (2x6) = 12 hours"* |
| (F) | TOTAL NON ELK HOURS | |
| (G) | ELK MILES | *"Round trip Miles traveled to attend an event (x # of people in car)"* |
| (H) | NON ELK MILES | |
| (I) | NON CASH CONTRIBUTIONS | *"Cash value of contributions including, Food, Clothing, Gifts etc. Do not include hours or mileage here"* |
| (J) | CASH CONTRIBUTIONS | *"Actual cash, Checks, Money Orders or Purchase Value of Savings Bonds donated to charity…"* |

Footer: *"Must be completed and submitted by the 10th of the month following the
event."*

**The member/non-member split on hours AND miles is unique to Elks** among the
five. It cannot be reconstructed after the fact from a blended number, so if it
is not captured at entry it is lost permanently.

Ohio Elks also publishes a **"Charity Records Booklet – A Partial List of
Items"**. It is explicitly *partial*, OCR-degraded, and dated **2015-2016** — do
not build a picklist from it. It does list **"Bingo"** and **"Charity Poker
Night"** as reportable charitable items, which is the collision point discussed
in §6.

---

## 4. Moose (Loyal Order of Moose) — VERIFIED, with an internal contradiction

**Requires hours AND dollars: YES — plus miles and volunteer headcount.**

**Vehicle:** the **LOOM Heart of the Community Report**, submitted online
through the Admin Menu on the Moose International website; a fillable paper
version still exists. Heart of the Community is a standing committee mandated by
**General Laws Section 35.5**.

**Period:** quarterly, periods ending **July 31 / October 31 / January 31 /
April 30**. Fiscal year end April 30, so the fraternal year is **May 1 – April
30**.

**Deadlines: February 15, May 15, August 15, November 15**, each a line item on
Moose International's *2026 Lodge Reporting, Remittance and Submission Deadlines*
(revised 12/18/25):

> `2/15/2026  Heart of the Community Report - deadline for QUARTERLY submission`

**Units — and the critical structural difference.** The form asks for
`TOTAL MONETARY DONATIONS` · `TOTAL VOLUNTEER HOURS` · `TOTAL MILES DRIVEN` ·
`TOTAL NUMBER OF VOLUNTEERS` **once, for the whole quarter — not per category.**
The categories above them are **free-text narrative blocks only.** Moose wants a
quarter-level total plus prose. **Any schema forcing Moose data into
per-category numeric rows is inventing a requirement that does not exist.**

**Categories — two official Moose sources disagree with each other right now:**

| Layer | Fillable form at mooseintl.org | 2023 Officers' & Committeemen's Handbook |
|---|---|---|
| **Core** | Mooseheart/Moosehaven; Moose Youth Awareness; Tommy Moose; Safe Surfin'; **Special Olympics**; **Moose Alert** | Mooseheart & Moosehaven; Moose Youth Awareness; Tommy Moose; Safe Surfin'; **Moose Veteran's Program** |
| **Companion** | **Make-A-Wish, Big Brothers/Big Sisters**; D.A.R.E./Red Ribbon; Emergency Services; Scouting; Youth Sports; Salvation Army | **Senior Center/Children's Hospital**; D.A.R.E./Red Ribbon; Emergency Services; Scouting; Youth Sports; Salvation Army; **Special Olympics** |
| **Local** | 4 free-text slots | free-text; examples incl. Meals on Wheels, Adopt-a-Highway, Bloodmobiles, Toys for Tots, food pantry |

Special Olympics moved Core→Companion; Moose Alert and Make-A-Wish/BBBS appear
only on the form; Moose Veteran's Program and Senior Center/Children's Hospital
only in the handbook. **The paper form is stale relative to the handbook and the
live online form may match neither. This is the strongest single argument
against hardcoding any category enum anywhere in this feature.**

**Exclusion rule** (same shape as VFW's): *"Do not include activities which are
limited in scope or specifically for the benefit of members or their families."*

**Consequence:** reports are graded **Superior / Excellent / Good** by the
Membership Department. *"Timely filing… is one of the criteria used in
determining the Premier Lodge Award."* Four "Superior" ratings in a fiscal year
make a Lodge eligible for annual judging; top 20% Gold, next 30% Silver, final
50% Bronze. The grade is driven by *"a combination of the variety of efforts…
as well as the number of community service efforts"* — explicitly **not** an
hour or dollar threshold. The old fixed "6-Point Community Service Program"
targets are retired.

---

## 5. Eagles (Fraternal Order of Eagles) — NOT VERIFIABLE PUBLICLY

**Requires hours? Requires dollars? UNVERIFIED.**

foe.com has members-only sections named Compliance, Forms & Logos, Membership
Reports. Fetching `foe.com/forms-logos` returns:

> *"This content is password-protected. To view it, please enter the password
> below."*

That is the finding. No publicly reachable evidence of a required
community-service or charitable-giving report from local Aeries to the Grand
Aerie; no form, no deadline, no category list, no fraternal-year boundary.
Everything findable publicly is third-party IRS Form 990 aggregation, which says
nothing about internal reporting obligations. Grand Aerie: 614-883-2200 /
help@foe.com.

**Do not build Eagles fields by analogy to the other four.**

---

## Comparison table

| Organization | Hours? | Dollars? | Units | Period | Deadline | Categories found? |
|---|---|---|---|---|---|---|
| **American Legion** | **YES** — 4 distinct buckets | **YES** — ~29 fields, whole dollars | hours, dollars, counts, checkboxes, 1 miles field | **Jun 1 – May 31** | **Jul 1** | **Y** — 7 sections, 126 items, verbatim |
| **VFW** | **YES** — decimal person-hours | **YES** | hours, **miles**, **members**, dollars + narrative | **Jul 1 – Jun 30** | **Jun 30** (National-required) | **Partial** — 7 top-level from a *department* doc |
| **Elks (national)** | **YES** | **YES** | dollars, hours, "other vital statistics"; numeric program codes | **Apr 1 – Mar 31** | **before Apr 30** | **N** — dropdown behind login |
| **Elks (Ohio overlay)** | **YES** — Elk/non-Elk split | **YES** — cash vs non-cash | people, Elk/non-Elk hours, Elk/non-Elk miles, non-cash, cash | per event | **10th of following month, monthly** | **Partial** — 2015-16 partial list only |
| **Moose** | **YES** — one quarterly total | **YES** — one quarterly total | donations, hours, miles, **volunteer count** — quarter-level, not per-category | **May 1 – Apr 30** | **Feb 15, May 15, Aug 15, Nov 15** | **Y but contradictory** |
| **Eagles** | **UNVERIFIED** | **UNVERIFIED** | — | — | — | **N** — password wall |

---

## 6. Ohio charitable-gaming interaction — NOT alignable

This section independently corroborates
`2026-08-30-sairnfreedom-orc-2915-verification.md`, reached by a different route
(the **authenticated** ORC PDF rather than the section page). Both reads agree on
the (V)(2)/(V)(3) split.

**ORC 2915.01(V)** — *"'Charitable purpose' means that the net profit of bingo,
**other than instant bingo or electronic instant bingo**, is used by, or is
given, donated, or otherwise transferred to, any of the following:"*

- **(V)(1)** an IRC 509(a)(1)/(2)/(3) organization that is a governmental unit or
  501(c)(3);
- **(V)(2)** a **veteran's organization** — VFW and Legion posts — net profit
  used *"for the charitable purposes set forth in division (B)(12) of section
  5739.02… awarding scholarships… donated to a governmental agency, or… used for
  **nonprofit youth activities**, the purchase of **United States or Ohio flags**
  that are donated to schools, youth groups, or other bona fide nonprofit
  organizations, **promotion of patriotism**, or **disaster relief**"*;
- **(V)(3)** a **fraternal organization** — Elks, Moose, Eagles — *"that has been
  in continuous existence in this state for **fifteen years** and that uses the
  net profit **exclusively** for religious, charitable, scientific, literary, or
  educational purposes, or for the prevention of cruelty to children or animals,
  **if contributions for such use would qualify as a deductible charitable
  contribution under subsection 170 of the Internal Revenue Code**"*;
- **(V)(4)** a volunteer firefighter's organization.

**The cross-referenced 5739.02(B)(12) list, verbatim** — this closes the open
item left by the statute verification: *relief of poverty; improvement of health
through the alleviation of illness, disease, or injury; operation of an
organization exclusively for the provision of professional, laundry, printing,
and purchasing services to hospitals or charitable institutions; operation of a
home for the aged; operation of a noncommercial educational radio or television
broadcasting station; operation of a nonprofit animal adoption service or county
humane society; promotion of education by an institution of learning…; operation
of a parent-teacher association, booster group, or similar organization…;
operation of a community or area center in which presentations in music,
dramatics, the arts, and related fields are made…; the production of
performances in music, dramatics, and the arts; or the promotion of education by
an organization engaged in carrying on research in, or the dissemination of,
scientific and technological knowledge.*

### Six evidenced mismatches

1. **Different axis entirely.** National reporting measures what the post did
   and gave, including its own program costs. Ohio measures where gaming net
   profit went. Not two views of one field.
2. **Hours have no place in Ohio 2915 at all.** Volunteer hours are central to
   all four national reports and appear nowhere in the charitable-purpose test,
   which is about net profit dollars. **Hours are single-tagged; dollars are
   double-tagged.**
3. **Ohio enumerates purposes no fraternal report has a bucket for** — home for
   the aged, noncommercial educational broadcasting, animal adoption/humane
   society, laundry/printing/purchasing services to hospitals.
4. **The national reports contain buckets Ohio does not permit for a veterans
   post.** CPR `#28` cost to post for wake/funeral/memorial services, `#104`
   administrative costs, `#111` ALR operations, `#116` NEF operations are
   legitimate CPR line items and are **not** on the (V)(2) permitted-destination
   list. A shared category would silently assert compliance the statute does not
   support.
5. **Veterans and fraternal orgs get different Ohio tests from each other.**
   (V)(2) gives an enumerated list plus youth activities, flags, patriotism and
   disaster relief. (V)(3) gives a narrower, IRC-170-conditioned list plus the
   15-year precondition and an **"exclusively"** requirement. A single shared
   `charitable_purpose` picklist would be wrong for one of them.
6. **Instant bingo is carved out and separately regulated.** 2915.101 imposes
   tiered mandatory distribution. **The game type that produced the money
   changes the rule the disbursement must satisfy**, so game type has to be on
   the record. *(Percentages summarized, not quoted verbatim — re-read before
   encoding.)*

**A direct collision worth flagging:** the Ohio Elks Charity Records Booklet
lists **"Bingo"** and **"Charity Poker Night"** as *reportable charitable
activities*, while VFW guidance lists *"working on bingo night"* as explicitly
**not** community service — and Chapter 2915 treats the same evening as a
*revenue source* for both. Three different meanings, one event.

---

## UNVERIFIED / COULD NOT CHECK

- **Eagles: everything.** Password wall. Build nothing by analogy.
- **Elks CLMS2Web charity program code list.** Exists as a numbered dropdown;
  one example value seen; full list behind Lodge Secretary login.
- **The current Elks Charity Records Workbook.** Only public artifact is an
  Ohio-published, OCR-damaged, explicitly partial list dated 2015-2016.
- **VFW sub-categories.** Confirmed to exist, reachable only through Members
  Only.
- **Whether the VFW's 7 categories are the national list.** Source is the VFW
  Department of South Carolina. The national deadline and period *were* verified
  from vfw.org's own PDF; the category names were not.
- **The live Moose online HOTC form.** Paper form and 2023 handbook contradict
  each other; the form rendered in the Admin Menu today may match neither.
- **Whether Moose HOTC filing is mandatory or strongly incentivized.** The
  committee is mandated by General Laws 35.5 and filing ties to awards; no
  penalty clause found.
- **American Legion CPR late window.** A 2024 search snippet mentioned reporting
  open until Sept 1 with awards forfeited; the 2026 legion.org article fetched
  directly does not say this. Unverified for the current year.
- **Whether CPR item numbers are stable across years.** 2025-26 artwork
  `#71IA1125`, 2024-25 `71IA1024`. Different artwork numbers strongly suggest an
  annually changing item set; the two forms were not diffed.
- **ORC 2915.101 exact percentages and threshold.** Summarized, not quoted.
- **Ohio AG / Casino Control Commission licence-renewal forms.** The statutory
  recordkeeping duty (2915.10) was verified; the actual renewal application was
  not fetched. It may impose its own categories. *(See also the AG's separate
  electronic-instant-bingo account and quarterly-report requirements recorded in
  the competitive scan doc.)*
- **Any API or bulk-import path** into MyLegion, CLMS2Web, VFW Program Reporting
  or the Moose Admin Menu. All four are manual member portals; no public API
  found.

---

## SCHEMA IMPLICATIONS

### Safe to build now — each traces to something actually read

**Shared activity/event record.** Date, title, narrative description (all four
want prose; VFW requires Who/What/When/Where/Why and Moose's entire category
structure *is* prose), organization served, and a `verified_by` field — VFW
requires verification *"by an authorized representative of that organization."*

**Numeric types, not just names:**

- `hours` **DECIMAL**, not integer. VFW mandates `.08` for five minutes; an
  integer column silently truncates it to zero.
- `hours` semantics are **cumulative person-hours** — stated identically by VFW
  (5 comrades × 2 hrs = 10) and Ohio Elks (2 Elks × 6 hrs = 12). Store the
  product; store headcount separately.
- `miles` DECIMAL, **round trip × people in the vehicle** — same rule in both
  VFW and Ohio Elks wording.
- `volunteer_count` its own column. Moose asks for it as a first-class total; it
  is not derivable from hours.

**Money must be two columns, never one.** Elks separates non-cash (I) from cash
(J); the CPR separates `#93` cash aid from `#94` value of goods. Collapsing them
destroys information both organizations ask for. The Elks instruction *"Do not
include hours or mileage here"* also means the in-kind column must not carry
imputed volunteer-time value.

**`disbursement_direction`** — money *given away* vs *cost to post for our own
program*. ~15 explicit "cost to post for X" CPR fields sit beside donation
fields, and this distinction is what determines Ohio permissibility (§6.4).

**`funding_source`** — charitable-gaming net profit / general funds /
restricted. The Ohio tagging obligation attaches **only** to the gaming-sourced
portion; without this, every disbursement drags an irrelevant compliance field.

**`game_type`** on gaming-sourced rows — bingo / instant bingo / electronic
instant bingo. 2915.01(V) excludes the latter two and 2915.101 governs them
differently.

**Member/non-member split on hours and miles.** Only Ohio Elks demands it, it
cannot be reconstructed later, and it collapses harmlessly to a single number for
the other four. Capture it.

**`counts_toward_national_service` boolean.** VFW and Moose both carry explicit
exclusions (post-benefit work, member-only activities, fundraiser hours, bingo
night). Without it the totals inflate and the Department chairman — the sole
approving authority — rejects the report.

**Category tags many-to-one with exactly one metric-bearing tag.** VFW's
anti-double-report rule made structural: an event may carry several category tags
for program credit, but only one may carry the hours/dollars/miles/members.
Enforce in the model, not by trusting the user.

**Two independent taxonomies on a disbursement:** `national_program_category` and
`ohio_charitable_purpose`. Neither derives from the other, and the Ohio one must
be conditioned on organization type.

**Reporting periods as per-organization configuration, never constants.** Four
verified fiscal years and four verified deadline schemes, plus the Ohio Elks
monthly overlay. One period generator driven by config; hardcoding even one will
be wrong for three organizations.

**Retention minimum 3 years** on anything touching gaming net profit (2915.10),
with an itemized recipient list — name, amount, purpose — as a first-class
table, not a free-text memo. Plus a field for **where the physical records are
kept**, since the AG must be notified of that location.

**VFW's 1,000-hour-per-organization-per-12-months cap** as a validation warning
at entry, not a stored value.

### Must NOT be built until someone with member access confirms

- Any hardcoded **VFW sub-category** list. Not seen; the 7 top-level names are
  from a department document, not National.
- Any hardcoded **Elks CLMS2 program code** enum. One example value is not a
  list.
- Any hardcoded **Moose category** enum. Two official sources disagree *today*.
  Store as configurable rows with an effective date.
- **Anything at all for Eagles.**
- **CPR item numbers (1–126) as stable database keys.** They are scoped to a
  form year. Key on a stable internal concept and map item numbers per year.
- **Any auto-submit or API integration.** All four are manual portals; no API
  verified. Design for export-to-CSV and human re-entry, and do not promise
  submission.
- **A single shared `charitable_category` picklist across post types.** Per §6
  this encodes a compliance claim the statute does not support.
- **The Independent Sector hourly value and IRS charitable mileage rate as
  constants.** Both change annually; both came from a department page.

---

## Sources

- American Legion Consolidated Post Report 2025-2026 (form 30-010, artwork 71IA1125) — legion.org
- The American Legion — "Legion and Sons reporting due July 1" — legion.org
- VFW National — Deadlines for VFW Programs (updated 8/8/2024) — vfw.org
- VFW Dept. of South Carolina — 2025 Community Service Guidelines — vfwsc.org
- Elks Lodge Secretary's Manual (BPOE) — elks.org/clms2web
- Elks CLMS — Grand Lodge Annual Report help — elks.org
- Elks Grand Lodge District Deputy packet — elks.org
- Ohio Elks Association — Charitable Reporting — ohioelks.com/charitable-reporting
- Ohio Elks — charity survey form (editable) — ohioelks.com
- Ohio Elks — Charity Records Booklet partial list (2015-16) — ohioelks.com
- Moose International — LOOM Heart of the Community Report form — mooseintl.org
- Moose International — 2026 Lodge Reporting, Remittance and Submission Deadlines (rev. 12/18/25) — mooseintl.org
- Moose — 2023 Officers' & Committeemen's Handbook — mooseintl.org
- Moose International General Laws (Aug 2025) — mooseintl.org
- Pennsylvania Moose Association — Heart of the Community — pamoose.org
- Fraternal Order of Eagles — Forms & Logos (password-protected) — foe.com
- ORC 2915.01 authenticated text, eff. 9/30/2025 — codes.ohio.gov
- ORC 5739.02 authenticated text, eff. 9/30/2025 — codes.ohio.gov
- ORC 2915.10 — bingo records — codes.ohio.gov
- ORC 2915.101 — instant bingo net profit distribution — codes.ohio.gov
