# SAIRNsenior — state round 11: Michigan confirmed, and it is not the null case I expected

2026-08-30. **Research only.** Thirteenth document in the series.

Round 10 parked Michigan as *"consistent with, but not proof of"* a no-licensure
position, pending the Public Health Code. **The code is now read. The negative
holds — and the interesting half is what Michigan does instead.**

---

## 1. Michigan — no licence, but a hard statutory employment bar

Source: **Public Health Code, 1978 PA 368, Article 17 (Facilities and Agencies)**,
fetched as `legislature.mi.gov/documents/mcl/pdf/mcl-368-1978-17.pdf` — 226 pages,
footer *"Complete Through PA 91 of 2026"*.

### The negative, at the statute

**MCL 333.20106(1)** defines *"Health facility or agency"* — the term Article 17's
licensure machinery attaches to — as an enumerated list of **eleven** items:

> (a) ambulance / aircraft transport / nontransport prehospital life support /
> medical first response service; (b) county medical care facility;
> (c) freestanding surgical outpatient facility; (d) health maintenance
> organization; (e) home for the aged; (f) hospital; (g) nursing home;
> (h) hospice; (i) hospice residence; (j) a facility in (a)–(g) located in an
> educational institution; (k) freestanding birth center.

**Home health agency is not in the list. Neither is home care, in-home services,
personal care, or homemaker services.** The BCHS self-description quoted in round
10 was accurate, and the enumerated definition is why.

**So Michigan does not license home health agencies and does not license
non-medical in-home care.** Confirmed at the statute, not inferred from an
agency web page.

### But Michigan defines "home health agency" anyway — via Medicare

**MCL 333.20173a** supplies its own definition:

> "**'Home health agency' means a person certified by Medicare** whose business is
> to provide to individuals in their places of residence other than in a hospital,
> nursing home, or county medical care facility 1 or more of the following
> services: nursing services, therapeutic services, social work services,
> **homemaker services**, home health [aide services]…"

**Michigan uses Medicare certification as the hook where other states use a
licence.** Same coupling family as Missouri (adopts 42 CFR 484 wholesale),
Tennessee (aide hours point at the federal competency rule) and Connecticut and
Oregon (overtime coverage by FLSA reference) — but here the federal instrument
determines **who the state rule applies to at all**, not what the rule says.

### MCL 333.20173a — the bar, and it is strict

A **"covered facility"** — expressly including a **home health agency**, alongside
nursing homes, county medical care facilities, hospice, swing-bed hospitals and
homes for the aged —

> "…**shall not employ, independently contract with, or grant clinical privileges
> to** an individual who **regularly has direct access to or provides direct
> services to** patients or residents…"

if that individual:

- **(a)** has been convicted of a **relevant crime under 42 USC 1320a-7(a)** — the
  federal healthcare-programme exclusion list, again a federal hook; or
- **(b)** has been convicted of enumerated felonies (intent to cause death or
  serious impairment; resulting in death or serious impairment; involving the use
  or threat of force or violence; and further categories), **or an attempt or
  conspiracy, or any similar state or federal crime** — *"unless **15 years** have
  lapsed since the individual completed **all** of the terms and conditions of his
  or her sentencing, parole, and probation"* before the date of application or of
  executing the independent contract.

**Three modelling points:**

1. **It reaches independent contractors and clinical privileges**, not just
   employees — the widest personnel scope in the survey.
2. **The trigger is "regularly has direct access to or provides direct
   services"**, and *"direct access"* is defined broadly at § 20173a as access to
   a patient **or to their property, financial information, medical records,
   treatment information, or any other identifying information.** An office-based
   worker with records access is inside the bar.
3. **The 15-year clock runs from completion of every term** — sentence, parole and
   probation — **not from conviction**, and it is evaluated at the date of
   application or contract execution. That is a computed date from three inputs,
   not a stored flag. Ohio's exclusionary periods and Arkansas's
   expungement/pardon escape are the same family; **Michigan's is the most
   precisely specified.**

The section also covers conditional employment, makes **knowingly providing false
information a misdemeanour**, makes **prohibited use or dissemination of criminal
history information a misdemeanour**, makes **failure to conduct the checks a
misdemeanour**, and provides for **fingerprint storage and retention,
notification, and an electronic web-based system** — i.e. a rap-back arrangement,
so the state can notify on a later arrest.

**MCL 333.20173b** gives a disqualified individual an **appeal to the department**
— so a Michigan disqualification is a contestable state, not a terminal one, the
same shape as the Massachusetts and Tennessee registry-removal petitions.

*(Note: **MCL 333.20173 itself was repealed** by 2006 PA 28 effective 2006-04-01 —
it covered nursing homes, county medical care facilities and homes for the aged.
The live provisions are 20173a and 20173b. A citation to "MCL 333.20173" is to a
repealed section.)*

### Where Michigan lands on the model

| Axis | Michigan |
|---|---|
| **A. Qualification** | **Absent** — no state training, competency or hour requirement for home health aides or in-home caregivers |
| **B. Criminal record** | **Present and strict** — § 20173a, employees + independent contractors + clinical privileges, 42 USC 1320a-7(a) plus enumerated felonies, 15-year lapse rule, criminal penalties for non-compliance, appeal under § 20173b |
| **C. Registry** | Fingerprint retention and an electronic web-based notification system (rap-back), not an adverse-findings registry |
| **D. Health screening** | Not found in Article 17 |
| **E. Supervision** | Not found in Article 17 |
| **Registration category** | **None** — the entity is defined by Medicare certification, not by a state licence |

**Michigan is Ohio's shape reached by the opposite route.** Ohio licenses home
health (skilled and nonmedical) and its chapter is *nothing but* background
checks. Michigan does not license at all and still imposes the background-check
regime — by hanging it on Medicare certification. **Two states, same axis
profile, incompatible mechanisms.** Neither a "licensed?" flag nor a
"regulated?" flag distinguishes them.

> **And a caution for the unlicensed segment.** § 20173a's bar attaches to a
> *Medicare-certified* home health agency. A Michigan **non-medical** in-home care
> business — not Medicare certified, not licensed — appears to fall outside both
> the licensure list and the covered-facility definition. **That is an inference
> from two definitions and is not verified**; Michigan's adult foster care and
> other acts were not searched. Tier 2.

---

## 2. Alabama and Mississippi — the route ledger, and why I stopped

**Both states publish their codes through LexisNexis**, and both link to it from
their own sites. That is the state's designated route, and it is JavaScript-gated.

| Attempt | Result |
|---|---|
| `alison.legislature.state.al.us/code-of-alabama` | 200, but a **1.9 KB SPA shell** with one self-referential link |
| `admincode.legislature.state.al.us` | 200, **902-byte SPA shell** |
| `alabamapublichealth.gov` (3 paths) | **200 with a "404page" body**, byte-identical — see round 10 |
| `alisondb.legislature.state.al.us/alison/codeofalabama/…` | **connection failed (000)** |
| `legislature.ms.gov` | 200; its only code links point to **`lexisnexis.com/hottopics/mscode/`** |
| `lexisnexis.com/hottopics/mscode/` | 200, **1.7 KB**, renders nothing without JS |
| `sos.ms.gov/regulation-enforcement/administrative-code` | 200, navigation only |
| `law.justia.com` (Alabama title 22) | **403** |
| `law.justia.com` (Mississippi title 41 ch. 71) | 200 with a **Cloudflare interstitial**: *"Just a moment… Enable JavaScript and cookies to continue"* |

**Stopped at nine attempts across two states**, consistent with the Arizona
precedent. Two further points recorded rather than acted on:

- **Justia is a secondary source**, so even a successful fetch would not have
  produced Tier 1 material. It was tried only to learn the chapter structure.
- **A browser could probably render all of these** — but the Arizona experience
  (Chrome loads the PDF, canvas viewer, `fetch` times out) is the reason that is
  not automatically the answer, and neither state is worth that cost ahead of the
  ~20 states not yet attempted.

**Alabama and Mississippi remain open, with the routes above already excluded.**

---

## 3. Tier 2 — reported, not independently checked

| Item | Status | Provenance |
|---|---|---|
| Whether Michigan regulates **non-medical** in-home care anywhere | **NOT ESTABLISHED — inference only** | Follows from § 20106(1) omitting it and § 20173a's definition requiring Medicare certification. Other Michigan acts not searched. |
| MCL 333.20173a subsection (2) onward (conditional employment mechanics, the full felony list, the web-based system) | **PARTIALLY READ** | The bar, the 15-year rule and the offence categories were read; the enumerated list continues past what was extracted. |
| Michigan health screening / supervision requirements | **NOT FOUND IN ART. 17** | Absence within the article read; other articles not searched. |
| Alabama Code tit. 22 ch. 21; Ala. Admin. Code ch. 420-5-6 | **NO ROUTE — nine attempts across AL and MS** | Listed above. |
| Mississippi Code § 41-71-1 et seq.; MAC Title 15 | **NO ROUTE** | Listed above. |
| LA ch. 92 Subchapters A–C; KY cross-referenced KRS; OAC 310:661; AZ AAC R9-10 | **CARRIED** | Unchanged. |
| Indiana | **ON HOLD** | Per instruction. |
| The remaining ~20 states | **NOT ATTEMPTED** | Thirty-one states touched on at least one axis is not coverage. |

## 4. Method notes

- **A negative is worth confirming at the statute even when the agency page
  already says it.** BCHS's self-description was right, but the *reason* — an
  eleven-item enumerated definition — is what makes the finding usable, and
  reading it turned up § 20173a, which changes Michigan's classification
  entirely. **"Michigan is a null case" would have been the wrong answer, reached
  from correct evidence.**
- **A repealed section still answers questions.** MCL 333.20173's repeal note
  names what it used to cover, which is how the live sections were identified.
- **When a state routes its own code to a commercial publisher, that is the
  route** — and if it is JS-gated, the state has effectively no fetchable primary
  source. Worth recording as a property of the state, not as a failure of the
  attempt.
