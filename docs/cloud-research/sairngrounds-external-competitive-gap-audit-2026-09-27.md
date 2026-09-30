# SAIRNgrounds external competitive-gap audit (2026-09-27)

**What this covers:**
- **Competitors:** golf clubhouse operations, golf turf maintenance, and commercial/HOA grounds contractors.
- **Ohio regulation:** pesticide applicators and records, pond permits, fertilizer, water withdrawal, clubhouse liquor, minors, OSHA.
- **Accuracy and liability.**
- **Adjacent market:** irrigation, course data and pace of play.
- **What practitioners say** about their current tools.

**Basis:** research pass dated 2026-09-27, in the isolated cloud-research lane. Docs only. It lands on the PR SAIRN1/SAIRN#18 branch.

**Claim:** session `cloud` claimed this work before starting, in commit `e3b8b0cd` on `origin/main`, subject `sairngrounds`. The claim also covers this session's lane handoff. `check` returned CLEAR.

**Internal code findings are in §1.2, separate from the external research.** They are written up for the build session that owns SAIRNgrounds. Nothing was fixed.

---

## 0. Read this before quoting anything

### 0.1 Network access and how reliable the sources are

**Page fetches are still blocked.**
- At 04:02 UTC on 2026-09-27, `example.com` was still refused (gateway 403).
- Each of the five research lenses tried one fetch, of foreupgolf.com, youraspire.com, codes.ohio.gov, agri.ohio.gov and capterra.com. **All five returned `EGRESS_BLOCKED`.**
- The cause is the environment's standing egress policy, the same diagnosis as SAIRNcash doc §0.1.

**Every external claim below is therefore graded [SNIPPET].** That means it comes from the search tool's summary of a result page, not from the page itself. §9 lists what to open first once fetching works.

**Budget:** 190 WebSearch calls, 38 per lens, and every lens stayed within its cap. Five WebFetch probes were made, all blocked.

### 0.2 Corrections to premises, including this pass's own brief

1. **Ohio's turf applicator category is Category 8 (Turf Pests), not "6D".** Aquatic is **3a** and ornamental is **6a**. [SNIPPET] [OSU catlist](https://pested.osu.edu/catlist)
2. **There is no single golf-course liquor permit class in Ohio.** The idea of a "golf-course D-5" was not supported. What the snippets do show for golf:
   - permits issued at golf courses since 1984 cannot be moved to another location (ORC 4303.29);
   - there is an F-7 permit for nonprofit golf events;
   - an older version of the law issued D-6 Sunday-sales permits at publicly owned courses.

   The classes a given course holds depend on the course: D-4 for a private club, and D-1/D-2/D-3/D-5 for public courses, which is an inference.
3. **The Ohio caddie exemption for minors that the brief expected was not found.** ORC 4109.06 exempts lawn mowing and snow shoveling. It also exempts 16- and 17-year-olds at "seasonal amusement or recreational establishment[s]", which may reach seasonal golf but is unconfirmed. **Age and schooling certificates are still required.** No evidence was found that they were abolished in 2022.
4. **"Toro Intelli360" does not exist.** Toro's golf dashboard is **IntelliDash**, and its contractor software is **Horizon360**.
5. **ServiceTitan bought Aspire in 2021, not 2023.** The deal was announced 2021-06-30 and closed 2021-08-11.

---

## 1. Internal grounding

Measured from `sairngrounds.html` at `origin/main` `e3b8b0cd`. The file is 343,066 bytes and was last changed in `c0ae9a0a`. It has 24 nav panels. Counts come from grep and are floors, not exact totals.

### 1.1 Status of the 2026-09-03 audit rows (§6 of that document)

| Row | Then | At `e3b8b0cd` |
|---|---|---|
| A1 Flat-price positioning | Absent in grounds | **Still absent.** `flat fee\|unlimited users\|per-seat` × 0 |
| A2 Satellite / aerial measurement | Absent | **Still absent** (× 0). Acreage is typed by hand |
| A3 Review requests / win-back | Absent | **Still absent.** All 24 `review` hits are the internal QC queue |
| A4 Tee-sheet waitlist | Absent, "no tee-sheet model" | **Still no tee sheet** (`tee sheet\|tee time` × 0). Built since: **On-Course Caddie** and **Pace of Play**, both driven by the course's own mapped points and logged arrival times |
| B1 Multi-course operator | Absent | **Still absent.** 2 `portfolio` hits are incidental |
| B2 Multi-division (snow and so on) | Absent | **Still absent** (`snow` × 0) |
| B3 Purchasing / POs | Partial (inventory and vendors, no POs) | **Unchanged:** `purchase order` × 0 |
| B4 Unlimited users | n/a in grounds | n/a |

**Built since the 09-03 audit, or not covered by it:** a clubhouse side made up of these panels:
- **Pro Shop** retail POS;
- **Bar & Compliance**: licences, sale hours, age check, voids, and an append-only inventory log;
- **Bottle Scanner**: an AI reads the label *and* estimates the fill level;
- **Food Inventory**;
- **Irrigation**: a data layer only;
- **Water Features**;
- **Plant Database**: USDA PLANTS data;
- **Invasive Species**;
- **Property Ecosystem Health**;
- **Crew Training**;
- **Design Walk**;
- **DreamClose**.

### 1.2 Internal findings for the owning build session (not fixed here)

> Reads of `origin/main`, not runs. **Nothing was changed.**

**G-1: No pesticide or fertilizer application record exists.** This is a missing feature with regulatory weight, not a bug.
- `pesticide|herbicide|fungicide|insecticide` appears × 4. All four are an advisory `treatment:` string in the invasive-species reference list, such as "Cut-stump herbicide".
- `EPA` registration, `applicator`, `SDS` and `restricted use` each appear × 0.
- The app plans invasive treatments and schedules jobs, but cannot record a legally required application record (§3.1).
- The **Invasive Species** panel's subtitle says it covers "treatment planning/history … and compliance".
- **The owner should confirm what "compliance" refers to there before any customer reads it as pesticide compliance.**

**G-2: The bar's sale-hours gate cannot represent Ohio's hours, and its seeded default is open on Sunday.**
- `msbEnsureSaleHoursSeeded()` (~L4480) seeds **10:00–23:59 every day, Sunday included**. Its own comment calls this a "permissive placeholder … that MUST be reconfigured".
- `msbIsAlcoholSaleAllowedNow()` (~L4485) tests `cur >= start && cur <= end` on a single-day window.
  - **A window that crosses midnight cannot be expressed.** Ohio's 1:00 a.m. and 2:30 a.m. closes (§3.5) are examples.
  - Setting end = 01:00 makes every sale fail, so the operator must stop at 23:59. That is the **safe** direction: it blocks lawful sales.
- **The Sunday default is the unsafe direction.** In Ohio, Sunday sales need a D-6 permit plus local-option approval, 10 or 11 a.m. to midnight (§3.5). An operator who never reconfigures is allowed to sell on Sunday by default.
- **The permit dropdown lists only Texas (TABC) permit types**: "Mixed Beverage Permit", "Beer and Wine Permit", "Private Club Registration Permit". The app is otherwise framed for Ohio and the Midwest.
- Both the hours check and the "ID checked, age verified" box are enforced **in the client only**. A `git grep` found no check of `age_verified` or sale hours anywhere in `api/`. Whether the server should re-check is the owner's call.
- The age box verifies the **customer**. It does nothing about the **employee's** age by beverage type (ORC 4301.22: 19 or older for beer across a bar, 21 or older for wine and spirits).

**G-3: The Bottle Scanner ships the one feature the platform's own research said needed a freedom-to-operate opinion first.**
- `docs/2026-08-30-sairnfreedom-competitive-and-patent-scan.md` found live prior art on image-based bottle fill-level estimation. It said a clearance opinion must come *"before the feature reaches sales material"*.
- SAIRNgrounds' **Bottle Scanner** panel says: "One photo → Claude reads the label (brand) AND estimates fill level".
- `patent|freedom to operate|FTO|clearance` appears × 0 in `sairngrounds.html`.
- This pass's liability lens found **at least three US families** (§4.6):
  - **Partender US 9,576,267 (granted);**
  - **Vianet/Beverage Metrics US 11,639,868 (granted);**
  - **E-Commerce Exchange Solutions US 2019/0197466.** This one claims CNN pixel and meniscus analysis, which is the closest to an AI fill-level scanner.
- **No litigation was found. That is not clearance.**
- **The owner should check whether the SAIRNfreedom FTO gate was meant to be platform-wide.**

**G-4: Demo data is seeded for every licence type, as in SAIRNbuild (its I-2).**
- `init()` (~L2086) calls `seed()` (~L2046). `seed()` checks only `grd_seeded`, even though `VALID=['GRD-','DEMO-','SAIRN-']` (~L1328).
- A paying `GRD-` customer's first sign-in on a new device loads the "Fairview Golf Club / Rocky River Estates HOA / Lakeshore Corporate Park" demo properties, jobs, quotes and golf zones.
- `st()` stamps each record as changed (`grdStampChanged`). **Whether seeded rows are then preferred over server rows in the merge, or pushed to the server, was not checked.**

**G-5: Pace of Play is manual timing and should not be marketed as pace management.**
- It measures "minutes per hole … from real arrival times" (panel subtitle), which is logged manually.
- The commercial reference, Tagmarshal, uses continuous per-group GPS, geofences and a live map (§2.1).
- This is honest as a measurement tool. The finding is about how it is described to customers, not about the code.

**Already on the platform's radar, so not raised again:** nothing SAIRNgrounds-specific was found in `docs/SAIRN-OPEN-WORK-INDEX.md` for the items above.

---

## 2. Competitive / market lens

All rows are [SNIPPET]. **VSC** marks a vendor's claim about itself.

### 2.1 Golf operations (the clubhouse side)

| Product | Segment | Price (as reported) | Ownership, 2021–26 | Note |
|---|---|---|---|---|
| **foreUP** | Public and municipal courses | Modules: tee sheet $120, POS $130, F&B $120, billing $80, marketing $70 per month | Clubessential bought it in Feb 2021. **Xplor–Clubessential merger signed 2025-09-16, closed Mar 2026** (Xplor Golf & Club: foreUP, Clubessential, **taskTracker**, BlueGolf). "3,500+ customers" (VSC) | AI BI (May 2025); AI voice concierge (Jun 2025). **Lost at least 68 courses in early 2025, 43 of them to Lightspeed and Club Caddie** (smbGOLF, a party with a commercial interest) |
| **Lightspeed Golf** (Chronogolf) | Public and semi-private | From $325/mo | Lightspeed (public); **no sale of the golf unit** | "On Deck" re-offers cancelled tee times. Reported in Google I/O 2026 AI-agent booking. Installations: 1,200+ vs 1,700+ (the sources conflict) |
| **Club Caddie** (Jonas) | Public and semi-private; **Detroit-based** | About $249–299/mo | Jonas, Feb 2020 | **+20% growth in 2025** (smbGOLF). "2,500+ clubs" (VSC). The most likely clubhouse competitor in the Midwest |
| **GolfNow / Golf365 Pro** | Public | **Barter**: tee times given in lieu of fees. Critics estimate $130–150K/yr in value per course | **Versant**, a Comcast spin-off listed 2026-01-05. Owns EZLinks (2019) | About 3,300 facilities. A GM reported bartering **3,000+ tee times in 2024** |
| **Club Prophet** | — | Not found | Fullsteam, 2022-05-31 | — |
| **Clubessential / Jonas Club** | Private clubs | About $10–50K+/yr | — | Membership billing |
| **Tagmarshal** | Pace of play | About $10 per tag per month (40-tag minimum), or $500–1,500/mo (sources conflict) | Independent; Series A reported Oct 2024 | GPS tags per group, geofencing, live map. "15+ min" shorter rounds (VSC) |
| **Club Car / Visage** (GPSI) | Cart GPS | — | Platinum Equity (2021, $1.7B). Sale exploration reported late 2025 (unconfirmed) | Raintree Golf, Green OH, installed Visage Connect in Mar 2025 |

**Course data:**
- The major apps get course maps from **paid, professionally validated mapping**:
  - **iGolf** (about 40K courses; API from **$5K/yr**);
  - **GolfLogix** (sold to Revelyst, 2025-07-14);
  - **StrackaLine / StrackaGolf** (used by 18Birdies and Golfshot);
  - **Hole19** (its own in-house team).
- **Even iGolf's self-service mapping app sends staff submissions through professional validation.** SAIRNgrounds' "no paid course-data vendor" mapping is cheap and workable for one course. **Distance-to-pin figures from uncorrected, self-mapped points carry an accuracy risk that competitors reduce by validating.**
- **"L2 Golf" was not found.** The iGolf app's publisher is "L1 Technologies".

### 2.2 Golf turf maintenance

| Product | Features | Price | Ownership |
|---|---|---|---|
| **GreenKeeper App** | GDD and PGR models, **spray and fertilizer records "that meet state reporting requirements"** (VSC), inventory, tank-mix, **WhiteBoard** job board linked to sprayer records, GPS sprayer prescription maps (CIS) | **$2,750/yr**, one plan | Founded by UNL/UW-Madison faculty. **Simplot exclusive licensing** (date not established) |
| **ASB taskTracker** | Job board, labour, equipment, **chemicals**, GDD, safety training | Not found | **Clubessential, 2024-05-22.** "nearly 1,000 golf courses" (VSC). Offered to foreUP courses |
| **Playbooks for Golf** | **Coverage** (chemical and fertilizer records "for government compliance"), ezPins, Conditions (member comms), irrigation maps | Not found | "1,000+ clients" (VSC) |
| **Syngenta GreenCast Connect** | GDD, growth potential, ET, spray windows, Spiio sensors | Pro + Spiio $167 or $199.60/mo (conflict) | Syngenta; app launched Mar 2025 |
| **John Deere Ops Center PRO Golf** | Job boards, fleet location, preventive maintenance | License-based | 2024 launch |
| **Toro IntelliDash** | Irrigation and fleet dashboard. **Ingests taskTracker, Playbooks, POGO, Spectrum, Perry Weather** and others | Included with myTurf Pro (since Feb 2024) | Toro |
| **Rain Bird CirrusPRO** | IC System, ingests Spectrum and Watertronics data | — | Rain Bird |

**No public third-party API was found for either Toro or Rain Bird.** Both integrate through partnerships that bring data *into* their own dashboards. SAIRNgrounds' irrigation "data layer only, no live controller API calls" matches that reality. **Getting read by IntelliDash, as taskTracker and Playbooks are, is a partnership question, not an engineering one.**

### 2.3 Commercial and HOA grounds contractors

| Product | Notable | Price |
|---|---|---|
| **Aspire** (ServiceTitan, TTAN) | POs, consumables allocation, **chemical application tracking**, snow, **PropertyIntel aerial takeoff** (from Go iLawn). ServiceTitan IPO 2024-12-12 | Model unsettled: per user, unlimited users, or **0.5–1% of revenue** |
| **Granum** (LMN + SingleOps + Greenius, launched **2025-10-08**) | Bilingual EN/ES crew app (LMN); Attentive.ai aerial measurement | LMN $297 / $598/mo; implementation $847 |
| **Service Autopilot** (Xplor) | Chemical tracking; "Smart Maps" satellite measurement add-on | $49–499/mo. **7% annual escalator** and payment-processor exclusivity reported by a third party |
| **RealGreen** (WorkWave) | **Commercial applicator reports for regulatory audits**; satellite measurement; franchise rollups | About $199/mo + $995 setup |
| **Jobber** | Chemical tracking; AI Receptionist (Aug 2025) | $29–$599/mo |
| **BOSS LM** | Branches, snow, inventory | Not published |
| **Aerial takeoff** | Go iLawn (from $300/yr); **Attentive.ai** (about $27–37 per site; $30.5M Series B); SiteRecon | — |

### 2.4 What the competitive lens changes

1. **Grounds plus clubhouse is no longer unclaimed.** Since March 2026 **Xplor Golf & Club** owns foreUP (clubhouse) and taskTracker (maintenance), and markets maintenance to foreUP's public courses. How integrated the two are is unverified. **SAIRNgrounds' distinct ground is its reach into HOA and commercial grounds.** No golf vendor found covers that, and its invasive species, ecosystem and plant-database modules had no equivalent in anything found.
2. **Without a tee sheet, SAIRNgrounds cannot replace a course's clubhouse system.** It can sit next to one. The tee sheet anchors every clubhouse competitor and is now wired to AI booking agents. A course would then run two POS systems (§6.2 on reconciliation pain).
3. **Spray records and GDD are baseline features in both markets**, and GDD tools are partly free (Syngenta). G-1 is the most exposed gap.
4. **Aerial takeoff comes bundled in contractor estimating.** Partnering (Go iLawn, Attentive.ai) is cheaper than building it.

---

## 3. Regulatory lens (Ohio)

Every row is [SNIPPET] and **is not legal advice**.

### 3.1 Pesticides: ORC Chapter 921 and OAC Chapter 901:5-11

- **A commercial applicator licence is required to apply *any* pesticide on golf courses**, per ODA and OSU guidance ([ODA](https://agri.ohio.gov/divisions/plant-health/pesticides/commercial/commercial-applicator)). Categories:
  - **8 Turf Pests**;
  - **6a Ornamental**;
  - **3a Aquatic**;
  - **5a Industrial vegetation**.
- **The licence expires September 30 every year.** Recertification is on a **3-year cycle: 5 credit hours, including 1 core hour** and at least 30 minutes per category. The per-category minimum comes from a secondary source.
- **Records, OAC 901:5-11-10** ([rule](https://codes.ohio.gov/ohio-administrative-code/rule-901:5-11-10)):
  - made **in English, on the day of application**;
  - copied to the business location **within 10 days**;
  - **kept 3 years**.
  - Required fields for turf, ornamental and aquatic applications:
    - licensed applicator and trained serviceperson;
    - customer name and address;
    - **date and time of day**;
    - target pest;
    - area type, size and location;
    - trade name and **EPA registration number**;
    - dilution and total amount;
    - equipment;
    - **wind direction, wind speed and air temperature**.
  - OSU offers a **free online record-keeping tool**, which counts as a competitor ([OSU](https://pested.osu.edu/online-records)).
- **Posting, OAC 901:5-11-09:**
  - **"Public lawn" expressly includes "golf course play areas".**
  - Signs must be **at least 5×4 inches, at least 14 inches off the ground, and stay up 24 hours**.
  - Alternative for public lawns in municipalities: a **permanent 8×10 inch sign**.
- **The EPA Worker Protection Standard generally does not cover golf play areas.** EPA's list of excluded uses includes "lawns". It **does** cover sod grown for sale. The exact golf wording was not established.

### 3.2 Aquatic pesticides in ponds

- **Ohio EPA NPDES Pesticide General Permit OHG870003**, effective **2022-10-18** ([permit](https://dam.assets.ohio.gov/image/upload/epa.ohio.gov/Portals/35/permits/Pesticide_Application_Dischargers/OHG870003.pdf)).
- A **Notice of Intent with a $200 fee is required for copper pesticides** applied to waters of the state.
- A Pesticide Discharge Management Plan and an annual report are required above **80 lake acres or 20 stream miles** a year.
- **Not established:** whether a closed golf-course pond counts as "waters of the State". **That single question decides whether the permit reaches the Water Features module.**

### 3.3 Fertilizer

- **SB 150 certification (ORC 905.321, effective 2014-08-21)** is aimed at agricultural production for sale on more than 50 acres. It **very likely does not reach golf or HOA grounds.** That is an inference; no exemption was seen.
- **SB 1 (ORC 905.326, effective 2015-07-03)** says "No person in the western basin shall surface apply fertilizer" in three conditions:
  - frozen or snow-covered ground;
  - saturated ground;
  - more than a 50% chance of more than 1 inch of rain within 12 hours.
- **Whether SB 1 binds golf and HOA grounds could not be established.** The exemptions were not visible. **Treat it as possibly applicable.**
- It fits SAIRNgrounds' weather engine closely: a go/no-go rule for a western-basin property.

### 3.4 Water withdrawal

- **ORC 1521.16: register with ODNR when withdrawal *capacity* exceeds 100,000 gallons per day** (pump capacity, not actual use), and **file an annual report** of daily withdrawals and returns. ODNR's categories name "agriculture/irrigation (includes golf courses)" ([ODNR](https://ohiodnr.gov/buy-and-apply/regulatory-permits/water-use-management/water-withdrawal-facilities-registration)).
- **ORC 1522.12, Great Lakes Compact permits for new or increased withdrawals:** the thresholds **conflict** across sources (1 / 2 / 2.5 / 5 MGD).
- The liability lens reports that Ohio's rules **exempt withdrawals from golf-course pond impoundments**. This is a secondary source; verify it.
- SAIRNgrounds' Irrigation panel has zones and schedules but **no withdrawal log**.

### 3.5 Clubhouse liquor

- **Sale hours, OAC 4301:1-1-49** (version dated 2024-05-01):
  - **1 a.m. group:** D-1, D-2, D-3 without D-3A, **D-4**, F-class and others. No sales **1:00–5:30 a.m.** Monday–Saturday.
  - **2:30 a.m. group:** D-3 with D-3A, D-4A, **D-5**, D-5a–o and D-7. No sales **2:30–5:30 a.m.**
  - **Sunday is closed unless the venue holds a D-6.** D-6 (ORC 4303.182, effective 2022-03-23) allows **10 a.m.–midnight**, or **11 a.m.** where 1 p.m. sales were approved before 2009-10-16.
  - Snippet anomaly: D-5h and D-5k appear in both groups. Verify against the rule.
- **Golf-specific:**
  - Permits at golf courses issued since 1984-09-26 cannot be moved to another location (4303.29).
  - **F-7 permit** for nonprofit "qualified golf events": up to 8 days, 2 per year, $450.
  - Public-course carve-outs (4301.402).
- **Beverage carts:** the permit application requires a **diagram of the permit premises**. Whether a whole course can be inside those premises was **not established**.
- **Server ages (ORC 4301.22):** 19 or older to sell beer across a bar; 21 or older for wine and spirits; under-18 limits on handling.
- **Dram shop (ORC 4399.18):** a permit holder is liable for off-premises injury only if it **"knowingly sold"** to a **"noticeably intoxicated person"** or to someone underage. **Records of ID checks, refusals and cut-offs are therefore the defence.** The app stores `age_verified` on each sale (§1.2 G-2), which is the right primitive to have.

### 3.6 Minors: caddies and crews

- **ORC Chapter 4109:**
  - **Age and schooling certificates are still required.**
  - Hours for 14–15-year-olds: **7 a.m.–7 p.m.**, or **9 p.m. from June 1 to September 1**.
  - **SB 50** would have allowed 9 p.m. year-round with parental consent. It was **vetoed on 2025-12-04**; override status after January 2026 is unknown.
  - **No caddie exemption was found.**
- **Federal FLSA, 29 CFR 570.33:** 14–15-year-olds may not operate power-driven machinery, **"including … lawn mowers, golf carts"**.
- **An enforcement example is in §4.5.**
- SAIRNgrounds' crew scheduling has no age field or task gating (`minor|work permit|child labor` × 0).

### 3.7 OSHA

- **HazCom 2024 revision:** after a four-month extension (Federal Register, 2026-01-15), **employers must update labels, the written program and training for substances by 2026-11-20.** The mixtures date conflicts: 2028-07-19 or about May 2028.
  - **This is the date a chemical inventory and SDS register would be built against** (`SDS` × 0 in the app).
- **Heat rule:** still proposed; not final as of May 2026.

---

## 4. Accuracy / liability lens

All rows are [SNIPPET]. Status marks: **A** = allegation or proposed; **S** = settlement or consent order; **J** = judgment or assessed penalty.

### 4.1 Pesticides: in the region, penalties land on *who* applied, more than on missing logs

| Date | Party | Penalty | What was cited | Status |
|---|---|---|---|---|
| 2017–18 | Hillcrest Golf & Country Club (Indiana, OISC) | 28 counts × $250 = $7,000, reduced to **$2,450** | **No certified applicator.** The superintendent's licence belonged to his own separate business entity | J (reduced for good faith) |
| n/d | Donald Ross Golf Club (Indiana) | $2,000, reduced to $600 | No certified applicator | J |
| n/d | Dogwood Glen GC (Indiana) | $2,000, reduced to $700 or $400 (conflict) | Same violation | J |
| 2007 | TruGreen (NY DEC) | $150,000 | **Missing contracts, expired licences, no posting, undocumented training** | S (outside the date window; shown for context) |

- Source: [OISC case summaries](https://oisc.purdue.edu/pesticide/iprb/iprb_153_case_summaries.pdf).
- **No Ohio enforcement action against a golf course or lawn firm was found.**
- ODA's escalation path runs from a field notice of warning, to a warning, to a civil penalty, to licence action, to prosecution. **Material harm can double the calculated penalty.**
- **Design implication:** tie each application to a **currently certified applicator licensed to *this* business**, and refuse to log it without one (§3.1). That matches the cited violation directly.

### 4.2 Ponds and wetlands

- **Pikewood National GC (WV), 2017:** unpermitted stream impoundments and fill. **$1.8M** plus restoration (S). [EPA](https://www.epa.gov/archive/epa/newsreleases/clean-water-act-settlement-pikewood-national-golf-club-protects-wetlands-morgantown-wv.html)
- **Jayhawk Club (KS), 2021:** about 7,000 ft of streams affected without permits (S).
- **No fish kill from an aquatic herbicide at a golf pond was found with a penalty in 2015–26.**

### 4.3 Water

- **Kapalua (HI), 2025:** alleged irrigation with drinking water during a drought without the needed permit (A; Earthjustice).
- **No Ohio or Great Lakes golf withdrawal enforcement was found.**

### 4.4 Liquor and dram shop

- **No Ohio Liquor Control Commission or Ohio Investigative Unit action against a golf club was found.**
- A 2026 Missouri appellate case reversed a **$6.14M** golf-cart injury judgment; the course was not a party.
- **The risk here comes from statute, not case history** (§3.5).

### 4.5 Child labour

- **South Park Country Club (Fairdale KY), 2021-12-27:** **two 15-year-olds drove golf carts and handled bags.** Penalty **$6,190** plus **$21,507** back wages for 43 workers (J; [DOL](https://www.dol.gov/newsroom/releases/whd/whd20211227-0)).
- Topgolf (OR), 2023: minors assigned to prohibited tasks (J; amount not established).
- The 2026 maximum is reported as **$16,035 per minor**.

### 4.6 Worker injury and exposure

- **TruScapes (FL), 2024-01-10:** a mower operator drowned, pinned under a rider in a pond. **The rollover bar was not engaged and the slope exceeded the manufacturer's limit.** One willful citation; **$166,305 proposed**; a repeat of a 2015 fatality (A; [OSHA](https://www.osha.gov/news/newsreleases/region4/01102024)).
- **Two Illinois golf-course deaths in 2026**, one under a zero-turn mower in a pond (incidents).
- ***Johnson v. Monsanto***, a school groundskeeper with Roundup exposure: the verdict was reduced to **$20.5M**. This was manufacturer liability, not employer liability.

### 4.7 Bottle fill-level patents (see G-3)

| Patent | Assignee | Scope (snippet) |
|---|---|---|
| **US 9,576,267 B2** | Partender LLC | Computer-based inventory of full and partial liquor containers ([Google Patents](https://patents.google.com/patent/US9576267B2/en)) |
| **US 11,639,868 B2** | Vianet Group (formerly Beverage Metrics) | Container profile plus measured liquid height gives remaining volume ([Google Patents](https://patents.google.com/patent/US11639868)) |
| **US 2019/0197466 A1** | E-Commerce Exchange Solutions | Photographs, identifies bottles by shape, label or UPC, and computes volume from pixels, including the meniscus, **using CNNs**; grant status not established ([Google Patents](https://patents.google.com/patent/US20190197466A1/en)) |

**No litigation was found. Claim scope, expiry and maintenance status were not checked.**

---

## 5. Adjacent market: irrigation, course data, pace of play

These are covered in §2.1–2.2. The two decisions they leave for the owner:
- **Irrigation.** Integrating means **partnering with Toro or Rain Bird as a data source**, since neither has a public API. The current data-layer-only design is correct until then.
- **Course data.** Self-mapping is legitimate, but the leaders validate it. **A validation step before distances are shown**, even just a second walk or an aerial cross-check, would close the accuracy gap without a paid data licence.

---

## 6. Practitioner voice

This lens was thin:
- No Reddit, TurfNet-forum or GCSAA-forum threads surfaced.
- Most material came through trade press and review-site snippets.
- Quotation marks show words the result presented as the reviewer's own.

### 6.1 Superintendents: the real alternative is a DIY TV board, and labour goes untracked

- A superintendent-built **job board on a 55" TV driven by an old Toro irrigation PC, costing about $1,200**, shows assignments, mowing directions and radar ([Golf Course Industry](https://www.golfcourseindustry.com/article/computerized--job-board/)).
- **"Few superintendents regularly track labor"**, although labour is **55–70% of the maintenance budget**. USGA presents labour data as the way to talk to decision-makers ([USGA Green Section Record](https://www.usga.org/content/usga/home-page/course-care/green-section-record/58/issue-18/tracking-labor-hours-with-new-technology-.html)).
- **Crews are often largely Spanish-speaking, and job boards should be bilingual** ([Golf Course Industry](https://www.golfcourseindustry.com/article/bilingual-superintendents-maintenance-crew-spanish-english/)).
- **The opening:** turn job-board data into **budget-versus-actual reports for the green committee or HOA board** automatically. The board itself is already served by GreenKeeper WhiteBoard and taskTracker.

### 6.2 Golf operators: reliability and support drive switching

- **foreUP:** outages with no local backup; updates that "cripple" the software; slow weekend support. An operator switched to Sagacity + Toast over "frequent outages and limited support", and **running the tee sheet and POS as separate systems creates reconciliation work** ([The Golf Wire](https://thegolfwire.com/switch-from-foreup-to-sagacity-and-toast/)).
- **Lightspeed:** "Too many clicks to check people in"; duplicate customer profiles with Lightspeed Restaurant.
- **Club Prophet:** "Customer support is awesome when someone is available. The wait time is too long."
- **Club Caddie:** "member billing seems to be the area that I struggle with at times".
- **Implication:** a SAIRNgrounds pro-shop or bar module will be judged on **weekend uptime** and on how it reconciles with the course's tee sheet.

### 6.3 Contractors: price model and lock-in

- **Aspire:**
  - "very expensive vs everything else on the market";
  - users dislike "the 1% of revenue that they want";
  - "Aspire was significantly more than boss, and provides virtually the same thing just a little prettier".

  Source: LawnSite, quotes merged across threads.
- **SingleOps:** QuickBooks sync failing for **6+ months**; annual terms with "no way out".
- **Service Autopilot:** crew clock-ins not uploading; a payment processor forced on users after the Xplor acquisition.
- **LMN:** time tracking unreliable; the crew app crashed on offline photos; **has a bilingual EN/ES crew app**.
- **Jobber:** "not really specifically built for the green industry" (LawnSite).

### 6.4 Ratings as shown (weak signal)

| Product | Rating |
|---|---|
| foreUP | Capterra 4.6 (160) |
| Jobber | Capterra 4.5 (1,045) |
| SingleOps | Capterra 4.4 (107) |
| Service Autopilot | Capterra 4.1 (139); iPhone app 2.4 (90) |

Aspire's Capterra product ID in the brief (137862) and the one search returned (161544) differ; the correct one was not established.

---

## 7. Synthesis

### 7.1 External gaps, ordered by what an Ohio course or grounds firm would feel

1. **Pesticide application records and an applicator licence register (§3.1, §4.1; G-1).**
   - Records: every OAC 901:5-11-10 field, same-day entry, a 10-day copy, and 3-year retention.
   - Register: licence number, categories 8/6a/3a, the September 30 expiry, and recertification credits.
   - **Block logging an application without a currently certified applicator licensed to this business.** This is the most exposed gap, and every competitor in both markets covers it.
2. **Ohio-correct bar configuration (§3.5; G-2):**
   - Ohio permit classes instead of Texas ones;
   - hours driven by the permit's group, with midnight-crossing windows;
   - Sunday closed unless a D-6 is on file;
   - employee age checked by beverage type.
3. **Freedom-to-operate review before the Bottle Scanner is marketed (§4.7; G-3).**
4. **Minor-labour guardrails (§3.6, §4.5):** age and certificate on file, 4109 hour limits, and **a hard block on 14–15-year-olds operating golf carts and mowers**.
5. **Posting, pond and chemical-inventory records (§3.1–3.2, §3.7):**
   - tracking of 24-hour lawn signs;
   - copper Notice of Intent and permit-threshold flags;
   - an SDS register built against **HazCom 2026-11-20**.
6. **A water-withdrawal log** for properties with capacity above 100,000 gpd (§3.4), and **SB 1 western-basin fertilizer go/no-go** in the weather engine if SB 1 applies (§3.3).
7. **Mower rollover and slope pre-operation checks (§4.6).** These are the highest-severity documented losses in this lens.
8. **GDD and growth-potential models, aerial takeoff partnership, POs** (§2). These are parity items.

### 7.2 Internal findings, for the owning session (repeats §1.2)

1. **G-1:** no pesticide records, and an "Invasive Species … compliance" subtitle that could be misread.
2. **G-2:** sale-hours window cannot cross midnight; Sunday is open by default; permit list is Texas-only; enforcement is client-side only; employee age is not checked.
3. **G-3:** Bottle Scanner fill-level estimation shipped without the freedom-to-operate check the platform's own research asked for.
4. **G-4:** demo data seeds for every licence type.
5. **G-5:** Pace of Play should be described as manual timing.

### 7.3 Where SAIRNgrounds is on the right side, and should say so

- **HOA and commercial grounds reach, plus golf**, where no golf vendor found goes.
- **Invasive species, ecosystem health, plant database and water features:** no equivalent was found in any competitor.
- **A QC photo completion gate.**
- **An append-only bar inventory log, voids gated by role, and a per-sale `age_verified` flag.** These are the right basic pieces for a dram-shop defence (§3.5).
- **Irrigation as a data layer rather than claimed live control**, which is honest and matches how the market integrates (§2.2).
- **Self-mapped course data with no paid vendor.** This is cheap for one course. It needs a validation step (§5).

---

## 8. What this document does not establish or decide

- **No page was opened** (§0.1).
- **§1.2 was read, not run.** Two points in particular were not checked:
  - how seeded demo rows behave in the merge;
  - whether the server should re-validate sale hours and age.
- **Unresolved conflicts, kept as found:**
  - Great Lakes Compact thresholds;
  - HazCom mixtures employer date;
  - the D-5h/D-5k duplication;
  - Tagmarshal pricing;
  - Lightspeed installations;
  - GreenCast pricing;
  - Aspire's pricing model;
  - Jobber Plus;
  - Dogwood Glen's reduced penalty;
  - Aspire's Capterra ID.
- **Not established:**
  - whether a pesticide business licence is needed for on-property application;
  - trained-serviceperson rules;
  - the exact WPS golf wording;
  - whether closed ponds are "waters of the State";
  - whether SB 1 reaches golf or HOA grounds;
  - any Ohio lawn phosphorus rule;
  - the ODNR report due date;
  - which liquor classes Ohio courses actually hold;
  - how permit premises treat beverage carts;
  - the Ohio "G" permit;
  - whether the golf D-6 clause survives in current law;
  - SB 50's override status;
  - OSHA's top-cited standards for NAICS 561730/713910;
  - patent claims, status and expiry;
  - how integrated foreUP and taskTracker are;
  - Hole19 ownership;
  - "L2 Golf".
- **No legal advice, no pricing decision, no code change.** The only write outside `docs/cloud-research/` is this session's own `.claude/claims/cloud.json`.

## 9. What to re-read first, once the network allows

1. **codes.ohio.gov OAC 901:5-11-10, -09 and -02, and ORC 921.** These are needed before building G-1.
2. **codes.ohio.gov OAC 4301:1-1-49 and ORC 4303.182.** These settle the D-5h/k question and whether the golf D-6 clause survives. Needed before fixing G-2.
3. **Google Patents: US 9,576,267, US 11,639,868 and US 2019/0197466.** Check claims, status and expiry, for G-3.
4. **Ohio EPA OHG870003 and its fact sheet.** Settles whether closed ponds are covered.
5. **ORC 905.326** exemptions, and **ORC 1522.12** current thresholds.
6. **ORC 4109.06 and 29 CFR 570.33.**
7. **The Xplor/foreUP and taskTracker pages.** Settle how integrated they are.

**Still pending from earlier docs in this session:**
- SAIRNbuild §9;
- SAIRNfreedom §9.1;
- SAIRNsenior §9;
- SAIRNcash §9;
- SAIRNbiz "Decay".

## Sources

Every source is linked inline where it is used. All were retrieved on 2026-09-27, and all are [SNIPPET] (§0.1).

Internal sources, read at `origin/main` `e3b8b0cd`:
- `sairngrounds.html`
- `api/_resources/sairngrounds.js`
- `SAIRNGROUNDS-SCOPE.md`
- `docs/superpowers/specs/2026-09-03-competitive-gap-audit-build-vet-biz-grounds-cash.md` §6
- `docs/2026-08-30-sairnfreedom-competitive-and-patent-scan.md` (bottle-photo FTO note)
- `api/sd-data.js` (grep only)
