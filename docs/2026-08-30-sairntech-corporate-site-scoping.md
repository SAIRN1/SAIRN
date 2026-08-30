# sairntech.com — initial scoping pass

**Written 2026-08-30 (CC). Scoping only. Nothing built, no design, no schema.**

Scope confirmed 2026-08-30: one catalog site combining ready-made SAIRN apps, a
new per-industry ebooks line, and a custom app/website-building service with its
own structured inquiry flow. Domain `sairntech.com`, registered, not yet built.

This pass identifies **the decisions that have to be made before design starts**,
the shapes the site actually has, and the risks that are specific to *this*
company rather than to websites in general.

---

## 1. The central finding: this is not one catalog, it is three funnels

Treating these as three categories in one shop is the obvious move and the wrong
one. They differ on every axis that matters to the build.

| | **Ready-made apps** | **Ebooks** | **Custom work** |
|---|---|---|---|
| What is sold | A licence to running software | A file | Time and judgment |
| Price known upfront | Yes | Yes | **No — that is the point** |
| Transaction | Purchase or subscribe | One-time purchase | **None. It is an inquiry** |
| Fulfilment | Issue a licence key, provision | Deliver a download | A human replies |
| After-sale | Ongoing: support, updates, renewals | None | An engagement |
| Failure if wrong | Customer cannot log in | Customer cannot download | **Nobody replies to a real lead** |
| Needs an account | Probably | Probably not | No |

**Consequence:** the custom-work section must **not** be a product card with a
"Contact us" button bolted on. It is a different flow with a different success
condition — a completed, structured, *answerable* inquiry — and it should be
designed as its own thing from the start. The other two can plausibly share a
commerce path; this one cannot join them.

---

## 2. What already exists — reuse, do not rebuild

Verified in the repo, not assumed:

- **`sairntech.com` is the owned domain** — NameCheap, expires **2028-06-09**.
  Confirmed during the SAIRNcare email incident, which also established that
  `sairn.com` is registered to a **third party** (Atom.com marketplace listing)
  and could never have been verified. Any material still saying `sairn.com` is
  wrong.
- **Email is already working and proven.**
  `alerts@notifications.sairntech.com` is a verified Resend sending domain, with
  provider-issued send ids in the production log as evidence. **The quote-request
  flow and the ebook delivery both need transactional email; the path exists.**
  Use `RESEND_FROM_EMAIL` — `RESEND_FROM_ADDRESS` is the name that never existed
  and silently broke two apps.
- **Licence issuance is a solved problem.** `api/_lib/license.js` already does
  `validateLicenseKey` and `hashLicense` (sha256 of the key), and thirteen apps
  gate on it. App purchase → licence key is an **integration**, not a new
  subsystem. Do not invent a second key format.
- **Stripe is connected** at the platform level.
- **Vercel + Supabase** is the deployment and data path for everything else here.

**What does not exist:** any catalog page, any ebook, any quote-request flow, any
pricing page. This is genuinely from zero on the site itself.

---

## 3. FLAGGED: the skill pack is a fourth product line, and it is the closest to shippable

`dist/skills-public/sairn-skills/` already exists in the repo — a Claude Code
plugin marketplace README under **SAIRN Technologies LLC**, pointing at
`sairntech.com`, with one skill published (`postgres-grant-sweep`) and an install
path (`/plugin marketplace add sairn-tech/sairn-skills`).

**As of tonight there are nine SAIRN-original skills**, six of them written and
vetted today, with an explicit shipping gate (`sairn-skill-vetter` Gate 3) that
has already been run against them: claims traceable to real incidents, versioned
standards dated, honest-scope sections, precedence declared, licence keys
redacted, `allowed-tools` set.

**Why this belongs in the scoping decision rather than as a later addition:**

- It is **the only offering with a finished artifact today.** The apps need a
  sellability gate (§4), the ebooks do not exist, custom work needs a flow.
- It has a **completely different distribution channel** — a plugin marketplace,
  not a purchase. If the site links to it, that is a fourth transaction shape
  (or a fifth: free-with-attribution) and the information architecture should
  know about it now rather than gaining a mismatched fourth tab later.
- It is **credibility content**. A prospect evaluating a custom-build service
  reads a public engineering artifact very differently from a marketing page.
  The skills are the strongest available evidence of how this shop works.

**Decision needed:** is the skill pack (a) a product on the catalog, (b) a free
credibility asset linked from an About/Engineering page, or (c) out of scope for
v1? Recommendation: **(b) for v1** — it costs almost nothing, it is already
public, and it strengthens the custom-work pitch, which is the offering with the
weakest cold-start story.

---

## 4. GATE BEFORE ANY APP APPEARS ON THE CATALOG

**A catalog is a page of external claims, and this platform has a standing rule
about those.** `sairn-decision-gate` triggers before *"claiming production /
complete / live to anyone outside the team."* A catalog listing an app is
exactly that claim, repeated once per card.

Not every app is sellable today, and the differences are known:

- **SAIRNfreedom** — researched tonight, **nothing built**. No schema, no app
  file.
- **SAIRNmechanical** — the file has **never been on `main`**; it lives only on
  an unmerged branch, `sairn.vercel.app/sairnmechanical` returns **404**, and
  recovery is a separate authorised task requiring a real review pass.
- Several live apps carry **known open items** — unaudited panels, deferred
  minimum-necessary tiering, an unexamined liquor-licensing surface.

**Required before design:** a per-app **sellability verdict** — sellable now /
sellable with disclosure / not listed — decided under `sairn-decision-gate`, with
the claim wording for each fixed at the same time. **SAIRNlaw already has a
precedent for exactly this**: an approved external-claim document that has been
rewritten at five consecutive gates because the specific half kept going stale.
Every catalog card is that problem in miniature.

**And SAIRNlaw specifically cannot be listed yet.** Its own claim document now
carries a **pre-launch blocker** — `law_deadline_rules` and `law_holidays` have
no authenticated write path — with an explicit note that "internal licences
only" is the sole reason it is deferred, and that the first real prospect makes
it false. A catalog listing *is* the first real prospect.

---

## 5. The ebooks line — the offering with the most upside and the sharpest risk

The premise is good and genuinely differentiated: **AI-assisted writing grounded
in real research already done for each app**, plus Michael's own industry
experience, held to the same verify-before-writing discipline as the platform —
explicitly not generic AI filler.

Tonight alone produced material that would be real content: Ohio Rev. Code
Chapter 2915 charitable gaming read from primary source, the 38 U.S.C. § 5901
accreditation boundary, Ohio liquor permit conditions, IRS quid-pro-quo receipt
rules, national fraternal reporting requirements across five organisations.
**That is a book's worth of researched, cited, dated material for one industry.**

### The risk, stated plainly

**Publishing regulatory content to strangers is a materially different exposure
from computing a date for a customer who signed an agreement.**

- Every one of those research documents says, in its own words, *"I am not a
  lawyer and this is not legal advice,"* and each carries an explicit
  **UNVERIFIED** section. That framing is load-bearing. It cannot be quietly
  dropped when the same material becomes a chapter.
- There is **no engagement letter, no jurisdiction check, and no client
  relationship** with an ebook buyer. An Ohio-specific finding read by a
  Pennsylvania lodge is a foreseeable outcome of selling a book.
- **Regulatory content goes stale, and the platform has a live example of the
  failure mode**: IRS Publication 1771 is three years out of date and still
  prints 2023 figures with a footnote nobody reads. A SAIRN ebook citing 2026
  safe-harbor amounts is Pub 1771 in two years unless it carries a read date and
  a revision policy.

### What that implies for the build

- Every factual claim carries its **source and read date**, exactly as the
  research docs do. That convention already exists; inherit it.
- Each ebook carries a **stated revision policy and an edition date**, and the
  catalog shows which edition a buyer is getting.
- **Counsel reviews the disclaimer and the general-information framing once**,
  before the first regulatory ebook ships — not per book.
- Consider splitting content deliberately: **operational and business content**
  (how a post canteen actually runs, what a Quartermaster's week looks like) is
  Michael's experience and carries little of this risk. **Regulatory content**
  carries all of it. They can sit in one book with different framing, but the
  distinction should be a conscious editorial decision rather than an accident.

---

## 6. The custom-work inquiry flow — the only genuinely new mechanism

Success condition is not "form submitted." It is **an inquiry a human can
actually answer with a price**, which means the form has to extract enough to
scope, without becoming a wall that kills the lead.

**Design questions to settle before building:**

- What is the **minimum viable inquiry**? Business, problem, rough scale, budget
  range, timeline. Budget range is the field everyone omits and the one that
  most determines whether a reply is possible.
- **Is it a form or a conversation?** The platform already has AI-assisted
  intake patterns. An assistant that asks follow-ups produces better-scoped
  inquiries — but it also becomes a public-facing AI under the company's brand,
  which carries the SAIRNroofing lesson: *the assistant must refuse to answer
  questions it has no basis for, especially anything that reads as a quote.*
  **An AI intake must never state or imply a price.**
- **What is the SLA, and is it stated?** An unanswered inquiry is worse than no
  form. If replies take three days, say three days.

**This is a PII intake surface from strangers**, and it deserves the same
treatment the platform applies elsewhere: decide before the table exists what is
collected, who may read it, how long it is kept, and whether it is encrypted.
An inquiry describing someone's business in detail is commercially sensitive to
*them*.

---

## 7. Architecture — what this site is, and what it is not

**It is not a SAIRN app.** The thirteen apps are single-file HTML with vanilla
JS, no build step, gated behind a licence key. A public marketing and commerce
site is a different animal with different constraints: SEO, page speed, public
crawling, and **no licence gate on the front door**.

Open questions, not decisions:

- **Does the site need its own data layer at all**, or can it be static plus
  three endpoints (checkout, ebook delivery, inquiry)? Smallest thing that works
  — see `sairn-minimalism`. A catalog of ~14 items does not need a CMS.
- **Where do inquiries land** — Supabase, or email only? Email only is simpler
  and has a real failure mode (lost in an inbox). Both is the likely answer, and
  the email must be the *notification*, not the record.
- **Ebook delivery** — signed expiring URL vs. account-gated library. The former
  is far less to build and is probably right for v1.
- **Does the customer get an account?** For apps they already effectively have
  one via the licence key. Introducing a second identity system for the site
  would be a real mistake — reuse or don't have one.

---

## 8. Sequencing recommendation

Ordered by dependency and by what is provably ready, not by revenue guess:

1. **Shell + custom-work inquiry flow.** It is the only offering that needs
   nothing else to exist, and it is the one where a missed lead has a real cost.
2. **App catalog** — but **only after** the §4 sellability gate produces a
   per-app verdict and approved claim wording. The gate is the work; the cards
   are easy.
3. **Skill pack link** as a credibility asset (§3). Nearly free.
4. **Ebooks** — after §5's counsel review and after the first book actually
   exists. The line is the strongest differentiator and the slowest to stand up,
   and shipping one excellent industry book beats announcing a line.

---

## 9. Decisions needed from Michael before design starts

1. **Per-app sellability verdicts and claim wording** (§4) — the gate that
   blocks the catalog.
2. **Skill pack: product, credibility asset, or out of scope** (§3).
   Recommendation: credibility asset for v1.
3. **Ebook legal framing** (§5) — counsel review of disclaimer and
   general-information positioning, once, before the first regulatory book.
4. **Custom-work SLA** and whether intake is a form or an AI conversation (§6).
5. **Pricing model** for apps and ebooks — entirely unscoped here, and it
   determines the commerce path.

## 10. What this pass did not cover

Visual design and brand. Pricing. SEO and content strategy. Anything about
competitors in the corporate-site space. Legal entity, terms of sale, refund
policy. ~~Sales-tax obligations on digital goods.~~ **RESEARCHED 2026-08-30 —
`docs/2026-08-30-sairntech-digital-goods-sales-tax.md`. Three findings change
the build: (1) SaaS licences and ebooks are taxed under DIFFERENT Ohio statutory
prongs — SaaS only "for use in business", ebooks to everyone — so they need
separate product classes from day one, not one "digital product" type;
(2) Stripe-as-processor is NOT a marketplace facilitator and SAIRN stays liable,
but Stripe Managed Payments IS merchant-of-record and does take the burden — a
real architectural fork to price before building; (3) the nonprofit exemption
mostly does NOT apply to our customers, because Ohio's is 501(c)(3)-and-
charitable-purposes and the veterans provision reaches STATE HEADQUARTERS only,
not local posts. Register an Ohio vendor's license before the first sale — it is
not threshold-dependent.** Accessibility, which for a public commercial site is a
different bar from an internal tool.

Nothing here is a design decision. It is the list of things that have to be
settled so design can start without being redone.
