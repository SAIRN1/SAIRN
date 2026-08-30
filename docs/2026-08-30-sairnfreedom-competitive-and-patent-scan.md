# SAIRNfreedom — competitive and patent/prior-art scan

> **CANONICAL DOCUMENT IS ELSEWHERE.** This file is an APPENDIX. The
> decisions, the merged statutory findings and the reconciliation record live in
> **`docs/superpowers/specs/2026-08-30-sairnfreedom-research.md`** — read that
> first. This file is kept as source-of-record for the competitive and patent
> scan's full citations and per-product detail.
>
> One thing here is SUPERSEDED: the section below says the bottle-photo feature
> "must not be built as originally scoped without a real freedom-to-operate
> opinion." **A decision has since been made** — build automatic determination
> from the start, no user-positioned indicator anywhere. See *Binding decisions*
> in the canonical document. The FTO caution is retained there as the reasoning
> behind that decision and as a gate before the feature reaches sales material,
> **not** as a still-open question about whether to build it.


**Run 2026-08-30.** Gate 2 of the SAIRNfreedom build, per the standing
platform rule that a competitive and prior-art scan happens before code.

**Not legal advice.** The patent section is a keyword screen, not a
freedom-to-operate clearance.

---

## THE REVISED MOAT — read this before anything else

The build was framed on a four-pillar combination: membership + regulated bar +
regulated gaming + legally-required fund segregation, with the premise that no
competitor combines them. **That premise is partially wrong, and the
differentiation story has to change.**

**Arrow International, headquartered in Cleveland, Ohio, already markets three
of the four pillars in one shipping product.** Verbatim from their own page:

> "Arrow's Tab King® is an industry-leading point-of-sale solution for clubs,
> social quarters, and charities. Designed to simplify operations and boost
> efficiency, Tab King puts every part of your business at your fingertips
> **from food and beverage to gaming, membership, time tracking, and
> reporting**."
> — equipment.arrowinternational.com/electronic-pull-tabs, address on the same
> page: 9900 Clinton Road, Cleveland, OH 44144

They have 55 years in charitable gaming, acquired Tab Wizard in December 2021
(consolidating the pull-tab + F&B POS category), and Tab King USA partnered with
the **Northeast Moose Association** in 2019 to build a fraternal lodge
management system including membership-card swipe for good standing. None of
this was in the prior research.

### What the moat actually is, restated

**NOT** "we combine four things." Three of those four are already combined and
selling, by a vendor in the target state with the distribution channel this
product needs anyway.

**The defensible ground is the three things no verified competitor touches:**

1. **Ohio Rev. Code Ch. 2915 charitable-purpose disbursement tagging** — no
   vendor found makes any claim about it, and it is the hardest of the three to
   copy because it requires reading the statute correctly. See
   `2026-08-30-sairnfreedom-orc-2915-verification.md`, which found the category
   list is per organization type, not one shared list — a subtlety a competitor
   bolting on a feature would very likely get wrong.
2. **District/state read-only rollup across independently-governed posts.** Only
   ClubExpress has anything adjacent, and its multi-tier chapters model is a
   general org-hierarchy feature, not a cross-tenant regulatory rollup.
3. **Hall rental.** Only ALPost has it, in an American-Legion-specific website
   builder with no accounting, no POS and no gaming.

**Fund segregation alone is a thin moat and should not be relied on.** No vendor
claims it today, but it is not a hard engineering problem — it is a
chart-of-accounts decision plus a reporting template. If Arrow decides Ohio
segregation is worth two sprints, that clause closes and the four-pillar framing
is fully refuted.

### The bottle-photo feature needs a real clearance opinion, not this scan

Two separate problems, and neither is fatal on its own:

- **It was mischaracterized.** Partender is **not** automated photo estimation.
  Verbatim: *"Just tap where the liquor level is on the bottle and swipe to the
  next bottle."* It is manual tap-on-a-displayed-image.
- **It carries the only identified patent exposure in the stack**, and the
  family is live to 2033/2034 with a **pending continuation whose claims can
  still be amended** (details below).

**This feature must not be built as originally scoped without a real
freedom-to-operate opinion from counsel.** A keyword screen is what was run
here, and it is not sufficient to clear a feature that goes into a shipping
product or into sales material. It is also the *weakest* differentiator in the
stack — it guards none of the three defensible items above — so it should not
drive architecture, and the FTO cost should be weighed against a feature that
is nice-to-demo rather than load-bearing.

---

## Verdict on the stated hypothesis

Hypothesis tested: *"No existing competitor combines membership + regulated bar
+ regulated gaming + legally-required fund segregation."*

**PARTIALLY REFUTED.** It survives only on the fourth clause. Three-of-four is
shipping today from a Cleveland vendor.

---

## Products found

Pillars: **M**embership · **B**ar/canteen POS · **G**aming compliance ·
**F**und segregation

| Product | URL | Verified: what it does | Verified: what it does NOT do | Pillars |
|---|---|---|---|---|
| **Arrow Tab King®** | equipment.arrowinternational.com/electronic-pull-tabs · tabkingusa.com | Vendor claims POS covering "food and beverage to gaming, membership, time tracking, and reporting" for "clubs, social quarters, and charities." Verticals: bars/restaurants, fraternal/veterans orgs, pull-tab shops, bingo halls, lottery. "Intelligent Ticket™" fraud validation. QuickBooks integration (per NEMA release) | POS product page lists sales, payments, inventory, staff, time clock, payroll, ID scan — **no membership, no gaming, no fund segregation named there**. No mention anywhere of fund segregation, separate gaming vs bar ledgers, or charitable-disbursement tracking. No Ohio 2915 language | **M B G** |
| **Tab Wizard** | tabwizard.com | Seattle, est. 1992; pull-tab POS + F&B POS. Acquired by Arrow Dec 2021 | Membership, fund segregation not verified | **B G** |
| **TidyHQ** | tidyhq.com/features | CRM/Contacts, Memberships, Events, Finances, Communications, Tasks & Governance, Meetings, Shop, Web Pages, Document Storage, TidyConnect, TidyAI. Automated renewals, member portal, tier management; Stripe/Xero; Shop = member-only products, basic inventory | **Confirmed absent from the features page:** POS, bar, canteen, liquor inventory, gaming, bingo, charitable gaming, fund accounting, fund segregation, restricted funds. TidyAI is *"AI consulting and workshops for sporting organisations"* — a services offering, **not** an AI assistant over org data | **M** |
| **Member Muster** | membermuster.com — **DEAD** | Domain parked (ParkLogic, offered for registration/renewal). `membermuster.us` returns DNS NXDOMAIN. Last Wayback capture 2025-04-05 | Cannot verify any feature claim. **Treat as possibly defunct** | — |
| **EO Software / M.A.P.S. Online** | thepostsoftware.com | **Licensed VFW National vendor**, VFW-specific since 1991. Verbatim: "Ledger, Check Writer, Check Register, Bank Reconciliation, Post Trustees' Quarterly Report, Monthly Report, Transaction Summary Report for 990, Membership Rosters, Labels & Reports, Membership Dues Posting." Notably: **"Even Bingo funds are accounted for with transaction codes"** | No canteen/bar POS, no liquor inventory, no bingo *operations*. Bingo as transaction codes in one ledger — **tracking, not segregation**. No published pricing | **M** + weak **F** |
| **ClubExpress** | clubexpress.com/features | Membership DB, member types/renewals, committees, non-member DB, volunteering. "powerfully supports multi-tier clubs (with chapters, districts and regions)" with chapter-scoped visibility. POS via **Addmi partnership** "to use at your facilities (for example, a restaurant or bar)" with member-status verification | **Decisive, from their Money tab: "ClubExpress is not a full accounting system for your club or association."** QuickBooks export +$20/mo. Core POS is merch/signups/donations at events. No bingo, no gaming, no fund segregation, no hall-rental module found | **M** + partial **B** (partner) |
| **ALPost** | alpost.org | American Legion-specific website builder + Membership Management, Easy Member Application, **Hall Rentals**, events, donations (coming soon) | No bar POS, no gaming, no accounting or fund segregation, no district rollup | **M** (+ hall rental) |
| **Buz Club Software** | buzsoftware.com | Private-club platform: member management + billing, "integrated accounting tools" incl. general ledger, inventory, AR, AP, banking; "streamlined food and beverage POS" with tablet service | **No** bingo/gaming/charitable gaming. **No** fund segregation. Targets golf/yacht/city/racquet/social/equestrian — **no** fraternal or veterans mention | **M B** |
| **Partender** | partender.com | "Bar Inventory, Online Ordering, Accounting in 15 min." Method verbatim: **"Just tap where the liquor level is on the bottle and swipe to the next bottle."** Claims consumption accuracy "up to 99.2%". XLS purchase orders | **NOT automated photo estimation** — manual tap-on-image. No membership, no clubs/veterans posts, no gaming, no fund accounting | **B** (inventory only) |
| **WISK.ai** | wisk.ai | AI bar inventory; photo-based counting cited at 5–10 sec/bottle; pricing $199–$799/mo per a third-party review site, not WISK's own page | No membership, gaming, or fund accounting | **B** |
| **MoneyMinder** | moneyminder.com | Club bookkeeping: budget, categorize, bank integration, Square/PayPal/Venmo/Stripe, reconcile, "Collect and disburse club funds." Names American Legion among customers | Does **not** name fund accounting/separate funds, bar POS, bingo/gaming, or membership dues. VFW, Elks, Moose, Eagles not mentioned | weak **F** |
| **Everi / Video King** | everi.com/bingo | Bingo hall management integrated with bingo equipment, "installed in thousands of charitable bingo halls" | No membership, no bar POS, no fund segregation verified | **G** |
| **Arrow Echo / Prestige** | equipment.arrowinternational.com | "Echo" = "fully integrated point-of-sale and bingo hall management station… exclusively with the E-max gaming system"; "Prestige" = POS + bingo hall management across bingo systems | No membership, no fund segregation, no F&B detail published | **G** (+ POS) |
| **Cannabis Club Systems** | globenewswire release 2025-11-09 | 900+ clubs; member admin, inventory, sales, compliance reporting; "SmartBud AI" personalized product recommendations | Not fraternal/gaming. **"GUST" was not found** — see UNVERIFIED | — |
| **LodgeMaster** | lodgemaster.io | Masonic lodge governance: Ritual & Floor Work, Polls & Voting, Documents, Tasks, News Hub, Activity Log, Catering, Reports, CSV import/export | No POS, no gaming, no fund segregation found | **M** |

### Partial-combination flags — the useful signal

- **Membership + bar + gaming:** Arrow Tab King. The only one. **This is the
  real competitor.**
- **Membership + bar:** Buz Club Software; ClubExpress (via Addmi partner).
- **Bar + gaming:** Tab Wizard (now Arrow); Arrow Echo/Prestige.
- **Membership + gaming-fund tracking:** M.A.P.S. Online — bingo funds as
  *transaction codes* in one ledger. The closest thing to segregation found,
  and it is not segregation.
- **Membership + hall rental:** ALPost.
- **Multi-tier district rollup:** ClubExpress only, and it is a general chapters
  model, not a read-only cross-post regulatory rollup.

---

## A compliance fact this scan surfaced that the statute read did not reach

The Ohio Attorney General states that organizations must maintain **"a separate
checking account for their electronic instant bingo proceeds"**, must file
**quarterly reports due February 28 / May 31 / August 31 / November 30**, and
that **"Manufacturers and distributors of electronic instant bingo systems must
obtain an endorsement from the attorney general's office."**
— charitable.ohioago.gov/Charitable-Bingo/Electronic-Instant-Bingo

This is a **third** segregation requirement, on a different money type, with
deadlines nothing in Chapter 2915 itself supplies. It confirms that the
AG/Ohio-Administrative-Code layer flagged as unread in the statute verification
is load-bearing, not a formality.

The endorsement requirement also bears on strategy: it is a regulatory moat
around *hardware/system distribution* that Arrow already sits inside and this
product does not — which is another reason the differentiation should rest on
the compliance and reporting layer rather than on anything touching gaming
system distribution.

---

## Patent scan

### (i) Image-based bottle fill-level — substantial, live prior art

| Patent | Title | Assignee | Dates | Status |
|---|---|---|---|---|
| **US9576267B2** | System and method for taking an inventory of containers for liquid | **Partender LLC** (inv. Nikhil Kundra) | priority 2012-11-26; granted 2017-02-21; anticipated expiry **2033-11-12** | **Active** |
| US10127520B2 | continuation | Partender family | 2018 | in family |
| US10915858B2 | continuation | Partender family | 2019 | in family |
| **US11961032B2** | System and method for taking an inventory of containers for beverages | Nikhil Kundra | priority 2012-11-26; granted **2024-04-16**; anticipated expiry 2034-01-21 | **Active** |
| **US20240320601A1** (app. 18/586,707) | same family | Nikhil Kundra | filed 2024-02-26; pub. 2024-09-26 | **PENDING** — claims 1–21 cancelled, claim 22 first independent |
| US20190197466A1 | Inventory control for liquid containers | E-Commerce Exchange Solutions | priority 2017-12-27 | **Abandoned** |
| EP3992847A1 | A bottle analysis system | Koninklijke Philips NV | filed 2020-10-27 | **Withdrawn** (2022-11-05) |
| US20070228068A1 | Alcoholic beverage management and inventory system | — | 2007 | weighing-based, not image |
| US20110166699A1 / US8453878B2 | Liquid level measuring device | — | 2010–2013 | RFID/barcode |

**The load-bearing detail.** Every *granted* claim in the live Partender family
requires **manual user interaction with a displayed image**. US9576267B2 claim 1
requires *"sliding the sliding member along the actual digital image… to a
position along the open container corresponding to an amount of liquid
remaining."* US11961032B2 claim 1 requires *"contacting the digital image at a
position."* Pending US20240320601A1 claim 22 likewise requires *"contacting the
graphical user interface at a position."*

**The risk.** Partender's **specification** discloses automatic estimation:
*"the computer can also identify and calculate the liquid level in each bottle
simply via photographing, video recording, or panning over the bottle(s) being
measured."* That disclosure sits in a family with a pending continuation whose
claims can still be amended. The two patents that squarely claimed automated CNN
liquid-level detection are abandoned and withdrawn respectively — favourable for
a genuinely automated approach, **but this is not clearance.**

### (ii) Charitable-gaming fund-segregation accounting — none found

Searches returned casino/Class II–III enterprise gaming accounting, not
charitable fund segregation: US8382584B2, US8366542B2 (networked gaming
enterprise accounting), US20110183747A1 (machine accounting + cashier station),
US5687971A / WO1997002876A1 (bingo game management, paper-sales reconciliation),
US7794319B2, US9536392B1 (bingo game system), US8135644B2 (gaming monetary
transactions, includes a charity-account crediting mechanism).

**No patent found claiming statutory fund segregation between a
charitable-gaming ledger and a bar/canteen ledger.** Caveat: Google Patents'
search UI is JS-driven and did not render, so this was keyword search via web
results into patent pages. **A screen, not an exhaustive search.**

---

## UNVERIFIED / COULD NOT CHECK

- **Member Muster** — not one feature claim verifiable. `.us` NXDOMAIN, `.com`
  parked, `web.archive.org` blocked to the fetch tool. The prior research's
  claims (Legion-specific, membership/dues only) are plausible but unconfirmed,
  and the product may be defunct.
- **TidyHQ's "300+ service clubs in 32 countries"** — not found on the features
  page; a customers/about page was not checked.
- **GUST (Spain, cannabis-club software)** — **no product by that name found.**
  Either the name in the prior research is wrong or it is not US-indexed. The
  "AI grounded in own operational data" validation is therefore only weakly
  supported: Cannabis Club Systems' SmartBud AI is verified as *product
  recommendation*, not marketing generation.
- **Spill-O-Not** — not searched, deprioritised.
- **Tab King feature depth — the single most important unresolved question.**
  The "membership" claim rests on Arrow marketing copy and one 2019 press
  release. Whether Tab King does real *dues billing and fraternal governance* or
  only *card-swipe good-standing + rewards* could not be determined. No pricing,
  no public feature matrix, help-centre pages were navigation stubs.
  **Request a demo before locking any strategic conclusion.**
- **ClubExpress POS/Addmi detail** — clubexpress.com and help.clubexpress.com
  return HTTP 403 to fetch tools; the features page was read via browser. The
  Addmi description comes from a search-result snippet, not a rendered page.
- **Everi/Video King, Arrow Echo/Prestige** — from Arrow's index page and search
  snippets; dedicated product pages not fetched.
- **Ohio-endorsed e-bingo vendor list** — the AG page names no specific approved
  distributors; no published registry located.
- **Whether any competitor sells into Ohio posts today** — not established. No
  vendor page read mentions Ohio except Arrow's Cleveland address.

---

## Scan-depth disclosure

The competitor half is solid: primary sources verified for eleven products. The
patent half is a keyword screen, not a proper search. And the competitor that
matters most — Tab King — is the one whose depth is least verifiable, because
they publish neither pricing nor a feature matrix. That gap should be closed by
requesting a demo before any strategic conclusion is locked in.
