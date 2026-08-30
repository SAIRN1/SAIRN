# SAIRNsenior — round 20: North Dakota opened, and Nebraska's two open flags closed

2026-08-30. **Research only.** Twenty-eighth document in the series.

Treating the six remaining states **by their diagnosed shape** worked on three of
them and produced a further diagnosis on the rest. **Nebraska's two flagged
questions are both answered**, and one of the answers reverses what the section
list implied.

---

## 1. Nebraska — the hour figure exists, and the sequencing is the interesting part

**§ 71-6608.01, Home health aide training course; standards:**

> "(1) Such course shall address each of the following subject areas through
> classroom and supervised practical training **totaling at least seventy-five
> hours**, with **at least sixteen hours devoted to supervised practical training
> *after* the individual being trained has completed at least sixteen hours of
> classroom training**…"

Subjects: communication skills; observation, reporting and documentation of
patient status and the care furnished; **reading and recording temperature, pulse
and respiration**; basic infection control; basic body functioning and changes
that must be reported to the supervisor; maintaining a clean, safe and healthy
environment; recognising emergencies and emergency procedures; and the physical,
emotional and developmental needs of the populations served, including respect
for the patient and their privacy.

> **A seventh hour-denominated state — and the first with an explicit
> *sequencing* rule.** Texas requires ≥16 classroom **before** clinical;
> Nebraska requires ≥16 classroom **before** the ≥16 supervised practical, inside
> a 75-hour total. **Arkansas nests (40 ⊃ 16 ⊃ 4); Nebraska orders.** A model
> holding `{total: 75, practical: 16}` still cannot express *"the practical hours
> must come after sixteen classroom hours."*

## 2. Nebraska — and the licensure question answers itself in the applicability section

**§ 71-6504, Sections; applicability:**

> "Sections 71-6501 to 71-6503 **do not apply** to the performance of health
> maintenance activities by **designated care aides** pursuant to section
> 38-2219, or to persons who provide **personal assistant services, respite care
> or habilitation services, or aged and disabled services**."

**§ 71-6501(6) defines the regulated entity:**

> "'**In-home personal services agency**' means an entity that **provides or
> offers to provide** in-home personal services for compensation **by employees
> of the agency or by persons with whom the agency has contracted** to provide
> such services."

**Answering the flag I raised in round 19:** the whole scheme is
**§§ 71-6501–71-6504 — four sections, and none of them is a licensure
requirement.** Nebraska imposes **statutory worker qualifications and agency
duties without licensing the agency**, on the text read. *(Stated as a reading of
those four sections; whether "in-home personal services agency" appears among the
licensed facility types in the Health Care Facility Licensure Act (§ 71-401 et
seq.) was **not** separately verified.)*

**Three things worth carrying from these two sections:**

1. **"Provides *or offers to provide*"** — Nebraska uses the same *offers*
   language that made Rhode Island's trigger the widest in the survey. **But the
   consequence differs completely:** in RI it pulls you into a licence; in
   Nebraska it pulls you into worker-qualification duties with no licence
   attached.
2. **"by employees of the agency **or by persons with whom the agency has
   contracted**"** — contractors are expressly contemplated in the definition
   itself. **Reclassification check: clean**, consistent with round 19.
3. **The applicability carve-out is a payer/programme carve-out.** Personal
   assistant services, respite, habilitation and aged-and-disabled services —
   the Medicaid-waiver family — are **outside** §§ 71-6501–71-6503 entirely. So a
   Nebraska agency's obligations differ **by programme**, within one workforce.
   The same per-client-by-payer shape as Arkansas's DHS exemption.

**Definitions to carry (§ 71-6501):** *attendant services* (hands-on ADL
assistance, transfer, grooming, bathing, **medication reminders**);
*companion services* (companionship, letter writing, reading); *homemaker
services* (housekeeping, personal laundry, shopping, **incidental
transportation**, meals); and *in-home personal services* as those three
**"that do not require the exercise of medical or nursing judgment."**

---

## 3. North Dakota — opened, and my diagnosis was half right

Round 19 diagnosed the `300 Multiple Choices` as **a wrong filename the server
itself flagged**. **Correct — but incomplete.** The 300 was *content
negotiation*: the same chapter exists as **`.pdf`**, and requesting
`t23c17-5.pdf` returned it immediately.

**And the chapter was the wrong one anyway.** `23-17.5` is
*"HEALTH CARE PROVIDER COOPERATIVE AGREEMENTS [Repealed by S.L. 2013, ch. 35,
§ 10]"* — **a fifth repealed chapter in this survey.**

**The right chapter came from the title index**, as it has in every state that
worked: **NDCC ch. 23-17.3, "Home Health Agency Licensure."**

> "'**Home health agency**' means a public or private agency, organization,
> facility, or subdivision thereof which is engaged in providing **home health
> services to individuals and families where they are presently residing** for
> the purpose of preventing disease and promoting, maintaining, or restoring
> health…"

Also defined at § 23-17.3-01: *allowed practitioner* (physician assistant or
APRN) and *clinical record* — which must cover services provided **directly and
through arrangements with another agency**, and contain past and current medical,
nursing, social and other therapeutic information **including the plan of
treatment**.

**Reclassification check: clean** — zero hits across the chapter.

**Two lessons compounded here:** a `300` can be content negotiation rather than a
dead end, **and** solving the route does not mean you have the right chapter. The
title index was still required.

---

## 4. The remaining five, re-diagnosed

| State | Round 19 diagnosis | Now |
|---|---|---|
| **North Dakota** | wrong filename, server-flagged | **OPENED** — `.pdf` extension; chapter found via the title index. |
| **Delaware** | my parser | **Parser fixed** — 143 chapters extracted. **But no home-health or home-care chapter is among them**; the nearest are ch. 10 *Hospitals*, ch. 11 *Long-Term Care Facilities and Services*, ch. 30A *Training and Certification Requirements for Certain Nurse Assistants*. Ch. 11's own index returned 1.1 KB and needs a further level. **Route works; chapter not yet identified.** |
| **Hawaii** | my parser | **Parser fixed** — the IIS listing uses uppercase `<A HREF=` and yields per-section files (`HRS_0321-NNNN.htm`). **Route works; the relevant sections not yet identified.** |
| **West Virginia** | my path | **Still wrong.** `code.wvlegislature.gov/16-5D/` and `/16-5D-1/` both return the **whole-code chapter navigation**, not article text. A different URL form is needed. |
| **Alaska** | self-declared move | **Not yet followed.** `akleg.gov/basis/statutes.asp` says *"This page is no longer used please use …"*; the pointer was not read. |
| **South Dakota** | genuine SPA | **Confirmed SPA.** `sdlegislature.gov/api/Statutes/Chapter/34-12` returned the same 2,256-byte shell, so that guessed API path is not the endpoint either. |

**Three of six now open** (Nebraska, North Dakota, plus the two parser fixes that
work but need a chapter). **Recorded per-state rather than as a batch**, which is
what let the North Dakota fix be a one-line change.

---

## 5. Tier 2

| Item | Status |
|---|---|
| Nebraska: whether "in-home personal services agency" is a licensed facility type under § 71-401 et seq. | **NOT SEPARATELY VERIFIED** — the four-section scheme contains no licensure requirement, which is a different claim. |
| Neb. §§ 71-6608.02, 71-6039, 71-417, 71-6602; Title 175 NAC | **NOT READ** |
| ND ch. 23-17.3 beyond § 01 definitions; ND admin rules | **NOT READ** |
| DE home-care chapter; HI relevant HRS 321 sections | **ROUTE OPEN, CHAPTER NOT IDENTIFIED** |
| WV art. 16-5D | **PATH STILL WRONG** |
| AK new statutes location | **POINTER NOT FOLLOWED** |
| SD | **SPA — no endpoint found** |
| AL, MS, UT, CT, KS | **NO ROUTE** — carried. |
| ID | **CLOSED** |
| IN | **ON HOLD** |

## 6. Method notes

- **A `300 Multiple Choices` is content negotiation, not necessarily an error.**
  North Dakota's server was offering the same document under a different
  extension.
- **Opening the route is not finding the chapter.** North Dakota's route worked
  on the first retry and still delivered a repealed chapter about the wrong
  subject. **The title index remained necessary** — five states in a row now.
- **The reclassification check ran on both new states at read time**, per the
  standing practice, and both are clean. Two commands total.
- **Per-state diagnosis paid off immediately.** The North Dakota fix was a
  file extension; had it been batched with South Dakota's SPA, it would have
  looked like the same intractable problem.
