# SAIRNsenior — intermediary-category scope: Oregon, Colorado, Nevada

2026-08-30. **Scope determination**, same standard as
`2026-08-30-sairnsenior-iowa-135Q-scope-determination.md`.

> **A documented reading of primary text, not legal advice.** Confirm with
> counsel before anything customer-facing rests on it.

Round 14 said the answer for these three *"looks the same on the face of it"* and
labelled that an impression. **Read properly, the conclusion holds for all three
— and one of round 14's own claims was wrong.**

---

## The answers

| State | Category | SAIRNsenior | Why |
|---|---|---|---|
| **Oregon** | *caregiver registry* (licence) | **OUTSIDE** | The roster must be **of private contractor caregivers** and **provided to the client for use in hiring**. SAIRNsenior's roster is the agency's own employees, used by the agency to assign. |
| **Colorado** | *home care placement agency* (registration) | **OUTSIDE** | Requires an organisation that, **for a fee, provides ONLY referrals** of providers to consumers. SAIRNsenior provides no referrals and is not paid for any. |
| **Nevada** | *employment agency to provide nonmedical services* (licence) | **OUTSIDE** | Requires an employment agency that **contracts with persons** to provide the care. SAIRNsenior contracts with no caregivers. |
| **Nevada** | *referral agency* (licence) | **NOT APPLICABLE — and round 14 was wrong to list it here** | See § 4. |

---

## 1. Oregon — ORS 443.014(1)

> "'**Caregiver registry**' means a person that **prequalifies, establishes and
> maintains a roster of qualified private contractor caregivers** that is
> **provided to a client or the client's representative for consideration in the
> hiring of an individual** to provide caregiver services within the client's
> place of residence."

**Four cumulative elements:**

| # | Element | SAIRNsenior |
|---|---|---|
| 1 | **prequalifies** caregivers | The *agency* qualifies its own staff; the software records it. |
| 2 | a roster of **private contractor** caregivers | The roster is the agency's **employees** — the app reads it through the shared `employees` resource. |
| 3 | the roster is **provided to a client or the client's representative** | It is never exposed to clients. It is an internal scheduling roster. |
| 4 | **for consideration in the hiring** of an individual by that client | Clients do not hire caregivers in this model; the agency assigns them. |

**Outside on elements 2, 3 and 4 independently.**

**But ORS 443.100's second limb is a real constraint on words, not architecture:**
a person may not *"**represent to the public that the person is a caregiver
registry**"* without a licence. **Marketing copy aimed at Oregon must not
describe SAIRNsenior as a caregiver registry**, and should avoid framing the
roster as something clients browse and hire from. Iowa has no equivalent limb.

**And if it were inside, the cost is not just a fee:** ORS 443.019 requires the
Oregon Health Authority to conduct an **in-person site inspection of a caregiver
registry before licensure and at least once every three years thereafter**
(accreditation may substitute in defined circumstances).

---

## 2. Colorado — 6 CCR 1011-1 ch. 26 § 2.12

> "'**Home care placement agency**' means an organization that, **for a fee,
> provides only referrals of providers to home care consumers seeking services**.
> A home care placement agency **does not provide skilled home health services or
> personal care services, directly or by contract**, to a home care consumer…"

**SAIRNsenior provides no referrals of providers to consumers, and takes no fee
for doing so. Outside.**

> **The word "only" carries weight and is worth keeping.** An organisation that
> both refers *and* provides services is **not** a placement agency — it is a
> licensed home care agency under Parts 5–7. So the Part 3 regime (including the
> **prohibition on directing, controlling, scheduling or training**, flagged as a
> build constraint in round 6) applies to **pure-referral businesses only**. A
> customer that does both is fully in the licensed regime, and the scheduling
> prohibition does **not** bind them.
>
> **That materially narrows the round-6 build constraint** — it gates on
> *pure-referral* status, not on "has a Colorado registration". The account-level
> capability gate should key on that, and the product needs to know which of the
> two a Colorado customer is.

Statutory basis: C.R.S. § 25-27.5-101 et seq.

---

## 3. Nevada — NAC 449.0033

> "'**Employment agency to provide nonmedical services**' means an **employment
> agency that contracts with persons to provide** 'nonmedical services related to
> personal care to elderly persons or persons with disabilities,' as that term is
> defined in NRS 449.01517."

It is licensed as a *"facility"* by operation of NAC 449.0034, which sweeps in
*"an employment agency that contracts with persons in this State to provide
certain nonmedical services described in subsection 1 of NRS 449.03005"*.

**The operative element is contracting with the caregivers.** SAIRNsenior
contracts with its agency customers for software; it engages no caregivers.
**Outside.**

---

## 4. Correction — Nevada's "referral agency" is not an analogue at all

Round 14's table listed Nevada as contributing **two** intermediary categories.
**That was wrong on one of them.** NAC 449.0061:

> "'**Referral agency**' means a business that provides **referrals to residential
> facilities for groups** which is subject to regulation pursuant to NRS
> 449.0305, including … any business entity that engages in the process of
> **referring clients for compensation to residential facilities for groups**."

**It refers *clients into group residential settings* — assisted living
placement. It is not about matching caregivers to homes**, and it is not a
sibling of Iowa's platform, Colorado's placement agency or Oregon's registry.

**How the error happened:** I read the category name in NAC 449's *fee schedule*
and matched it to the pattern I was already looking for, without reading the
definition. **A category name in a fee list is not a definition** — the same
class of mistake as the Missouri false negative and the Tennessee wrong-guess
citation, in a third disguise.

**Revised count: three states have a caregiver-matching intermediary category** —
Iowa, Colorado, Oregon — **plus Nevada's employment-agency variant**, which is
adjacent but hinges on *contracting with workers* rather than on matching.

---

## 5. What is still not determined

- **Whether any of the three would reach a future SAIRNsenior open-shift
  marketplace.** All four determinations (with Iowa) are about the product **as
  built on 2026-08-30**. Iowa's trigger is bidding; Oregon's is a roster provided
  to clients for hiring; Colorado's is fee-for-referral; Nevada's is contracting
  with workers. **A marketplace feature would need re-testing against all four
  separately — they would not all flip together.**
- **The Oregon OARs implementing ORS 443.105** — unreachable (OARD bot-walled),
  so the registry rules' content is unknown.
- **ORS 443.360** *"Agency with choice services; license required"* and **ORS
  443.370–443.376** *"LONG TERM CARE REFERRAL — registration; duties of referral
  agents; violation as unlawful practice"* — **two further Oregon intermediary
  categories, found in the chapter index this round and NOT read.** Oregon may
  have three, not one.
- **C.R.S. § 25-27.5-101 et seq.** — Colorado's statutory basis, unread.
- **NRS 449.01517, 449.03005, 449.0305** — Nevada's underlying statutes, unread.

## 6. Method note

**Read the definition, not the label.** Three of the four categories in round 14's
table were identified from a name; only Iowa's had been read. One of the three
turned out to be a different business entirely. The rule that keeps working:
**a name in an index or a fee schedule tells you a category exists — nothing
more.**
