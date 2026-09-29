# SAIRNbuild cloud audit (PR #18) — re-derived at HEAD

**2026-09-29 (Hank).** Item 13 of queue23. **DOCS ONLY — nothing was built and
nothing in `sairnbuild.html` was changed by this pass.** Every cell below was
re-derived against the file at HEAD rather than carried forward, and where a
finding rests on an absence, the search that established the absence is printed
so a reader can re-run it.

`sairnbuild.html` at HEAD: **9,470 lines.**

---

## 1. First sign-in shows two integrations as CONNECTED, connected to nothing

**Confirmed. This is the sharpest of the three.**

`seed()` writes `bld_integrations` at `sairnbuild.html:3511`:

| id | name | status |
|---|---|---|
| INT-01 | QuickBooks Online | **`connected`** |
| INT-02 | DocuSign | **`connected`** |
| INT-03 | Bill.com | `pending` |
| INT-04 | Stripe | `not_connected` |
| INT-05 | HelloSign | `not_connected` |

The Integrations panel renders a KPI reading **`Connected` / `Active`**
(`:1292`), so a first sign-in shows **Connected: 2**.

**THE SEARCH THAT ESTABLISHES THE ABSENCE, because a finding that rests on
"there is no code" has to say how it looked:**

```
grep -ciE 'quickbooks|docusign|hellosign|bill\.com' sairnbuild.html   ->  0
```

Zero — outside that one seed literal. **There is no QuickBooks code, no DocuSign
code, no OAuth, no API call, no token field anywhere in the file.** The resource
holds `{id, name, category, status, last_reviewed, notes}` — it is a **register of
which integrations the business has evaluated**, and nothing more.

**Why that is a real problem rather than a cosmetic one.** The panel does not say
"integrations we are considering"; it says **Connected / Active**, on a seeded
row, before the user has done anything. `notes` reinforces it — *"Synced for job
costing exports"* for QuickBooks, *"Used for signed change orders"* for DocuSign.
Both describe a live data flow that does not exist. A contractor evaluating this
app on day one is shown two working integrations, and the evidence for them is a
row the app wrote to itself.

**This is the fabricated-KPI shape from `sairn-guardian-v2` Check 0b**, with one
difference that makes it worse rather than better: the number *is* computed, from
real stored rows, by real code. The fabrication is in the **seed**, and no check
that looks for a KPI with no function behind it would find this one.

**WHAT THIS AUDIT DOES NOT CLAIM:** that seeding demo data is wrong. The file
argues for it explicitly at `:3413` — the portal needs *"something genuine to show
across every card"* — and that is sound. The finding is narrower: **a status value
that asserts a connection is a different kind of seed from a sample job or a
sample invoice.** One is illustrative; the other is a claim about the deployment
the user is looking at.

**A fix that requires no new code:** seed `INT-01` and `INT-02` as `pending` with
notes saying *"evaluated — connector not built"*. Every panel keeps its shape,
the KPI keeps its formula, and nothing asserts a connection. **Not done here** —
this is a docs-only pass and `sairnbuild.html` carries no claim of mine.

---

## 2. The Client Portal has no usable homeowner link

**Confirmed, and it is a product-shape finding rather than a bug.**

`rClientPortal()` at `:6803` is thorough and well-judged. Its header is worth
quoting because it shows the information boundary was thought about properly:

> *"Deliberately homeowner-facing only: cost, margin, committed spend, and
> internal notes never render here even though the underlying job/cost records
> carry them. This is the one panel in the file where showing internal numbers
> would be a real information-boundary mistake."*

It renders address, stage, target completion, blockers, photo count, accepted
change orders with amounts, selections with status, and message count. **That is a
genuinely good homeowner view.**

**AND NO HOMEOWNER CAN REACH IT.** The search:

```
grep -niE 'share|magic link|invite|homeowner|token' sairnbuild.html
```

returns the sidebar button, the panel title, its subtitle, and session-token
plumbing for the *contractor's* own login. **There is no share link, no invite, no
per-job token, no public page, no email-out.** The panel lives behind
`api/bld-auth.js` inside the contractor's authenticated app.

So the feature as shipped is: **the contractor can look at what the homeowner
would see.** That has real value for a walkthrough on a phone. It is not what the
subtitle says — *"Shared view for the homeowner"* — and the sidebar groups it
under a heading **"Client"** alongside nothing else.

**The gap is one field and one page, not a rewrite.** A per-job read-only token
and a public page rendering the same function is the whole feature; the
information boundary is already decided and already enforced in one place.

**WHY IT MATTERS COMMERCIALLY, stated once:** a client portal is a headline
feature in this market, and the app lists one. If a prospect asks *"can my
homeowner log in and see this"*, the honest answer today is no.

---

## 3. Ohio home-construction law, RRP, and lien deadlines

### 3a. Lien waivers — the paperwork is tracked, none of the clocks are

`bld_lien_waivers` (`:3297`) holds
`{id, job_id, draw_id, party, type, amount, status, date}` with
conditional/unconditional and executed/pending. The panel's own subtitle is
accurate: *"the paperwork that travels with money."*

**No deadline is computed anywhere.** The search:

```
grep -nE '75 day|60 day|90 day|daysUntil|deadline' sairnbuild.html
```

returns exactly one hit, `item_28` in an unrelated training-needs list. Also zero
for `notice of commencement`, `notice of furnishing`, `mechanics lien`, and
`1311` (the ORC chapter).

**What that means and what it does not.** Ohio's mechanics' lien regime runs on
hard clocks — the notice-of-furnishing window after a notice of commencement is
recorded, and the affidavit-filing window after last work — and **missing one
extinguishes the right, not just the paperwork.** This app records who signed
what for how much. It does not know when anything is due.

**THE MACHINERY FOR THIS ALREADY EXISTS IN THE FILE**, which is why this is worth
raising rather than dismissing as out of scope: `complianceDaysUntil()` and
`subDocIssues()` (`:6250`) already compute days-until on a stored date, split the
answer into **blocking** and **expiring**, and feed `eligibleToBid` — a gate that
genuinely refuses. A lien clock is the same shape with a different source date.

**AND THE HARD PART IS NOT THE ARITHMETIC — it is that the deadline depends on
facts the app does not record** (whether a notice of commencement was filed, and
when last work occurred on that job). **That is the finding to act on first**, and
it is a data-model question, not a calculation one.

### 3b. RRP — zero occurrences, and the gate that would carry it already exists

```
RRP 0 | lead-safe 0 | lead safe 0 | pre-1978 0 | renovate right 0
```

**Nothing in the file mentions lead-safe renovation.** For a residential
remodeler, EPA's Renovation, Repair and Painting rule attaches to work disturbing
painted surfaces in pre-1978 housing: the firm must be certified, a certified
renovator must be assigned, and the pamphlet must be delivered before work starts.
Firm certification **expires**.

**The subcontractor compliance table already tracks exactly this shape.**
`subDocIssues()` blocks an award on an expired certificate of insurance or
licence and warns at 30 days. **RRP certification is simply not one of the
credentials in the list** — `w9_on_file`, `coi_expiry`, `licence_no`,
`licence_expiry`, and nothing else.

**So the cheapest useful change in this whole document is one more expiry field on
`bld_subs` plus one more line in `subDocIssues()`** — the gate, the badge, the
KPI and the award refusal all follow for free. Stated as an observation; **not
built here.**

### 3c. The Ohio Home Construction Service Suppliers Act — not modelled

```
4722 0 | HCSSA 0 | right to cure 0
```

ORC 4722 governs home-construction service contracts above a dollar threshold:
required written terms, and a supplier's right to cure before certain claims
proceed. The app has bids, proposals, change orders and accepted contract values
— and **no contract-terms check of any kind.**

**This is the weakest of the three legal findings and is marked as such.**
Whether 4722 applies turns on the contract's value and character, and this audit
did not establish that SAIRNbuild's users are inside its scope. **Recorded as a
question for a lawyer, not as a defect.**

---

## What this audit did NOT do

* **It changed no code.** Docs only, as instructed. Every remedy above is
  described and none is applied.
* **It did not run the app.** Every finding is from source at HEAD. The
  integration statuses, the portal's reachability and the three legal absences
  are all facts about the file, which is the right evidence for all three — but a
  live walkthrough could still surface something a read does not.
* **It did not check the other seeded resources for the same shape as §1.** The
  integrations seed asserts a *connection*; ~30 arrays are seeded in one pass
  (`:2351`), and whether any other seeded value makes a claim about the
  deployment rather than illustrating a workflow was **not swept**. That sweep is
  the obvious follow-on and is named rather than quietly skipped.
* **It gave no opinion on whether ORC 4722 applies.** See §3c.
