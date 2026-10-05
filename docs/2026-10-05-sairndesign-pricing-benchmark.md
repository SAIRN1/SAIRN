# What a 10-person interior design firm actually pays — the number any SAIRNdesign tier has to be set against

**Researched 2026-10-05 (Fourth). Published list prices, fetched from each
vendor's own pricing page today.** Every figure below is quoted, not inferred.

---

## 0a. THE CONFIRMED PRICE BOOK — Michael, 2026-10-05

**This supersedes §0's "there is no pricing".** Pricing was confirmed after the
benchmark below was researched, and is now recorded in the same place and the
same format as StoneDesk's, in `api/_lib/exec-context.js`.

| Tier | Price |
|---|---|
| **Business** | **$399/mo** |
| **Professional** | **$599/mo** |
| **Enterprise** | **$899/mo** |
| Above that | **custom quote**, for full design-implementation engagements |

**There is no entry-level tier below Business**, matching StoneDesk's posture.
**No Stripe price IDs are on file for SAIRNdesign** — stated because the
StoneDesk line in the same file does claim them, and inheriting that phrasing
would be a claim this repo cannot verify.

**Two sources, and a test that makes them agree.** This table and the
`exec-context.js` line are the two places the figures live, and
`tests/sairndesign_pricing.js` reads both. That is not ceremony: the incident
`tests/pricing_single_source.js` exists for is StoneDesk carrying two price
lists that disagreed, in two files, with the one a customer signs being the
wrong one.

### What the benchmark below says about these three numbers

- **$599 Professional is the strong one.** A 10-person firm pays **$790/mo** on
  Studio Designer Professional and **$790/mo** on Design Manager. At $599 per
  firm we undercut the established cluster by ~$190/mo at ten seats, and
  because ours is per-firm and theirs is per-seat **the gap widens with every
  hire** — at 15 people they pay $1,185 and we still charge $599.
- **$399 Business is comfortably inside the band** ($350–$1,090 at ten seats)
  and sits just above Programa's 10-seat total of $350.
- **$899 Enterprise is ABOVE the cluster**, including Studio Designer's top
  Premier tier at $1,090 only for firms over ~8 seats. That is a real position
  rather than a safe one: it needs the full design-implementation scope to
  carry it, not feature breadth. Flagged, not objected to — it is a confirmed
  decision.
- **Still unmeasured: Houzz Pro**, whose pricing page 404'd. It is the largest
  name in the category and is absent from every figure here, so none of the
  three comparisons above account for it.

---

## 0. The premise of the research task was wrong, and that is why §0a is separate

**The research task** was to price a 10+ person firm *"under the current employee-headcount
tiers"*. **There are no such tiers.** The repo was searched for a SAIRNdesign
pricing model and holds none: no price table, no headcount bands, no per-seat
figure, nothing in `sairndesign.html`, `api/_resources/sairndesign.js` or any
doc. Every file matching *tier* in `docs/` is the **criticality** tier system
(A/B/C, data-risk) — a different thing that shares a word.

So there is **no under-monetisation gap to measure**, because there is nothing
being charged to compare against. What there is, and what this provides, is the
**benchmark a tier would have to be set against** — before a price gets locked,
which is what the task was actually for.

---

## 1. The market, at list

| Vendor | Published price | Unit |
|---|---|---|
| **Studio Designer** — Essentials | **$69/user/mo** billed annually · **$79** monthly | per seat |
| **Studio Designer** — Professional | **$79/user/mo** annually · **$89** monthly | per seat |
| **Studio Designer** — Premier | **$109/user/mo** annually · **$119** monthly | per seat |
| **Design Manager** — Standard | **$79/mo per user** | per seat |
| **Mydoma** — single plan | **$58/mo/user** billed yearly | per seat |
| **Programa** — Pro | **$71/mo** first seat, **+$31/mo** each additional | per seat, cheap marginal |

**All four price per seat.** None of them publishes a per-firm price.

## 2. What that costs a 10-person firm

| Vendor / plan | 10 people | 15 people | Annualised at 10 |
|---|---|---|---|
| Programa Pro | **$350/mo** | $505/mo | **$4,200** |
| Mydoma | **$580/mo** | $870/mo | **$6,960** |
| Studio Designer Essentials | **$690/mo** | $1,035/mo | **$8,280** |
| Studio Designer Professional | **$790/mo** | $1,185/mo | **$9,480** |
| Design Manager Standard | **$790/mo** | *unknown — see §4* | **$9,480** |
| Studio Designer Premier | **$1,090/mo** | $1,635/mo | **$13,080** |

**The band at 10 people is $350–$1,090/month.** The two established
full-operations products (Studio Designer, Design Manager) **cluster tightly at
~$790/month** for a 10-seat firm on their mid plan.

**Programa is the outlier and the reason is structural, not a discount:** its
marginal seat is $31 against a $71 first seat, so it gets cheaper per head as
the firm grows. The pure-per-seat vendors get linearly more expensive. At 10
people Programa is **55% below** Studio Designer Essentials; at 15 it is 51%
below.

## 3. What this means for a per-firm price

SAIRN's licence model is **per tenant, not per seat**, which is a real
differentiator in a market where every vendor charges per head — and it cuts
both ways:

* **A flat per-firm price set from the small-firm band badly under-prices a
  10-person shop.** For scale, `docs/2026-10-05-sairnlegacy-positioning.md`
  records death-care software at **$49–$200/month per firm**. If a SAIRNdesign
  tier were set anywhere in that band, a 10-person firm paying $200 would be
  paying **$590/month less** than the Studio Designer / Design Manager cluster
  it is choosing against — **$7,080 a year, from one customer.** That is the
  gap the task was looking for, and it is real the moment a low flat price is
  locked in.
* **The ceiling is visible and it is not generous.** $790/month for 10 seats is
  what the market bears at the mid tier; $1,090 at the premium tier. A per-firm
  price above ~$800/month for a 10-person firm is asking them to pay more than
  the incumbent, which needs a reason beyond breadth.
* **Per-firm pricing is a strong story at scale and a weak one at 1–3 people.**
  At 2 seats Studio Designer Essentials is $138/month; a flat $299 per-firm
  price loses that customer. Any headcount banding should be read as *protecting
  the small end*, not as *extracting from the large end*.

**The honest planning range for a 10+ person firm is $400–$800/month per firm**
— above Programa's 10-seat total, at or below the per-seat cluster. That is a
position, not a recommendation: it is derived from list prices only, and §4 is
why it should not be treated as more than that.

## 4. What I could NOT get, named rather than estimated

* **Houzz Pro** — the pricing URL returned **404**. It is a major competitor in
  this category and is **absent from every figure above**. The band in §2 is
  therefore incomplete, not a market survey.
* **Design Manager above 10 users** — the page says *"For teams larger than 10,
  please contact our Sales team"*, so the $790 figure is the **last published
  point before pricing goes private**. The 15-person column has no Design
  Manager row for that reason rather than an extrapolated one.
* **Mydoma monthly** — only the annual rate ($58) is published. The monthly
  rate will be higher; every other vendor here charges a $10/user premium for
  monthly, but that is a pattern, not their number, so it is not in the table.
* **Studio Designer minimum seats** — not published. If there is a floor, the
  small-firm figures in §3 are wrong in our favour.
* **Programa annual** — the page has an annual toggle whose figures did not
  render. $71/$31 are the **monthly** rates, so Programa's real annual cost is
  at or below what §2 shows.
* **Discounting.** These are list prices. Nothing here reflects what a firm
  actually negotiates, and in a category where one vendor hides pricing above
  10 seats, the list is likely the ceiling rather than the transaction.

## 5. What would make this document wrong

A vendor repricing — these were fetched on one day, from pages that change. The
specific thing to re-check before a tier is locked is **Houzz Pro**, because it
is the largest name in the category and this pass has nothing on it at all.

## Sources

- [Studio Designer — Pricing](https://studiodesigner.com/pricing/)
- [Design Manager — Pricing](https://www.designmanager.com/pricing)
- [Mydoma — Pricing](https://www.mydomastudio.com/pricing)
- [Programa — Pricing](https://www.programa.design/pricing)
