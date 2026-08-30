# SAIRNfreedom — Ohio liquor permits for fraternal and veterans lodges

**Read 2026-08-30 from codes.ohio.gov.** Closes the gap flagged as
*"LIQUOR LICENSING IS ENTIRELY UNEXAMINED"* in the phased build spec, and opened
by the D-4/D-4a correction in the alcohol-pricing pass.

**Not legal advice.** Primary-source read by a non-lawyer, same standard as the
ORC 2915 and 38 U.S.C. 5901 passes. `com.ohio.gov` returned **HTTP 404 on every
URL attempted** — nothing here depends on it.

**Scope note:** purchasing and pricing are covered separately in
`2026-08-30-sairnfreedom-four-research-items.md` §3 and were not re-researched.

---

## 1. The retention condition — bigger than we thought, and it names our own fields

**ORC 4303.17(A)(1), verbatim:**

> No D-4 permit shall be granted or retained until all elected officers of the
> organization controlling the club have filed with the division of liquor
> control a statement certifying that the club is operated in the interest of
> the membership of a reputable organization, which is maintained by a dues
> paying membership, **and setting forth the amount of initiation fee and yearly
> dues.**
>
> The roster of membership of a D-4 permit holder shall be submitted at the
> request of the superintendent of liquor control. Any information acquired by
> the superintendent or the division with respect to that membership shall not
> be open to public inspection or examination…

**The certification is THREE things, not two.** The third — *"setting forth the
amount of initiation fee and yearly dues"* — is a **numeric disclosure of the
actual dollar amounts.** Prior research had only the first two.

**That collides directly with §2a of the build spec.** The three-layer fee
structure's **initiation fee** and **annual dues** are not just product
configuration; they are **certified figures on a liquor-permit filing.** And
**ORC 4301.25(A)(3)** makes *"Making any false material statement in an
application for a permit"* an independent revocation ground. Changing a dues
amount without updating the filing is therefore a permit exposure, not a config
change.

**"All elected officers"** — not the presiding officer, not a compliance
designee. A partial filing does not satisfy it. And it is the officers of *"the
organization controlling the club"*, i.e. the post itself, not the department or
national body.

**The roster duty is unqualified.** *"Shall be submitted at the request of the
superintendent"* — no notice period, no form, no time limit, no content spec.
The confidentiality sentence protects the club; it does not limit the duty.

**And the club definition rests on PREPAID dues.** ORC 4301.01(B)(13): a club is
an organization *"membership in which entails the **prepayment** of regular
dues."* A member in arrears is arguably outside the definition the permit rests
on — which makes `dues_paid_through_date` a compliance field, not a billing
convenience.

**No OAC rule elaborates any of this.** The full Chapter 4301:1-1 index and the
definitions rule (4301:1-1-02) were read: **no definition of "club", "member" or
"guest" anywhere.**

---

## 2. Renewal — and the trap is a tax date, not a filing date

**There is no statutory renewal date.** ORC 4303.27 issues permits *"commencing
on the day after the **uniform expiration dates designated by the division**"* —
delegated to the Division and **not in the ORC or the OAC.** Also note a permit
is issued *"for one year, **or part of one year**"*, so a mid-cycle permit
expires on the next uniform date, not twelve months out.

**ORC 4303.271(C):** renewal must be filed **at least 15 days before
expiration**; late filing draws a **10% penalty of the permit fee**; an expired
permit may still be renewed **within 30 days** of expiration. Under ORC 119.06
the existing permit continues while an application is pending.

**Renewal is presumptively granted** — 4303.271(A): the holder *"shall be
entitled to the renewal"* unless rejected for good cause; and OAC 4301:1-1-12(B)
directs the division to presume a same-location renewal *"will not prejudice the
maintenance of public decency, sobriety, and good order."*

### The tax-delinquency trap — the single most software-relevant date here

**ORC 4303.271(D)(2)(a):** the Division **shall not renew** the permit of a
holder the tax commissioner identifies as delinquent **"as of the first day of
the sixth month preceding the month in which the permit expires"**, or assessed
**"on or before the first day of the third month preceding"** expiration.

Taxes swept in include **sales/use, employer withholding, alcoholic beverage,
and cigarette/other tobacco** — all live for a lodge with a canteen.

**The club is judged at six months out and only told at three months out.** By
the time the notice arrives the disqualifying date has passed. Appeal window:
90 days after expiration.

### Local objection

**ORC 4303.271(B):** a municipality, township or county may object to renewal,
**postmarked no later than 30 days before expiration**, by resolution with the
chief legal officer's statement that the objection has substantial legal
grounds. **D-4 is inside the cited range (4303.11–4303.183), so a lodge is
objectionable.** Grounds are in ORC 4303.292(A) — fitness of officers, building
and safety code noncompliance (**not** zoning), inadequate law-enforcement
access, *"substantial interference with public decency, sobriety, peace, or good
order"*, prior nuisance declaration.

**Fees:** D-4 **$469** · D-6 **$500** (to a D-4 holder) · F **$40** · F-2 **$150**
(+$10 for a co-applying D holder).

---

## 3. Hours — D-4 closes ninety minutes before the bar down the street

**OAC 4301:1-1-49(B)** puts **D-4** in the **1:00 a.m.** group:

> (1) From Monday to Saturday **between the hours of one a.m. and five-thirty
> a.m.**
> (2) On Sunday **between the hours of one a.m. and Sunday midnight, unless
> statutorily authorized otherwise.**
> (3) **Consumption** … is **also prohibited** during the above hours upon the
> premises…

**Paragraph (C) — the 2:30 a.m. group — is D-3-with-D-3A, D-4A, D-5 series and
D-7. D-4 is not in it.** A club canteen must close an hour and a half earlier
than a D-5 bar, which is exactly the kind of difference a lodge assumes away.

**(B)(3) prohibits consumption, not just sale.** Last call is not the gate — the
room must be clear of drinks by 1:00 a.m.

**Sunday is closed all day for a D-4 absent a D-6.**

---

## 4. Who may be served — and the one thing nobody can answer

**The entire textual basis is one clause of 4303.17(A)(1):** *"to sell beer and
any intoxicating liquor **to its members only**, in glass or container, **for
consumption on the premises where sold.**"* Three constraints: members only,
on-premises, by the drink as sold.

**GUESTS ARE COMPLETELY UNRESOLVED.** No statute, no OAC rule, no definition of
"guest" anywhere in Chapter 4301:1-1. **No source found permitting them and none
prohibiting them by name.** Every lodge in Ohio serves accompanied guests as a
matter of practice; that practice has **no verified basis in the sources
fetched**, in either direction. **Do not encode a guest allowance as settled
law.** → counsel.

**The roster is the only mandated record.** No guest register, no sign-in book,
no POS membership check is required by anything found. **That absence is the
finding:** the roster is the sole documentary proof the statute names, which
makes roster and dues-status accuracy the entire evidentiary case.

**Serving a non-member** is not a standalone offence — it routes through **ORC
4301.25(A)**, suspension or revocation *"for the violation of any of the
applicable restrictions of either chapter."*

**Staff age limits (ORC 4301.22)** — these are staffing gates, not service
gates: under **18** may not handle, serve or sell at all; under **19** may not
sell beer across a bar; under **21** may not sell wine, mixed beverages or
spirituous liquor across a bar. Plus the absolute rule: *"no permit holder …
shall sell or furnish beer or intoxicating liquor to an intoxicated person."*

---

## 5. Other permits a lodge holds

**D-6 (Sunday) — election-gated.** ORC 4303.182 issues it to a D-4 holder, but
*"only … if the sale has been approved under a question specified in"* the local
option statutes. **A local option election is required.** With it, Sunday hours
mirror Mon–Sat, floor 5:30 a.m.

**To-go under ORC 4303.185** — D-4 qualifies (ORC 4301.82(A) excludes only D-6
and D-8), but with hard conditions: *"may only sell … if the permit holder also
sells a meal"* and *"shall not sell more than three alcoholic beverages per
meal"*, sealed closed containers, bona fide 21+ check. **A canteen selling to-go
drinks without food is outside this.**

**Outdoor sales on lodge grounds — ORC 4303.188.** No extra permit, but requires
a **delineated area**, delivery by the permit holder or employee, and **notice
to the Division and the Department of Public Safety at least ten days before
beginning** (*summarised fetch — verify before treating as a hard gate*).

**F permit (ORC 4303.20)** — **beer only**, *"not to exceed five days"*,
*"No more than two such permits … in any thirty-day period"*, $40, proceeds not
*"for the profit or gain of any individual."*

**F-2 permit (ORC 4303.202)** — beer or intoxicating liquor by the drink at an
event; max **4 consecutive days**; **one per 30 days** per organization; $150.
Eligibility requires the applicant be not-for-profit and organized for a
*"charitable, cultural, educational, fraternal, or political purpose"* and
***"not affiliated with the holder of any class of liquor permit, other than a
D-4 permit."*** The drafters explicitly preserved F-2 for D-4-affiliated
organisations. **Strict liability** for out-of-hours sales.

---

## 6. HALL RENTAL — the verdict changes the Phase 2 feature

**Renting the hall for an alcohol-serving event has a real permit dimension. It
is not a room booking with a deposit tier.**

The D-4 sells *"to its members only."* **The lodge's own permit does not cover
serving a renter's non-member guests.**

The mechanism Ohio provides is the **jointly-issued F-2** —
**OAC 4301:1-1-36(B), verbatim:**

> a class F-2 liquor permit applicant may request that the permit be issued
> **jointly to the applicant and a class D-3, D-4, or D-5 liquor permit holder,
> who is to conduct the sale of beer and intoxicating liquor at the event.**

ORC 4303.202 confirms the design by exempting D-4 affiliation from the
disqualifying test, and the co-applying D holder *"may receive an unlimited
number of joint F-2 permits"* at $10 each.

**But that path is open only to a NOT-FOR-PROFIT renter** organised for a
charitable, cultural, educational, fraternal or political purpose, whose
proceeds go to the stated purpose and not to any individual's gain. **A wedding,
a birthday party, a corporate rental — none of these qualify.**

### Three modelled cases, and the third is a refusal

1. **Member-hosted, lodge serves** — covered by the D-4. Gate that the host is
   dues-current and attendees fall under the members-only rule.
2. **Not-for-profit renter, lodge serves** — joint F-2 workflow: renter's
   non-profit qualification, 4-day and 1-per-30-days limiters, fee tracking,
   chief-peace-officer notification, proceeds destination.
3. **Private or commercial renter wanting alcohol** — **no verified permit path
   exists. The correct product behaviour is a HARD BLOCK plus an escalation
   prompt to counsel, not a permissive default with a bigger deposit.**

**The alcohol-serving damage-deposit tier in the Phase 2 design must be gated
behind cases 1 and 2. Case 3 refuses the booking rather than pricing it.** The
failure mode is a lodge selling drinks to a wedding party under its D-4 and
losing the permit under ORC 4301.25(A).

---

## 7. Suspension, premises responsibility, and a cross-module link

**ORC 4301.25(A)** — suspension or revocation for violating any applicable
restriction or lawful rule, *"for other sufficient cause"*, and for enumerated
causes including **(A)(3) false material statement in an application** (see §1)
and conviction of the holder or an agent/employee for a felony. **(B)** is a
**mandatory** revocation on conviction under ORC 2913.46 (SNAP/WIC misuse).

**OAC 4301:1-1-52** — *"No permit holder, their agent, or employee shall
knowingly or willfully allow in and upon the licensed permit premises any
persons to:"* disorderly activity, nudity, sexual activity, public indecency,
controlled substances, food-assistance fraud, theft/fraud. Plus: employees may
not be intoxicated while working; no facilitation of human trafficking; weapons
restrictions; no tobacco/nicotine sales under 21.

**OAC 4301:1-1-53 — gambling, and it couples the two modules.** Conviction for a
Chapter 2915 gambling violation grounds suspension; **(D) and (E) permit
charitable games and instant bingo by licensed organisations *"provided strict
compliance occurs"* with Chapter 2915.**

> **A Chapter 2915 bingo violation is simultaneously a liquor-permit exposure.**
> The gaming module and the liquor module are not independent.

**OAC 4301:1-1-21** — *"The current, original permit issued by the division shall
always be kept on the licensed premises."* During suspension a copy of the
notice must be posted over the permit; purchases and deliveries are allowed in
the final two weeks.

**ORC 4301.66** — no person shall hinder or obstruct an inspection.

**Server training — ORC 4301.253 — VOLUNTARY, but worth tracking.** The
commission *"shall consider whether the permit holder and the permit holder's
employees have successfully completed a training program"* when deciding
suspension, revocation or forfeiture. **The duty runs to the commission, not the
permit holder.** It is a statutory **mitigating factor at the penalty stage** —
so the club only gets the benefit if it can prove completion when it is already
in trouble. Track it.

---

## 8. Records retention — none found, and that is the finding

**No Ohio liquor analogue to ORC 2915.10's three-year bingo rule was found**,
and it was looked for directly: OAC 4301-3-01 has no retention provision;
4303.17 requires the roster be *submitted on request* but never *retained*;
4301.66 imposes no records duty. The only affirmative on-premises document duty
is OAC 4301:1-1-21 (keep the original permit).

**Default the liquor module to three years, mirroring the bingo rule, and label
it in the UI as a POLICY CHOICE, not a legal requirement.** The real retention
driver is the 4303.271(D) six-month tax lookback, plus Title 57 sales/use and
withholding retention rules that were not researched.

---

## 9. What the software must do

**Officer certification module** — on the club: `d4_permit_number`,
`d4_permit_expiration_date`, `initiation_fee_amount` and `annual_dues_amount`
(**both certified figures**), `officer_certification_filed_date`, a scan of the
filed statement, and a snapshot of every elected officer named on it. On the
officer: `is_elected_officer` (**elected**, not appointed — committee chairs and
the bar manager do not count), term dates, and
`included_in_current_d4_certification`.

**Two gates.** If any elected officer is not on the filed statement, raise a
blocking flag naming ORC 4303.17(A)(1) — **but flag it, do not assert a refiling
is legally required**, because the statute does not say so (§10). And if a
certified fee or dues amount changes, flag it against ORC 4301.25(A)(3).

**Roster module** — `dues_paid_through_date`, not a boolean, answerable
retroactively. **Append-only, never hard-delete**: production can be demanded at
any time and used in a Commission hearing. A one-button point-in-time roster
export with a settable as-of date. Restrict and log every export — the statute
makes membership information non-public.

**Renewal calendar**, anchored to a **per-club expiration date the club enters
from its own permit** (§10 — do not hardcode):

| Offset | Reminder | Cite |
|---|---|---|
| **E − 6 months, 1st of month** | **Tax filings must be current TODAY.** Delinquency as of this date blocks renewal — no notice for another three months | 4303.271(D)(2)(a) |
| E − 90 days | Officer certification review | 4303.17(A)(1) |
| E − 3 months, 1st | Watch for a delinquency notice; assessments by this date also block | 4303.271(D) |
| **E − 30 days** | **Local objection window closes** | 4303.271(B) |
| **E − 15 days** | **Renewal filing deadline** — later draws a 10% penalty | 4303.271(C) |
| **E + 30 days** | **Absolute late-renewal cutoff** | 4303.271(C) |
| E + 90 days | Appeal deadline if denied for tax delinquency | 4303.271(D)(2)(b)(i) |

**Bar/POS gates** — hard block on sale **and open-container consumption**
1:00–5:30 a.m. Mon–Sat; Sunday fully blocked unless `d6_permit_held`. Put
`permit_hours_class` on the club (D-4 defaults to the 1:00 a.m. group) so a
later permit change cannot silently inherit the wrong cutoff. Every alcohol sale
attaches to a `member_id`; non-member sale requires an explicit logged override.
One-tap intoxication-refusal log. Staff DOB with the 18/19/21 shift gates. To-go
requires a meal on the same ticket, capped at three drinks per meal.

**Events module** — F and F-2 limiters as **rolling 30-day counters** with a
hard warning before a booking breaches them; chief-peace-officer notification
and limited vendor's licence as required uploads (OAC 4301:1-1-34); proceeds
destination recorded; 10-day advance notice task for outdoor sales.

**Cross-module** — any Chapter 2915 compliance failure raises a flag on the
**liquor** dashboard citing OAC 4301:1-1-53(D)–(E).

---

## 10. UNVERIFIED / COULD NOT CONFIRM

1. **The actual uniform expiration dates.** Delegated to the Division by ORC
   4303.27; not in the ORC or OAC. Search snippets consistently report
   **February 1 / June 1 / October 1** by district with a ~34-county list, but
   **no page confirming this could be fetched** — `com.ohio.gov` 404'd on every
   attempt. **Do not hardcode. Make it a per-club entered field and confirm with
   the Division at onboarding.**
2. **Whether officer turnover requires a fresh certification.** The statute
   conditions retention on the filing and is **silent on refiling**. *"The
   current officers must have filed"* and *"the officers who filed were the
   officers at the time"* are different rules and the text does not choose.
   → counsel.
3. **Whether the certification is one-time or recurring.** Same silence; no
   annual-filing language anywhere, and no renewal-linked certification in
   4303.271.
4. **Guest privileges — completely unresolved in either direction.** → counsel.
5. **Any guest register or sign-in requirement** — none found; Commission
   decisions and Division bulletins not searched.
6. **How ORC 4303.185's "personal consumer" interacts with members-only.**
   Nothing reconciling them was found. **Do not build to-go sales to
   non-members on the strength of 4303.185.**
7. **F-2 closing hours.** OAC 4301:1-1-49(B) puts F-2 in the 1:00 a.m. group;
   ORC 4303.202 says F-2 tracks D-3 hours. Unreconciled, and 4303.202 imposes
   **strict liability**.
8. **ORC 4303.188's ten-day notice** — summarised fetch, not literal.
9. **ORC 4303.202, 4303.292(A), 4301.22, 4303.188, OAC 4301:1-1-52 and -53** —
   summarised, not literally transcribed. Quoted fragments are reliable; the
   surrounding characterisations are paraphrase. **Re-pull literal text before
   any of it becomes customer-facing compliance copy.**
10. **D-4 quota exemption.** ORC 4303.29 limits D-3/D-4/D-5 to one per 2,000
    population. Exemptions reviewed cover airports, **soldiers' memorials**,
    golf courses, fairgrounds, zoos and park districts — **no club or fraternal
    exemption surfaced, but the soldiers'-memorial exemption may well reach a
    VFW or Legion post.** Reviewed via summary; worth a dedicated look.
11. **Liquor record retention** — none found for a D-4; Title 57 not researched.
12. **D-6 local option election mechanics** — the requirement is confirmed and
    six statutes are cited, but **none was fetched**. Petition process, ballot
    wording, timing and precinct scope all unresearched.
13. **OAC 4301:1-1-52's 2026-05-01 effective date** — whether an earlier version
    currently governs was not checked.

---

## Must go to Ohio liquor counsel or the Division regardless

**Two gates the software will otherwise guess at:** whether a D-4 club may
lawfully serve accompanied non-member guests (§4 — no primary source either way,
yet every lodge does it, and the product must either permit or block it), and
whether a change in elected officers requires a fresh 4303.17(A)(1)
certification (§10.2–3 — the difference between "flag it" and "block it" is a
legal question, not a product one).

**Confirming each client's county expiration date with the Division belongs in
onboarding**, not in a value the software supplies.
