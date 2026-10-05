# SAIRNscape competitive-gap audit — 2026-10-05 (CC). **Both halves, one pass.**

**Third and last of the three apps that had no competitive-gap doc of any kind**
(`docs/2026-09-29-competitive-gap-doc-inventory.md`: `sairndesign`,
`sairnlegacy`, `sairnscape`). **With this one, the gap closes: every app on the
platform now has an audit.**

Both halves in one pass, per the method change paid for earlier today when
SAIRNlegacy's Part 2 killed its own Part 1's main claim. Internal figures
measured at `sairnscape.html` at HEAD; every competitor claim is **vendor or
review-site material** and is labelled as such. Sources at the end.

---

## 0. FIRST, A CORRECTION TO MY OWN COMPARISON TABLE FROM THIS MORNING

SAIRNlegacy's Part 1 justified picking that app over this one with a table
containing the cell **"`sairnscape` — 0 panels found by that pattern"**, and used
panel count as a proxy for build-out.

**THE PROXY WAS INVALID FOR THIS APP, AND THE ZERO WAS A STRUCTURAL FACT I
MISREAD AS AN ABSENCE.** `sairnscape.html` is not shaped like the other apps. It
opens with a **marketing hero and a pricing section** and two buttons — *Open
App* and *Business Login* — and routes with `showPage('home')` /
`showPage('app')`. **There are exactly two pages, and the application is behind
the second one.** 170 `scpData` / `function scp…` references confirm the app is
really in the file.

So the honest statement of what I measured is: *this app does not use the
`id="panel-…"` idiom*. **It was never evidence about how much app there is.** The
pick between the three may still have been right — SAIRNlegacy has 36 register
rows against 9 here — but one of the three columns I justified it with was
measuring nothing.

**And the structural difference is itself the most interesting thing about this
app**, for the reason in §3.

---

## 1. What SAIRNscape is, measured

**22 `scp_*` collections.** `docs/CRITICALITY-TIERS.md` carries **9** register
rows, **1 rated Tier A** — the lightest stored-data surface of any app audited.

```
customers  designs    invoices   jobs      quotes    schedule   vendors
progress_photos        settings
irr_controllers   irr_schedules   irr_zones   water_features
```

Two things stand out from the list rather than from prose:

* **A real irrigation subsystem** — controllers, zones, schedules and water
  features as four separate collections. No other SAIRN app has anything like
  it.
* **It publishes its own price.** Three tiers rendered on the landing page:
  **$99, $199, $299**. **No other SAIRN app read in any of these audits states a
  price on its own page.**

The app also carries **domain rate knowledge inside its AI prompts** rather than
in data — crew rates *$45–80/hr per crew member*, maintenance *$150–200/hr*,
mulch *$75–100/yard installed*, and so on. That is a real asset and it is worth
naming where it lives, because prompt text is not a priced catalogue and cannot
be edited by a customer.

---

## 2. THE IRRIGATION SUBSYSTEM — and it competes with the wrong thing

**Read at HEAD, the controller record is an ASSET RECORD, not an integration:**

```js
var rec={id:scpCtlid||('CTL-'+Date.now()), customer_id:customerId, name:name,
         brand:…, model:…, zones_supported:Number(…), …}
```

`brand`, `model`, `zones_supported` — **a manual catalogue of what is installed
at a customer site.** That is a genuinely useful thing for a contractor to have
and it is not what the market in this space sells.

**Vocabulary at HEAD, which is the measurement behind the claim:**

| Term | Occurrences |
|---|---|
| `weather` | **0** |
| `evapotranspiration` / `et0` | **0** / **0** |
| `soil` | **0** |
| `runtime` | **0** |
| `restriction` | 1 |
| `leak` | 3 |
| `rain` | 7 |
| `gallons` | 1 |

**WHAT THE CONTROLLER VENDORS' OWN PLATFORMS DO, from their material:** Hunter
**Hydrawise** does *Predictive Watering* — adjusting schedules from forecast
temperature, rainfall probability, wind speed and humidity — is **flow-meter
compatible for real-time leak detection**, keeps **365 days of Extended System
History**, and gives contractors *Field Insights* across their installed base.
**Rachio** does custom yard mapping by **soil type, plant variety, sun exposure
and slope**. Both reportedly support a **drought mode that respects local
restriction schedules**.

**SO THE GAP IS NOT AGAINST LANDSCAPING BUSINESS SOFTWARE — IT IS AGAINST THE
FREE APP THAT SHIPS WITH THE HARDWARE.** A contractor who installs Hunter or
Rachio controllers already has scheduling, zone detail, leak alerts and a year of
history, from the vendor, at no extra cost. SAIRNscape's four irrigation
collections re-implement the *weakest* part of that (an asset list) and none of
the part that saves water or catches a burst line.

**THE STRATEGIC READING, and it is a question rather than a finding:** the
defensible position is almost certainly **not** to compete with Hydrawise but to
**integrate** — pull controller and zone state in, and own the thing the vendors
do not: the job, the crew, the quote and the invoice attached to that site.
Whether that integration is possible depends on APIs this audit did not
investigate.

---

## 3. PRICING — the only SAIRN app that states one, and it lands in a real band

| Vendor | Published price | Unit |
|---|---|---|
| **SAIRNscape** | **$99 / $199 / $299 per month** | per tenant, from its own landing page |
| **Jobber** | from **$49/mo**, **+~$29/month per user** past the included seats | per firm **+ per user** |
| **Service Autopilot** | **$49** Startup (plus sign-up fee), **$199** Pro, **$499** Pro Plus, custom Elite | per firm, tiered |
| **LMN** | **$297/mo** Starter (1 office/crew-lead + 5 crew licences), **$648/mo** Professional | **bundled licences** |
| **Aspire** | **unpublished**; independent reports of **$300–500+ per user/month**, licensing described as one fee with no user limit | quote only |

**THE PRICE IS NOT THE PROBLEM, WHICH IS WORTH SAYING PLAINLY AFTER TWO AUDITS
WHERE IT WAS.** $99–299 sits squarely inside the Service Autopilot band and
*below* LMN's entry tier. And the per-tenant model is **aligned** here — Aspire
is described as one fee with no user cap and LMN bundles licences, so flat
pricing is normal in this category rather than the exception it was for
`sairndesign`.

**That makes SAIRNscape the one app of the three where the licence model, the
published price and the category norm all agree** — and it is the app with the
*thinnest* feature surface, which is the uncomfortable pairing.

---

## 4. Ranked, both axes

| # | Finding | Severity | Competitor beating us? |
|---|---|---|---|
| 1 | **The irrigation subsystem competes with the controller vendors' own free platforms and loses on every axis that matters** — no weather, no ET, no soil, no runtime, no flow-based leak detection | **HIGH (strategic)** | **Yes, and by the hardware vendor rather than a rival app** — which is harder to beat and cheaper for the customer |
| 2 | **Thinnest stored-data surface audited** — 9 register rows, 1 Tier A, against SAIRNlegacy's 36/20 and SAIRNdesign's 18/10 | **MODERATE** | **Unknown.** Thin is not the same as missing; no feature-by-feature comparison against Jobber or Service Autopilot was run |
| 3 | **Domain rate knowledge lives in AI prompt text, not in data** — crew, maintenance and material rates are strings a customer cannot edit | **MODERATE** | **Yes, by construction.** LMN's whole pitch is estimating and budgeting from the contractor's OWN rates |
| 4 | Pricing and licence unit | **NONE — this one is right** | No. $99–299 per tenant is in-band and the flat model is normal here |

**The two rankings agree on item 1 and disagree on item 2**, where severity is
real and competitive exposure is genuinely unmeasured.

---

## 5. Sources

* [Hunter — Hydrawise software](https://www.hunterirrigation.com/irrigation-product/software/hydrawiser-software)
* [Hydrawise](https://www.hydrawise.com/)
* [Rachio](https://rachio.com/)
* [LMN review — pricing, limits and alternatives (2026)](https://fervorstudio.ca/news/lmn-review-pricing-alternatives/)
* [Service Autopilot vs LMN for landscaping (2026)](https://servicebusinessacademy.org/top-4-differences-service-autopilot-lmn-landscaping-2026/)
* [Top 4 Jobber alternatives for landscaping (2026)](https://servicebusinessacademy.org/top-4-jobber-alternatives-for-landscaping-2026/)
* [LMN vs Jobber vs Aspire](https://hero365.ai/blog/lmn-vs-jobber-vs-aspire-which-landscaping-software-actually-fits-your-business)
* [Best crew scheduling software for landscaping (2026)](https://www.cleansavannah.com/post/best-crew-scheduling-software-for-landscaping-companies-2026)

---

## What this document does NOT claim

* **No vendor was trialled or demoed**; every competitor claim is marketing or a
  review-site summary.
* **No screen of SAIRNscape was clicked.** Everything is read out of the file.
* **No feature-by-feature comparison** against Jobber, LMN, Service Autopilot or
  Aspire was attempted — only the irrigation axis and pricing were compared, so
  item 2 above is deliberately left as unknown rather than scored.
* **Whether Hydrawise or Rachio expose an API** SAIRNscape could integrate
  against was **not investigated**, and §2's strategic reading depends on it.
* **`leak` 3 / `rain` 7 / `restriction` 1 are raw counts** and were not read in
  context, so some may be prose. The four zeros were the load-bearing figures and
  a zero cannot be a false positive.

**BLIND SPOTS: 5.** (1) The competitor half is marketing, and **feature-list
absence is not used as evidence anywhere in this document** — the irrigation
finding rests on what the vendors *advertise they do* against what our file
*measurably lacks*, which is the stronger direction. (2) No negative search:
I did not look for a landscaping platform that also lacks weather-based
scheduling, so "the market does this" rests on two vendors. (3) Pricing is list
price; Aspire is unpublished and its $300–500/user figure is third-party report,
not vendor-stated. (4) The AI-prompt rate knowledge was found by a currency-regex
sweep, so there may be more of it, or less, than the handful quoted. (5) **I
corrected one of my own measurements in §0 and the correction raises a question
this document does not answer** — whether the three-app pick order should have
been different, which would need a buyer-interest signal that nothing here has.
