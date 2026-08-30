# SAIRNfreedom — phased build spec

**Written 2026-08-30 (CC). This is a SYNTHESIS, not new research.** Everything
statutory here traces to
`docs/superpowers/specs/2026-08-30-sairnfreedom-research.md` (canonical) and its
two appendices. Feature scope comes from the expanded deep-dive list. Where a
feature arrived as a *name* without detail, it is listed in **§9 Needs source
detail** rather than guessed at.

**Status: nothing built. No schema, no app file, no API branch.**

---

## 1. The two structural decisions everything else hangs off

### 1a. Capability-based permissions, with officer titles as a per-org-type MAPPING

The named officer structure — **Commander, Vice Commander, Adjutant, Finance
Officer, Chaplain, Judge Advocate, Historian, Service Officer,
Sergeant-at-Arms** — is the basis of the permissions model, as directed. But it
must not be the *enum*.

**Reason, and it is the same lesson the statutory research already forced:** the
verified finding in the canonical doc is that ORC 2915.01 gives veteran's
organisations **(V)(2)** and fraternal organisations **(V)(3)** different
charitable-purpose tests inside one state. Organisation type is already a
first-class axis of this product. **Officer titles vary on that same axis** — a
VFW post's finance officer is the *Quartermaster*; Elks and Moose use different
titles again. Hardcoding one vocabulary produces a product that is wrong for
three of the five target orders in exactly the way a shared `charitable_purpose`
enum would have been.

**So:** `capability` is the stable thing; `officer_title` is display and is
mapped per `org_type`.

| Capability | Held by (Legion/VFW vocabulary given) | Notes |
|---|---|---|
| `post.govern` | Commander | Sole holder. The "last active provisioner" role |
| `post.govern.deputy` | Vice Commander | Acts when Commander unavailable — this is the recovery path, see §1c |
| `records.write` | Adjutant | Minutes, roster, membership records |
| `finance.write` | Finance Officer (VFW: Quartermaster) | **Bonded.** Personally responsible for post funds |
| `finance.approve` | Commander + Finance Officer | Two-party. See §4 |
| `gaming.operate` | designated bingo workers | **Cannot be compensated** — ORC 2915.09(D)(1) |
| `gaming.report` | Finance Officer | Owns the 2915.10 record set |
| `canteen.operate` | bar staff | Shift-scoped, not officer-scoped |
| `canteen.close` | Canteen manager + Finance Officer | Nightly reconciliation |
| `member.admit` | Adjutant | |
| `services.refer` | Service Officer | **Scoped §9a.1** — referral/scheduling/accreditation-tracking only, never claim preparation |
| `ceremonial.manage` | Sergeant-at-Arms | Honor guard equipment, details |
| `history.write` | Historian | |
| `legal.review` | Judge Advocate | Bylaws, disputes |
| `chaplain.pastoral` | Chaplain | Likely no data capability at all — confirm |

**Reuse, do not reinvent:** `sairn-employee-auth-scaffold` already ships PIN
credentials, signed session tokens, lockout and the credential-deactivation
lifecycle across thirteen apps. The officer model is a role vocabulary on top of
`api/_lib/auth.js`, not a new auth system.

### 1b. Tenancy: the auxiliary distinction is a schema decision, not a UI one

- **Sons of the American Legion (S.A.L.)** — a **sub-category of the same
  entity**. Same licence, same treasury, same tenant. Model as a
  `member_category`, not a separate post.
- **Auxiliary / Women of the Moose** — **genuinely separate, co-located legal
  entities.** Own treasury, own officers, own reporting. Model as a **separate
  tenant** that shares a physical location.

**Getting this wrong is unrecoverable in the direction of merging.** Two entities
merged into one tenant means one treasury where the law expects two, and
un-merging afterwards means re-attributing every historical transaction. The
canonical research already establishes each post is independently governed and
independently licensed; the auxiliary is the same fact one level down.

**Consequence:** `location` and `entity` are different keys from day one, and the
district rollup (§7) aggregates *entities*, not buildings.

### 1c. The provisioning trapdoor — design it in, do not discover it

The platform already has a live failure of this shape: a licence with credential
rows and **zero rows that are both active and hold a provisioning role** is
unrecoverable through the API. RF-PINNACLE-2026 sat in that state and nothing
noticed.

A post whose only `post.govern` holder is deactivated is the same trapdoor.
`post.govern.deputy` exists partly to prevent it. `tools/employee_auth_guard_check.py`
already enforces the two safe end states — zero rows, or at least one active
provisioner — and any SAIRNfreedom credential SQL must carry that guard.

### 1d. Banner: animated app-wide, static on onboarding — DECISION 2026-08-30

**This supersedes the earlier "static everywhere" branding call.**

- **Animated flag banner, consistently, on the dashboard and every other page.**
  One banner component, one behaviour, everywhere. An animation that appears on
  some pages and not others reads as a bug, not a choice.
- **Onboarding is the exception and is STATIC.** The one place a new member is
  being asked to concentrate is the one place the banner does not move.

**The constraint that produced the earlier call still stands and is why this is
recorded rather than just changed.** Animated distortion was previously
attempted and rejected as visually broken — it read as water or TV static — and
the guidance was to avoid canvas/SVG turbulence-filter animation on a working
dashboard. **That failure was a bad implementation, not a bad idea.** The
decision now is that it gets built properly, by an agent, as real work — not
attempted again in a quick mockup tool.

**So the prohibition that survives is on the technique, not the effect:** do not
reach for turbulence filters and call it done. Whatever is built must be
reviewed against `sairn-visual-review` on a rendered page at real size before it
is called finished, because the last attempt looked fine in source and wrong on
screen.

**Still holds, unchanged:** no literal reproduction of the American flag —
trademark/copyright caution — so this is a red/white/blue diagonal-stripe motif
with a small star cluster, not a flag.

---

## 2. Phase 1 — Foundation (no dependencies; everything else needs this)

| # | Feature | Notes |
|---|---|---|
| 1.1 | Entity + org_type + licence model | `org_type` drives §1a titles AND the §5 charitable categories |
| 1.2 | Officer roles / capability model | §1a. On `sairn-employee-auth-scaffold` |
| 1.3 | Member roster, categories, S.A.L. sub-category | §1b |
| 1.4 | Dues, renewal, **three-layer fee structure** | Defined — see **§2a**. One-time initiation, annual dues, national per-capita. The third is a **pass-through liability, not revenue** |
| 1.5 | Conditional dues/fee waivers | Defined — see **§2b**. Active-duty, recently-separated (24 months, **expiring**), sick/in distress. **Elks-confirmed only — org-type-specific, do not assume** |
| 1.6 | Post profile: licence types, **15-year test** for fraternal orgs | OAC 109:1-4-08 Types I/II/III gate lawful activity; ORC 2915.01(V)(3) 15-years-continuous-existence gates fraternal disbursement eligibility |
| 1.7 | Branding shell | Red/white/blue, **diagonal** stripe, small star cluster, no literal flag reproduction. Post name + org type + city in header. **ANIMATED banner across the whole app — see §1d** |

**Phase 1 exit criterion:** a real post can be created, its officers provisioned,
its members enrolled and dues taken — and the app knows its org type, licence
types and eligibility facts, because everything downstream branches on those.

### 2a. The three-layer fee structure — three money types, not three prices

| Layer | Set by | Typical | What it actually is |
|---|---|---|---|
| **Initiation fee** | the lodge | one-time, at admission | Lodge revenue |
| **Annual dues** | the lodge | **~$25–150/yr** | Lodge revenue |
| **National per-capita assessment** | the national body | every member, every lodge | **A PASS-THROUGH LIABILITY** |

**The third layer is the one that will be modelled wrong if it is treated as a
price.** The lodge *collects* per-capita from the member and *owes* it upward.
Money collected on behalf of another entity is a **liability, not income** — the
lodge is a conduit. Booking it as revenue overstates the lodge's income by the
whole per-capita line and understates what it owes.

**It also has a deadline and a real penalty**, from the service-hour appendix:
Elks per capita is **due May 1**, and late filing of the Annual Report that
accompanies it carries *"a $100 fine and possible probation, or harsher
penalties"* — the only hard penalty found anywhere in that research.

Build consequences:

- Three separate ledger treatments, not one `amount` column with a `type` tag
  used only for display.
- Per-capita liability is **per member per period**, so it accrues on admission
  and is owed even for a member whose dues were waived — **see §2b, which is
  exactly where this gets subtle.**
- A per-capita remittance deadline belongs in the same calendar that already
  carries the gaming constraints and the national reporting deadlines.
- Amounts are **configuration per org type and per year**, never constants.
  Layer 1 and 2 are lodge-set; layer 3 is set by a body the lodge does not
  control and changes without asking.
- **THE INITIATION FEE AND ANNUAL DUES ARE CERTIFIED FIGURES ON A LIQUOR-PERMIT
  FILING.** ORC 4303.17(A)(1) requires the officer certification to set forth
  *"the amount of initiation fee and yearly dues"*, and ORC 4301.25(A)(3) makes
  a false material statement in a permit application a revocation ground.
  **Changing either amount must raise a permit-filing flag**, not just update a
  price. See the liquor doc §1.

### 2b. Conditional waivers — governance decisions, and two of them expire

Confirmed conditions, **at Elks specifically**:

1. **Active-duty** members
2. **Recently separated** veterans — **within 24 months**
3. Members who are **sick or in distress**

**Three things this must not become.**

**It is not a discount code.** A waiver is a governance decision under the
lodge's bylaws with an audit trail: who granted it, under which condition, on
what date, and reviewable. Model it as a **record**, not a price modifier.

**Condition 2 EXPIRES, and expiry is computed.** "Within 24 months of
separation" lapses on a date the system derives from the separation date. That
is date arithmetic on a boundary, in a codebase that has already shipped a
UTC-midnight date bug — compute in the post's local date, and re-evaluate
eligibility rather than storing a boolean that silently goes stale. Condition 3
is open-ended and needs a **review date**, not an expiry.

**It is org-type-specific — this is confirmed for Elks only.** The same lesson
as ORC 2915.01 (V)(2) vs (V)(3) and as the officer titles: **do not assume VFW,
Legion, Moose or Eagles share these conditions.** Waiver conditions are a cited
row per org type, like the charitable-purpose categories.

**The interaction with §2a, stated because it is easy to get wrong:** a dues
waiver is a decision the lodge can make about *its own* revenue. **The national
per-capita assessment is not the lodge's to waive** — it is owed upward for
every member regardless. So waiving "dues" must not silently waive the
pass-through, or the lodge quietly funds the difference without seeing it.
**Confirm this against the actual bylaws before building it** — §9b.

**PII note:** the evidence for conditions 1 and 2 is a DD-214 or equivalent
service record. Decide storage, access role and retention before the field
exists — same gate as the winner-SSN requirement in Phase 3.

---

## 3. Phase 2 — Canteen and events (depends on 1.1–1.3, 1.7)

| # | Feature | Notes |
|---|---|---|
| 2.1 | In-house POS: bar + kitchen | **Stripe/Square for payment rails only** — the POS is SAIRN's. This is the pillar Arrow's Tab King already ships; see the competitive doc |
| 2.2 | Nightly shift close-out + cash reconciliation | Feeds §4. VFW's own materials: trustees are **required** to physically inventory canteen liquor regularly |
| 2.3 | Bottle fill-level estimation | **AUTOMATIC determination only.** Binding decision, patent-avoidance. No slider, no tap-to-set, no adjustable guess. See canonical doc *Binding decisions* |
| 2.4 | Lodge events + live-music calendar | Public-facing side of the same calendar the gaming module constrains |
| 2.5 | Hall rental | Weekday/weekend rates, member vs public tier. **THE ALCOHOL TIER IS NOT A DEPOSIT DECISION — see §6a.** Three permit-modelled cases, and the third is a refusal |
| 2.6 | Vendor/supplier management | Gaming supplies, alcohol, food, entertainment bookings |
| 2.7 | AI vendor price search | Defined — **two distinct capabilities**, see **§3a**. (1) compare vendors already on file — grounded, deterministic. (2) search the wider market — **fabrication surface, different rules** |

**Dependency note:** 2.4 must be built as one calendar with the Phase 3 gaming
constraints, not a second calendar bolted alongside. See §4.

### 3a. AI vendor price search — two capabilities with different truth rules

These are **not one feature with a wider radius.** They have different failure
modes and must be built and labelled separately.

**(1) Compare among vendors already on file.** Grounded entirely in the lodge's
own data — the vendors in 2.6 and their recorded prices. Deterministic,
auditable, and there is no fabrication surface: every number came from a record
the lodge entered. This is the one that should ship first and it does not
strictly need a model at all.

**(2) Actively search the wider market** for better pricing on gaming supplies,
alcohol, food and entertainment — **including vendors not yet used.** This is a
genuinely different thing: it leaves the lodge's data and produces numbers no
record backs.

**Rules for (2), non-negotiable:**

- **Every price carries its source URL and the date it was read.** A price with
  no source is a fabricated price — the same standard the platform enforces at
  the API for `rf_cert_rules` and `rf_contingency_rules`, where a rule with no
  citation is refused rather than discouraged.
- **A searched price is never presented as a quote.** It is a lead. The UI
  wording must make a searched figure and a vendor-confirmed figure visually
  distinguishable, because a Finance Officer acting on a stale scraped price and
  budgeting against it is the failure this rule exists to prevent.
- **Prices go stale.** Show the read date next to the number, always, not in a
  tooltip.
- **Alcohol pricing is regulated in Ohio.** Ohio has state-controlled spirits
  pricing; a "better price" for spirits may not be a thing a lodge can act on,
  and beer/wine distribution runs through a franchise system. **§9b** — do not
  ship market search for alcohol until that is checked.
- **Gaming supplies must come from a licensed distributor.** ORC 2915.09(A)(1):
  equipment must be owned or leased from licensed sources, and the AG endorses
  electronic instant bingo distributors. A search result offering cheaper bingo
  supplies from an unlicensed seller is not a saving, it is a licence problem.
  **The search must filter or at minimum warn on this category.**

### 6a. Hall rental has a PERMIT dimension — the third case is a hard block

The D-4 sells *"to its members only."* **The lodge's own permit does not cover
serving a renter's non-member guests.** Ohio's mechanism is a **jointly-issued
F-2** — OAC 4301:1-1-36(B) lets an F-2 applicant request the permit be issued
*"jointly to the applicant and a class D-3, **D-4**, or D-5 liquor permit
holder, who is to conduct the sale."* ORC 4303.202 confirms the design by
exempting D-4 affiliation from the otherwise-disqualifying test.

**But that path is open only to a NOT-FOR-PROFIT renter** organised for a
charitable, cultural, educational, fraternal or political purpose. A wedding, a
birthday, a corporate rental — none qualify.

| Case | Path | Product behaviour |
|---|---|---|
| **Member-hosted, lodge serves** | Covered by the D-4 | Gate that the host is **dues-current**; attendees under the members-only rule |
| **Not-for-profit renter, lodge serves** | **Joint F-2** | Workflow: renter's non-profit qualification, **4 consecutive days max**, **1 per 30 days per renter**, $150 + $10, chief-peace-officer notification, proceeds destination |
| **Private or commercial renter wanting alcohol** | **None found** | **HARD BLOCK + escalate to counsel.** Refuse the booking; do not price it |

**The alcohol-serving deposit tier is gated behind cases 1 and 2.** The failure
mode this prevents is a lodge selling drinks to a wedding party under its D-4
and losing the permit under ORC 4301.25(A) for violating an applicable
restriction of Chapter 4303.

---

## 4. Phase 3 — Gaming compliance and the money model (depends on Phase 1; interlocks with Phase 2)

**This is the regulated core and the actual moat.** Build order inside the phase
matters.

| # | Feature | Notes |
|---|---|---|
| 3.1 | **Bingo account as a first-class entity** | ORC 2915.10(C): **gross profit** — receipts *minus prizes* — into an account **devoted exclusively** to the session; expenses and distributions paid **only** from it |
| 3.2 | Separate **electronic instant bingo** account | Ohio AG requirement, distinct money type, **quarterly reports due Feb 28 / May 31 / Aug 31 / Nov 30** |
| 3.3 | Session model + calendar **constraint enforcement** | Max **3 sessions per 7 days**; **$6,000** prize cap per session; **no sessions 2 a.m.–10 a.m.** (instant sales may begin 9 a.m. for a 10 a.m. session). Session = 5 continuous hours + 2-hour instant windows either side — and per the canonical doc this is a **definition**, not a rule: anything longer is *not a session*, and every per-session calculation keys to nothing |
| 3.4 | Profit chain | receipts − prizes = gross profit; − expenses = net profit. `(GG)(11)` makes canteen cost an allowable expense **paid out of the segregated account** |
| 3.5 | 2915.10(A) record set | By game type; itemised expenses with payee; prize list; participant count; **food and beverage sales AND expenses**; 3-year retention; supply inventory **due Nov 1**; AG notified of where records are kept |
| 3.6 | Operator eligibility | Under-18 barred; felony/gambling conviction barred; **no compensation of any kind** to operators — interacts with paid canteen staff |

**PII gate before 3.5 exists as a table:** 2915.10(A)(3) requires storing winner
**Social Security numbers** for prizes ≥ $600. Encryption, access role and
retention must be decided **before** the column exists, not retrofitted.

---

## 5. Phase 4 — Disbursement, donations and outreach (depends on Phase 3)

| # | Feature | Notes |
|---|---|---|
| 4.1 | Disbursement log, **two independent taxonomies** | `ohio_charitable_purpose` (conditioned on org_type — **(V)(2) veteran's list vs (V)(3) fraternal list are different lists**) and `national_program_category`. Neither derives from the other |
| 4.2 | Instant-bingo tiered distribution engine | 2915.101: ≥25% on the first $250,000, ≥50% above, 5% own-purpose allowance. **Cumulative annual running total**, calendar year, and the threshold is *"or adjusted amount"* — configuration, never a constant |
| 4.3 | Disbursement record fields | `funding_source` (gaming net profit vs general), `game_type`, `disbursement_direction` (given away vs cost-to-post). Per the appendix: the CPR's ~15 "cost to post for X" fields are legitimate nationally and are **not** permitted (V)(2) destinations |
| 4.4 | Donations received + **automatic emailed tax receipts** | Reuse the platform's Resend integration — **`RESEND_FROM_EMAIL`**, not `RESEND_FROM_ADDRESS`, which has never existed here and silently broke two apps |
| 4.5 | Donor-tier recognition | Defined — see **§5a**. **Cumulative lifetime** giving from $100, earning physical items (pins). Fulfilment tracking, and a **tax-receipt interaction flagged in §9a** |
| 4.6 | AI-directed community outreach tied to disbursement categories | Must propose only within the org's *own* legal category set. An outreach suggestion outside (V)(2)/(V)(3) is a compliance hazard dressed as marketing |
| 4.7 | Volunteer / service-hour tracking | Full schema implications in the service-hour appendix. **Decimal hours** (5 min = .08), cumulative person-hours, round-trip miles × occupants, member/non-member split, `counts_toward_national_service` flag, per-org reporting periods as **configuration** — four different fiscal years, none shared |

### 5a. Donor recognition — cumulative lifetime, physical fulfilment, and a tax edge

Pattern: **cumulative giving-level tiers starting at $100**, earning **physical
recognition items (pins)** — the Moose Charities *League of Guardians* shape.

**Cumulative means LIFETIME, not annual.** A running per-donor aggregate that
survives every year boundary, every fiscal-year change in §4.7, and every
reporting period reset. Do not derive it from the current period's ledger; store
and increment it, and be able to rebuild it from the donation records.

**A tier is an award, not a disbursement.** It sits on the *money-received* side.
It must never appear in the §4.1 `ohio_charitable_purpose` taxonomy, which
governs where gaming **net profit goes**. Two different directions of money, and
conflating them would put a donor pin in a charitable-purpose report.

**Physical items need fulfilment state.** Earned / ordered / sent / presented.
A tier crossed and a pin never sent is a promise silently broken, and the person
it was broken to is a donor. This is the same silent-failure class as a write
that shows "Saved" and did not persist.

**The pin costs money**, so it is also a small expense on the other side of the
books — and per the service-hour appendix, "cost to post for X" is a legitimate
national-reporting line but **not** a permitted (V)(2) destination for gaming net
profit. Tag it accordingly.

**THE EDGE THAT NEEDS A REAL ANSWER — §9a:** under IRS quid-pro-quo rules, a
donor who receives goods in exchange for a contribution may deduct only the
excess over the value of those goods, and the receipt must state that value —
unless the item is below the token/low-cost threshold. **4.4 auto-emails tax
receipts.** A receipt that omits the pin's value where it is required is a
defective receipt issued automatically, at scale, in the donor's name. **Do not
ship 4.4 and 4.5 together until this is researched.**

---

## 6. Phase 5 — Member experience and operations (depends on Phase 1; low regulatory risk)

| # | Feature | Notes |
|---|---|---|
| 5.1 | New-member onboarding | "World-class." **See §9 on the animated flag** |
| 5.2 | Volunteer scope-of-work / liability paperwork | Reuse StoneDesk's HR e-sign pattern (`sd_hr_*`, e-sign + durable storage). **§9a.6** — the documents themselves need legal review; the e-sign mechanism does not |
| 5.3 | Ceremonial duties | Honor-guard equipment, shell-casing tracking, shared-team details across posts |
| 5.4 | Vehicle / maintenance tracking | Post-owned vehicles. Distinct from the deferred *building* maintenance item |
| 5.5 | Automated AI monthly newsletter | Grounded in the post's own live data. Depends on Phases 2–4 having data worth reporting |
| 5.6 | Named youth programs | Defined — see **§6a**. Named and **distinct per org type**; explicitly NOT folded into generic community outreach |
| 5.7 | Veteran-services availability across ALL lodge types | Explicitly not veteran-org-only. Elks and Moose posts run veteran services too |

### 6a. Youth programs are NAMED and PER ORG TYPE — not generic outreach

Instruction is explicit: track as **named, distinct programs**, not folded into
generic "community outreach". The three orders do not just run different
programs — they run **structurally different kinds of thing**, and a single
`youth_program` free-text field would erase that.

| Org | Programs | Shape |
|---|---|---|
| **Elks** | **Hoop Shoot** — national free-throw contest, **ages 8–13**; **Soccer Shoot**; **Most Valuable Student** scholarships | Competitions with brackets and age divisions, plus a scholarship |
| **VFW** | Youth **scholarships up to $30,000**; classroom / citizenship programs | Award + curriculum, no competition bracket |
| **Moose** | **Mooseheart** — a residential community for children in need | **Not a competition or a contest at all.** Ongoing welfare, integrated |

**Why the shape difference matters more than the names.** A schema built around
"contest → round → winner" fits Elks and breaks on Moose. A schema built around
"program → contribution" fits Moose and cannot express a Hoop Shoot age
division. Model a **program registry keyed by org type**, with per-program
structure rather than one shared shape — the same conclusion the service-hour
research reached about Moose wanting a quarter-level total and prose where the
Legion wants 126 numbered items.

**Three cross-links, none optional:**

- **Disbursement (§4.1):** scholarships are an enumerated (V)(2) purpose —
  *"awarding scholarships to or for attendance at an institution mentioned in
  division (B)(12) of section 5739.02"* — and youth activities are too:
  *"nonprofit youth activities."* So a scholarship funded from gaming net profit
  is legitimately taggable, and must be tagged.
- **Service-hour reporting (§4.7):** the Legion CPR has a whole **CHILDREN &
  YOUTH (C&Y)** section with its own hour bucket (`#96`) and its own dollar
  fields. Youth program activity feeds that directly.
- **Outreach (§4.6):** the AI may propose within these named programs. It must
  **not invent a program** — a lodge-branded suggestion to run a contest that
  does not exist is the fabricated-capability class.

**MINOR DATA — decide before the table exists.** Hoop Shoot is ages **8–13**.
Any participant record is data about a child: names, ages, schools, possibly
photographs and results published under the lodge's name. Storage, access role,
retention, parental consent and photo release all need a decision **up front** —
the same gate applied to winner SSNs in Phase 3 and DD-214 evidence in §2b, and
for the same reason: retrofitting protection onto a table that already holds the
data protects nobody who is already in it. **§9a.**

---

## 7. Phase 6 — District/state rollup (depends on everything; build last)

Read-only aggregation across independently-governed entities for an overseeing
body. **One of the three defensible moat items** — no verified competitor has it.

- Aggregates **entities**, not locations (§1b).
- **Read-only by construction.** A district officer must not be able to write
  into a post's books; the posts are separate legal entities with separate
  treasuries.
- Cross-tenant read is a genuinely new authorisation shape for this platform —
  every existing app is single-tenant-per-licence. Design it with
  `sairn-software-architect` before writing it.

---

## 8. Deferred — logged, not built

Building maintenance/facilities tracking · officer election, term and bonding
tracking · Phase 2 passive bottle sensor hardware (**needs its own patent pass**;
it was not scanned).

---

## 9. NEEDS RESEARCH OR SOURCE DETAIL BEFORE BUILDING

**Blocking-for-that-feature only; nothing here blocks Phase 1.**

### 9a. Regulated — do not build on assumption

1. ~~**Service Officer VA-claims referral** — blocked pending primary-source
   research.~~ **RESEARCHED AND SCOPED 2026-08-30.** See
   `docs/2026-08-30-sairnfreedom-va-claims-accreditation-boundary.md`.
   **38 U.S.C. § 5901** prohibits acting *"as an agent or attorney in the
   preparation, presentation, or prosecution"* of a claim without recognition —
   narrower than the feature name implied. **§ 5902(a)(1) names the American
   Legion and the VFW in the statute** as organizations whose representatives
   the Secretary may recognize, so a post's Service Officer is typically already
   accredited. **Safe to build (Phase 5):** referral directory, appointment
   scheduling and log, accreditation-status tracking, attributed general
   information. **Out of scope:** anything that prepares, presents or prosecutes
   a claim — including form auto-fill, drafting statements in support, or
   assembling an evidence package. **Two hard product rules** come out of it, in
   §9d below.
2. **Tips received — tax treatment.** Already flagged. Reporting obligations,
   tip credit, allocation between employees and volunteers. **Do not build
   fields until researched.**
3. ~~**Liquor licensing — entirely unexamined.**~~ **RESEARCHED 2026-08-30** —
   `docs/2026-08-30-sairnfreedom-ohio-liquor-permits.md`. Headlines: the D-4
   officer certification must **also set forth the initiation fee and yearly
   dues amounts**, making §2a's fee figures *certified figures on a permit
   filing* and a false one a revocation ground under ORC 4301.25(A)(3); **D-4
   closes at 1:00 a.m., not 2:30** (OAC 4301:1-1-49(B)) and **consumption** is
   barred too, not just sale; **Sunday is closed all day without a D-6, which
   requires a local option election**; renewal is blocked by tax delinquency
   measured at **six months before expiration** while notice arrives at three;
   and **OAC 4301:1-1-53(D)–(E) makes a Chapter 2915 bingo violation a
   simultaneous liquor-permit exposure** — the two modules are coupled. **Hall
   rental changes — see §6a below.** Two questions go to counsel regardless:
   guest service (no primary source either way) and whether officer turnover
   forces a fresh certification. **Still unexamined:** the uniform expiration
   dates themselves (delegated to the Division, `com.ohio.gov` 404s — a per-club
   field, never hardcoded), D-6 local-option mechanics, and whether the
   soldiers'-memorial quota exemption reaches a VFW or Legion post.
4. **OAC 109:1-4-* beyond `-08`**, and the AG's actual licence-renewal forms.
   The renewal report this product feeds may impose its own categories.
5. **ORC 2915.091 / .092 / .093** — instant bingo conduct and location rules,
   unread.
6. **Volunteer liability documents (5.2)** — templates need legal review; this
   is document *drafting*, not schema.

### 9b. Named but not defined — need the source detail

**RESOLVED 2026-08-30 — all five source details received and folded in.**

- ~~Three-layer fee structure~~ → **§2a**
- ~~Conditional waiver rules~~ → **§2b**
- ~~Donor recognition tiers~~ → **§5a**
- ~~Named youth programs~~ → **§6a**
- ~~AI vendor price search scope~~ → **§3a**

Nothing in this sub-section is outstanding. Note that folding them in **created
four new research items** (§9a.7–10) rather than closing the list — detail
surfaces edges that a feature name hides, which is the argument for getting the
detail before building rather than after.

### 9c. ~~A conflict to resolve~~ — RESOLVED 2026-08-30

**The animated-flag / static-branding tension is decided.** Animated banner
app-wide, **static on onboarding**. The earlier rejection was of a bad
implementation (turbulence filters reading as water or TV static), not of the
idea, so what survives is a ban on the *technique*, not the effect. Built
properly as real work and reviewed against `sairn-visual-review` on a rendered
page at real size before it is called done. Full reasoning in **§1d**; also
recorded in the canonical research doc's Binding Decisions.

### 9d. Two hard product rules from the VA research — not optional

**No fee may attach to claims assistance, anywhere in the product.** Every
recognition route in 38 U.S.C. §§ 5902, 5903 and 38 CFR 14.630 requires
certifying that **no compensation of any nature** is charged. A post is a
nonprofit and its officer serves free, so this is satisfied naturally — **but
the Service Officer function must never sit behind a paid tier, subscription
gate or upgrade prompt.** Doing so creates exactly the compensation the
certification denies.

**The AI assistant must DECLINE claim-strategy questions in its system prompt.**
Not a disclaimer, not a warning banner — a refusal. This platform already made
this call once on SAIRNroofing, where the operations assistant was changed to
refuse claim-strategy questions because *"nothing stopped it answering a
negotiation question from general knowledge, and an app-branded answer of that
shape was the real exposure."* Here the stakes are higher: an AI answering
*"what should I claim for?"* is producing claim preparation, under the post's
brand, for an unaccredited asker, at scale.

7. ~~IRS quid-pro-quo receipt valuation~~ · ~~minor-participant data~~ ·
   ~~Ohio alcohol pricing~~ · ~~per-capita waiver treatment~~
   **ALL FOUR RESEARCHED 2026-08-30** —
   `docs/2026-08-30-sairnfreedom-four-research-items.md`. Each changed the
   design. Headlines:

   - **IRS.** The pin is the small problem. **§ 170(c)(3) veterans posts and
     § 170(c)(4) fraternal societies have different deductibility conditions** —
     for a fraternal lodge it applies *"only if such contribution or gift is to
     be used exclusively for religious, charitable, scientific, literary, or
     educational purposes"* and only for gifts **by an individual**. So
     deductibility is a **gate before the receipt renders**, per org type and
     designated use — not a fixed string. **Third legal regime to split on the
     veterans/fraternal axis.** On the pin: § 6115 triggers above **$75**; a
     **lodge-emblem** pin costing ≤ **$13.90** (TY2026) clears the logo route at
     the $100 tier; **without a logo** the fallback is 2% of the payment = $2.00
     and almost any pin fails. **Publication 1771 is three years stale** — it
     prints 2023 figures; load from the annual Revenue Procedure.
   - **Minor data. COPPA does not apply** — collection is defined as gathering
     information *from a child*, and "collected online" is statutory. **It flips
     the moment a child types into the system**: treat that as an architectural
     invariant with an owner. The real exposure is **ORC 2741.01(B)(4), which
     makes *fundraising* a "commercial purpose"** — the same photo is lawful in a
     results story and prohibited in a donation appeal, and **the standard Elks
     release is scoped to Hoop Shoot promotion only.** Build **scoped consent as
     an enum, never a boolean.**
   - **Ohio alcohol. The vendor-search feature does not survive for alcohol.**
     Spirits are a state monopoly at a uniform price; **OAC 4301:1-1-43(J)(2)
     prohibits the RETAILER from buying outside its distributor's territory** —
     hidden in a rule titled about signs — and discounts and rebates are banned
     both directions. The exposure is a **first-degree misdemeanor and the
     lodge's permit**, not ours. Replacement is better: cost-per-serving,
     pour-cost, menu pricing against the markup floors, and **auditing that the
     lodge is actually charged the posted price.**
   - **Per-capita. Half confirmed, half REFUTED.** It does accrue per member on
     the roster regardless of dues status — but **"the lodge absorbs it" is one
     of four patterns.** Elks: the **member pays it personally** (per capita is
     defined *outside* "dues"). VFW: a **ring-fenced Post Relief Fund** pays it
     under Sec. 219(g), and an **actuarial endowment** covers life members.
     Legion: the post absorbs it. So **`payer` is a separate dimension** —
     `member` | `restricted_fund` | `endowment` | `lodge_general`. **Moose books
     it as "Acct 2515 as liability"** in its own chart of accounts, which
     independently confirms §2a's pass-through design.

   **Two spec corrections from the alcohol pass:** **D-4** is the club permit
   (ORC 4303.17(A)(1), and (B) expressly preserves service in a bingo room);
   **D-4a is an AIRLINE permit** (ORC 4303.171) — never label a lodge permit
   that. And **ORC 4303.17(A)(1) conditions D-4 issuance AND retention on
   officers certifying a dues-paying membership with the roster on request**, so
   the membership module already touches a liquor-permit retention condition —
   feeding §9a.3.

   **Still open, and deliberately so:** whether a premium earned by crossing a
   *cumulative lifetime* threshold attaches to the crossing payment (no
   authority exists — tax professional); the Elks Youth Protection Guidelines
   (not public); whether a *conferred* Moose life member generates per capita;
   and **Eagles entirely** — the Grand Aerie Constitution is sold as a physical
   product, so Eagles must be treated as unresearched. Three questions for a real
   lodge officer are in the research doc.

### 9b. Named but not defined — need the source detail

**RESOLVED 2026-08-30 — all five source details received and folded in.**

- ~~Three-layer fee structure~~ → **§2a**
- ~~Conditional waiver rules~~ → **§2b**
- ~~Donor recognition tiers~~ → **§5a**
- ~~Named youth programs~~ → **§6a**
- ~~AI vendor price search scope~~ → **§3a**

Nothing in this sub-section is outstanding. Note that folding them in **created
four new research items** (§9a.7–10) rather than closing the list — detail
surfaces edges that a feature name hides, which is the argument for getting the
detail before building rather than after.

### 9c. ~~A conflict to resolve~~ — RESOLVED 2026-08-30

**The animated-flag / static-branding tension is decided.** Animated banner
app-wide, **static on onboarding**. The earlier rejection was of a bad
implementation (turbulence filters reading as water or TV static), not of the
idea, so what survives is a ban on the *technique*, not the effect. Built
properly as real work and reviewed against `sairn-visual-review` on a rendered
page at real size before it is called done. Full reasoning in **§1d**; also
recorded in the canonical research doc's Binding Decisions.

### 9d. Two hard product rules from the VA research — not optional

**No fee may attach to claims assistance, anywhere in the product.** Every
recognition route in 38 U.S.C. §§ 5902, 5903 and 38 CFR 14.630 requires
certifying that **no compensation of any nature** is charged. A post is a
nonprofit and its officer serves free, so this is satisfied naturally — **but
the Service Officer function must never sit behind a paid tier, subscription
gate or upgrade prompt.** Doing so creates exactly the compensation the
certification denies.

**The AI assistant must DECLINE claim-strategy questions in its system prompt.**
Not a disclaimer, not a warning banner — a refusal. This platform already made
this call once on SAIRNroofing, where the operations assistant was changed to
refuse claim-strategy questions because *"nothing stopped it answering a
negotiation question from general knowledge, and an app-branded answer of that
shape was the real exposure."* Here the stakes are higher: an AI answering
*"what should I claim for?"* is producing claim preparation, under the post's
brand, for an unaccredited asker, at scale.

7. **IRS quid-pro-quo / donor-tier receipt valuation.** §5a. Auto-emailed tax
   receipts (4.4) plus physical recognition items (4.5) meet at a real IRS rule:
   goods given in exchange for a contribution reduce the deductible amount and
   the receipt must state their value, unless below the token threshold. **Do
   not ship 4.4 and 4.5 together until this is answered.** An automatically
   issued defective receipt is worse than no receipt.
8. **Minor-participant data for youth programs.** §6a. Ages 8–13. Consent,
   photo release, retention, access role — before any participant table exists.
9. **Ohio alcohol pricing and distribution.** §3a. State-controlled spirits
   pricing and beer/wine franchise distribution may make "shop for a better
   price" inapplicable or unlawful for some categories. Check before shipping
   market search for alcohol. Sits alongside the wholly-unexamined liquor
   licensing item (§9a.3).
10. **Whether a dues waiver can waive the national per-capita.** §2b. Almost
    certainly not — it is owed upward per member regardless — but it is a bylaw
    question, it differs by order, and getting it wrong means the lodge quietly
    funds the difference without seeing it. **Confirm against actual bylaws.**


---

## 10. Dependency summary

    Phase 1 (entity, roles, members, fees, branding)
      ├── Phase 2 (POS, canteen, events, hall, vendors)
      │     └── shares ONE calendar with ─┐
      ├── Phase 3 (gaming: accounts, sessions, records) ◄┘
      │     └── Phase 4 (disbursement, donations, outreach, service hours)
      ├── Phase 5 (member experience, ceremonial, vehicles, newsletter)
      │     └── 5.5 newsletter needs Phases 2-4 producing real data
      └── Phase 6 (district rollup) — needs all of the above

**The one interlock worth stating twice:** Phase 2's events calendar and Phase 3's
session constraints are **one calendar**. Building them separately produces a
booking surface that cheerfully schedules a fourth bingo session in a seven-day
window, and a compliance surface that reports the violation afterwards. The
calendar must **refuse**, in the fail-closed posture the roofing rescission
engine already uses.

---

## 11. What this spec does not settle

- **Trade/market build order beyond the phases.** Phase order is dependency
  order, not commercial priority.
- **Whether Tab King already does the membership half properly.** Still the
  single most important open competitive question; Arrow publishes no pricing
  and no feature matrix. **Request a demo before locking strategy.**
- **Pricing, licensing tier, or contract shape.** `sairn-contract-drafter` owns
  that when the time comes.
- **Anything in §9.** Those are named gaps, not assumptions to be quietly filled
  by whoever builds first.
