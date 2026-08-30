# SAIRNsenior — round 24: Hawaii's rules are JS-gated, and every state now has a status

2026-08-30. **Research only.** Thirty-sixth document in the series.

Two results: **Hawaii's administrative rules are a third instance of the fifth
blocking shape** — statute read, rules unreachable — and, with Hawaii's statute
done, **there are no untouched states left.** All fifty have either been read on
at least one axis or carry a recorded, diagnosed route status.

**"No untouched states" is not "coverage", and the distinction is the point of
this document.**

---

## 1. Hawaii's rules — the statute is enabling, and the rules are behind JavaScript

HRS § 321-14.8 (round 23) says the Department of Health *"shall adopt rules …
to provide for the licensure of home care agencies."* **The operative training,
screening and supervision content is therefore in the rules, not the statute** —
which is why round 23 flagged them as the priority.

**They were not reached. Five routes tried, all diagnosed:**

| Route | Result |
|---|---|
| `health.hawaii.gov/opppd/rules/` | **404** — but the 404 page is branded *Office of Planning Policy and Program Development*, confirming the office |
| `health.hawaii.gov/ohca/home-care-agencies/` | **404** — branded *Office of Health Care Assurance*, which **confirms OHCA is the licensing office** |
| `health.hawaii.gov/ohca/` | **200** — and its "Rules & Regulations" link points to `/opppd/administrative-rules/` |
| `health.hawaii.gov/opppd/administrative-rules/` | **200, 103 links, exactly one PDF** (an unrelated practice-and-procedure document). The page loads **`jquery-vertical-accordion-menu`** — **the chapter list is rendered client-side.** |
| `health.hawaii.gov/opppd/wp-json/wp/v2/pages/59` | **212 bytes** — the WordPress REST endpoint is exposed in the page's own `<link>` tags but returns nothing usable |
| `lrb.hawaii.gov/admin-rules-directory/` | **200, 2,280 characters** of navigation only |
| `health.hawaii.gov/opppd/files/2021/06/11-800.pdf` (guessed) | **404** |

> **Third instance of "index server-side, content client-side"**, after Alaska and
> South Dakota — and the first where it is a **jQuery accordion on a WordPress
> site** rather than a Vue SPA. **The shape is not about the framework.** The
> tell is the same each time: a real, useful index arrives, and the level beneath
> it does not.
>
> **What was gained anyway, and it is not nothing:** the responsible office is
> confirmed as **OHCA (Office of Health Care Assurance)**, and the rules index is
> confirmed to live under **OPPPD's administrative-rules page**. A future pass
> starts from a known office and a known page rather than from the statute.

**Hawaii's position in the model is therefore: axis-by-axis unknown, licensure
confirmed.** § 321-14.8 establishes *that* every home care agency is licensed,
the individual-provider carve-out, the payer-based exemptions and the ch. 457
scope boundary — but **no training hours, no screening standard and no
supervision cadence are established for Hawaii**, and none should be inferred.

---

## 2. Every state now has a status

With Hawaii's statute read, **the fifty-state sweep has no untouched entries.**
Recorded precisely, because the categories mean different things:

**Read on at least one axis — 42 states.**
AZ · AR · CA · CO · CT · DE · FL · GA · HI · IA · IL · KY · LA · MA · MD · ME ·
MI · MN · MO · MT · NC · ND · NE · NH · NJ · NM · NV · NY · OH · OK · OR · PA ·
RI · SC · TN · TX · VA · VT · WA · WI · WV · WY

*Some of those are thin by design and are labelled so in their own rounds:*
**Connecticut** is overtime-only (its licensure regs are unreachable);
**New Hampshire** and **Montana** are "chapter repealed, successor identified";
**New Mexico** is "route open, chapter [RESERVED] and empty"; **Hawaii** is
"statute read, rules gated".

**Diagnosed route failures — 8 states.**

| State | Shape |
|---|---|
| **Alabama**, **Mississippi** | state routes its own code to **LexisNexis**, JS-gated |
| **Utah**, **Kansas** | publisher SPA / index is site chrome only |
| **Connecticut** | soft-200 error body on the regs portal (`"Unable to Acccess Resource"`) |
| **Alaska**, **South Dakota** | **index server-side, content client-side** |
| **Idaho** | **state-declared outage** — its own banner says search and listings are broken |

**On hold — 1.** **Indiana**: not blocked; `api.iga.in.gov` returns
`"x-api-key not found"` and points at its docs. **A credential decision, not an
obstacle.**

### The honest caveat, stated plainly

**No state has been read exhaustively.** Every round document carries its own
Tier 2 list. What "read on at least one axis" means in practice ranges from
**Colorado** (licensure chapter, both service categories, placement agencies,
background and registry rules) to **Connecticut** (one overtime definition).
**Anyone using this survey must read the per-state document, not the count.**

---

## 3. Tier 2

| Item | Status |
|---|---|
| Hawaii Administrative Rules (OHCA/OPPPD) | **JS-GATED** — office and index page identified; content not reached. |
| HI §§ 321-13.5, 321-1.9; HRS ch. 457 boundary | **NOT READ** |
| The eight diagnosed states | **ROUTE STATUS RECORDED, CONTENT NOT READ** |
| Indiana | **ON HOLD** — API key |
| Every state's unread sections | **See each round's own Tier 2** |

## 4. Method notes

- **A branded 404 is evidence.** Hawaii's two dead URLs returned 404 pages
  carrying the names of the offices that own them, which is how OHCA was
  confirmed as the licensing office and OPPPD as the rules publisher. **The error
  page identified the right agency even though the path was wrong.**
- **The fifth blocking shape is framework-agnostic.** Vue (South Dakota),
  server-rendered-list-plus-JS-drilldown (Alaska) and a jQuery accordion on
  WordPress (Hawaii) are the same problem. Naming it in round 23 made this one
  identifiable in a single pass.
- **"No untouched states" is a milestone about *process*, not about knowledge.**
  It means every state has been looked at and given a status. It does not mean
  the map is complete, and the paragraph above says so in the same breath.
