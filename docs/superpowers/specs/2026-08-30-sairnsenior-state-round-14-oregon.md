# SAIRNsenior — state round 14: Oregon, and Iowa was not an isolated case

2026-08-30. **Research only.** Seventeenth document in the series.

Two findings, both of which change conclusions written earlier in this survey:

1. **Oregon licenses "caregiver registries."** Iowa's platform category is not
   unique — **four states** now have a distinct regulatory category for the
   matching / referral / placement business, under four different names. Round
   13's caution that "no other state has been checked" is answered: **the
   category is common.**
2. **Oregon's 2025 worker-safety statute names a mobile application as the
   compliance mechanism** and specifies the contents of a client intake
   questionnaire. It is the most concrete product requirement found anywhere in
   this survey.

---

## 1. The matching business is a regulated category in at least four states

| State | Category name | Instrument | Found in |
|---|---|---|---|
| **Iowa** | *health care technology platform* | **registration**, $500/yr | round 13 |
| **Colorado** | *home care placement agency* | **registration** | round 6 |
| **Oregon** | *caregiver registry* | **licence** | this round |
| **Nevada** | *referral agency*; *employment agency to provide nonmedical services* | **licence** (both appear in NAC 449's fee schedule) | round 12, noted in passing |

**Round 13 said the absence of a finding elsewhere was not evidence of absence.
That was the right caution and it was warranted** — Oregon's turned up on the
first chapter read afterwards, and Nevada's had already been in a fee list I read
past. **Four states, four names, and no shared vocabulary to grep for.** Any
future state sweep must look for the *function* (matching, referral, placement,
registry, marketplace, staffing) rather than a term.

### ORS 443.100 — Oregon requires a licence, not a registration

> "**A person may not establish, conduct or maintain a caregiver registry, or
> represent to the public that the person is a caregiver registry, without first
> obtaining a caregiver registry license from the Oregon Health Authority.**"

**Two triggers, and the second is unusual:** conducting one, *or* **representing
to the public that you are one**. A marketing claim alone can trip it.

### ORS 443.105 — what OHA may regulate

Rules may cover: **the minimum qualifications of individuals whose services are
offered through** a registry; standards for the organisation and quality of
client care; record-keeping; contractual arrangements for professional and
ancillary services; **criminal background checks on individuals placed on a
roster by a caregiver registry**; complaint procedures; and inspection
procedures.

> **The same shape as Iowa § 135Q.3(2):** the matching entity becomes responsible
> for the *qualifications* and *background checks* of people it never employs.
> Two states, independently, put axis A and axis B on the intermediary.

**A note on vocabulary, so nobody misreads it.** ORS 443.105(5) uses the word
**"roster"**, and SAIRNsenior's own UI uses "roster" thirteen times. **That is a
coincidence of ordinary English, not a trigger.** The statutory hook is
*offering individuals' services to the public as a registry* — an agency
scheduling its own employees, using the word "roster" internally, is not
conducting a caregiver registry. The same reasoning that put SAIRNsenior outside
Iowa ch. 135Q applies here. **But the Oregon "represent to the public" limb means
the marketing copy matters in a way Iowa's does not** — describing the product to
Oregon prospects as a "caregiver registry" would be a poor choice of words with a
statutory edge on it.

Also nearby and unread: **ORS 443.090** (exemption from in-home care agency
licensing) and **ORS 443.095** (applicability of the laws to domestic service) —
both bear on the unlicensed segment, and Oregon's domestic-worker overtime
carve-out for licensed in-home care agencies is already recorded in
`2026-08-29-sairnsenior-domestic-worker-overtime.md`.

---

## 2. ORS 443.190 / 443.195 — a statute that specifies an intake form and a mobile app

Enacted by **2025 c.535 §§ 12–13**. Note the ORS editor's own flag: these
sections *"were enacted into law … but were not added to or made a part of ORS
chapter 443 or any series therein by legislative action"* — they are law, printed
adjacent to ch. 443 but not codified into it. **A citation search restricted to
chapter 443's series would miss them.**

Scope: a **"home health care services entity"** — a home health agency under ORS
443.014, or a home hospice program under ORS 654.412 — delivering services in a
client's home.

### § 443.190 — client intake, and the questionnaire has mandatory contents

At intake the entity **shall**:

- **(2)(a)** collect information necessary to identify and assess potential health
  and safety risks, **including workplace violence as defined in ORS 654.412**,
  that staff may encounter in the setting;
- **(2)(b)** **provide that information, to the extent known, to each staff member
  who will be responsible for providing the services**; and
- **(2)(c)** for patients discharged from a hospital and referred on, provide each
  responsible staff member **any client history of violence made known to the
  entity as part of the continuity-of-care process**.

**§ 443.190(3) then specifies the minimum contents of the intake questionnaire:**

> "(a) The presence of **pets** at the home health care setting and whether such
> pets, if any, **can be secured away from the area in which care is given, if so
> requested by the home health care staff**.
> (b) Suspected **pest infestations**.
> (c) The willingness of the client to agree to **securely store any weapons**
> that are present at the home health care setting **prior to any visit**."

> **This is a form specification in primary legislation.** Nothing else in this
> survey descends to the field level. It is also **directional**: information
> collected from the client must be **pushed to the assigned caregiver**, which
> makes it a property of the *assignment*, not of the client record — the same
> per-assignment shape as Louisiana's per-client competency, arriving from
> worker-safety law instead of licensure law.
>
> The definitions also introduce **"household individual"** — a person other than
> the client *"present or reasonably anticipated to be present"* in the setting —
> so the risk picture is not limited to the client.

### § 443.195 — duties to staff, including a named mobile application

Each entity **shall**:

1. **Train** staff on recognising hazards commonly encountered in home settings
   and protocols for managing them, **consistent with training endorsed by NIOSH
   and OSHA**;
2. **Conduct quarterly safety assessments** with staff assigned to a setting;
3. **Provide staff with identifying information to verify a client's identity
   before an initial visit**;
4. **"Provide mechanisms by which home health care staff can perform safety
   checks, including but not limited to the use of a mobile application to access
   the relevant safety-related information collected … under ORS 443.190"**; and
5. Establish policies allowing staff to **perform data entry and chart updates at
   a time and place outside the home health care setting**, and to **be
   accompanied by an escort** where there are safety or security concerns.

> **Point 4 names the software.** Every other rule in this survey describes an
> obligation a product might help with; Oregon writes the delivery mechanism into
> the statute as the worked example. Points 3 and 5 are equally concrete: identity
> verification **before the first visit**, and **charting away from the client's
> home** — the second of which cuts directly against a point-of-care-only
> documentation design.
>
> And point 1 makes **NIOSH/OSHA-endorsed** content the benchmark — a federal
> pointer on a state training duty, the same coupling family as Missouri,
> Tennessee and Michigan.

---

## 3. Platform-registration sweep — method adopted for every remaining state

Per instruction, each remaining state gets an explicit sweep for a
platform/registry/placement category rather than assuming Iowa was isolated.
**Terms alone are insufficient** — the four found so far share no keyword. The
sweep now runs on **function words**: *registry, referral, placement, staffing,
employment agency, marketplace, platform, roster, temporary, per diem, bids,
open shift*.

Applied to ORS 443 this round: `technology platform` 0, `marketplace` 0,
`staffing agency` 0, `employment agency` 0, `open shift` 0, `independent
contractor` 0, `referral agency` 0 — **and the category was still there**, under
"caregiver registry". **The keyword sweep alone would have missed Oregon.** What
found it was reading the chapter's own section index.

---

## 4. Tier 2 — reported, not independently checked

| Item | Status |
|---|---|
| **OAR implementing ORS 443.105** (the actual caregiver-registry rules) | **NO ROUTE** — `secure.sos.state.or.us/oard` is bot-walled (round 13). The statute authorises rules; their content is unread. |
| ORS 443.090, 443.095 | **NOT READ** — exemption from in-home care agency licensing; applicability to domestic service. |
| ORS 443.004–443.087 (in-home care agency and home health agency licensing proper) | **NOT READ** — only the section index was surveyed. |
| ORS 654.412 (workplace violence; home hospice program) | **NOT READ** — carries the definition § 443.190 incorporates. |
| Whether Oregon's caregiver-registry licence would reach SAIRNsenior | **NOT DETERMINED** | The Iowa-style determination has **not** been run for Oregon. On the face of ORS 443.100 the answer looks the same — no public offering of individuals' services — but that is an impression, not the section-by-section reading Iowa got. |
| Nevada *referral agency* / *employment agency to provide nonmedical services* | **NOT READ** — seen only in NAC 449's fee schedule. |
| Colorado placement agency vs Oregon registry vs Iowa platform — are the triggers actually different? | **NOT COMPARED** | Three different instruments, three definitions, only Iowa's read in full. |
| Mountain West and New England states | **NOT ATTEMPTED** | Next. |
| Alabama, Mississippi, Utah, Connecticut, Kansas | **NO ROUTE** — carried. |
| Indiana | **ON HOLD** — per instruction. |
| The remaining ~17 states | **NOT ATTEMPTED** | Thirty-four touched is not coverage. |

## 5. Method notes

- **The function, not the term.** Four states regulate the same business under
  four names with no shared keyword. Sweeping for "platform" would have found one
  of four.
- **Read the chapter's section index first.** Oregon's `443.100 License required
  for caregiver registry` was visible in the index before any body text was read.
  This is the fifth state where the index was the whole answer.
- **A statute can be law without being codified into the chapter it sits beside.**
  ORS 443.190/443.195 carry an editor's note saying exactly that. A search scoped
  to a chapter's series would skip them.
