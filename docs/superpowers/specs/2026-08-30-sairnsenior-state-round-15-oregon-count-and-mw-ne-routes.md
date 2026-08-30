# SAIRNsenior — round 15: Oregon's real intermediary count, and the Mountain West / New England route ledger

2026-08-30. **Research only.** Nineteenth document in the series.

---

## 1. Oregon has ONE caregiver-matching category, not three

Round 14 flagged **ORS 443.360** and **ORS 443.370–443.376** as possible extra
intermediary categories and said *"Oregon may have three, not one."* **Read: it
does not.** The count stays at **three states** with a caregiver-matching
intermediary category — Iowa, Colorado, Oregon.

**This is the same over-count as the Nevada "referral agency" error, caught
before it hardened.** Both times a section *name* suggested a category; both
times the definition said otherwise. The difference is that this one was checked
in the round it was raised.

### ORS 443.370–443.376 — "long term care referral" is FACILITY placement

Every operative phrase is about facilities, not caregivers: *"refer a client to a
**facility**"*, *"the length of any contract the referral agent has with a
**facility** regarding placement information"*, *"whether the referral agent
provides referrals **only to facilities** with which the agent has an existing
contract."*

**It is the same business as Nevada's referral agency** — steering clients into
assisted living or other long-term-care facilities — and is **not** an analogue
of Iowa's platform, Colorado's placement agency or Oregon's own caregiver
registry.

**Recorded anyway, because it would bind a "help me find a facility" feature.**
ORS 443.373: no one may provide a long term care referral without **registering
with the Department of Human Services**; **$750 fee**; **renewal every two
years** (renewal capped at $750); the applicant must identify a responsible
individual, demonstrate compliance with ORS 443.376, **maintain at least
$1,000,000 in general liability insurance**, and **perform background checks on
referral agents who have direct contact with clients**. Civil penalties apply.

ORS 443.376 then imposes a **pre-referral disclosure** — which may be oral **only
if audio-recorded with the client's consent** and followed by a written version —
that must be conspicuous and in clear language and state: a description of the
referral **including the length of any contract the agent holds with a facility**
regarding the client's placement information; the agent's contact details; **the
agent's privacy policy**; **whether the agent refers only to facilities it has
contracts with**; and **whether the facility pays the referral fee**.

Prohibitions worth carrying:

- **may not share or sell a client's placement information to a facility or
  marketing affiliate "without obtaining affirmative consent from the client
  **for each instance** of sharing or selling"** — per-instance consent, not a
  one-time authorisation;
- may not refer to a facility in which the agent **or an immediate family member**
  has an ownership interest;
- may not contact a client who has asked **in writing** to stop;
- if the agent maintains a website it **must link to the state agency website
  listing complaints concerning facilities**; if not, clients must be notified in
  writing.

> **The per-instance consent rule is the transferable part.** It is a data-sharing
> constraint of a kind nothing else in this survey has produced, and it would
> apply to any lead-routing or partner-referral feature.

### ORS 443.360 — "agency with choice services" is a contracted programme, not a category

Enacted by **2024 c.37** and, like ORS 443.190/443.195, **law that was never
codified into chapter 443's series** — the same editor's note applies.

It is not an open licensing category. *"The Oregon Health Authority and the
Department of Human Services **shall contract with up to two agencies** to
provide agency with choice services … no later than January 1, 2026."*

**A state-procured, self-directed service-delivery model limited to two
contracted providers.** Expansion is staged: after two years of operation serving
medical-assistance recipients, DHS may extend it to Oregon Project Independence
clients (ORS 410.430–410.450), and the **Home Care Commission** (ORS 410.602) may
extend it to the private-pay home care worker programme (ORS 410.605) — but only
after a stakeholder group analyses the data.

**Not something a vendor or agency can register for. Not an intermediary
category.** Worth knowing only because "agency with choice" is a real
self-direction model SAIRNsenior might encounter in Oregon, alongside Nevada's
client-as-managing-employer branch.

---

## 2. Mountain West and New England — route ledger

Index-first probes, bodies checked (not status codes):

| State | Host tried | Result |
|---|---|---|
| Montana | `rules.mt.gov/browse/collections/1` | 200, **13 characters** of body — *"Montana SOS"*. SPA shell. |
| Idaho | `adminrules.idaho.gov/rules/current/16/` | 404, and the page states the site is *"experiencing a temporary technical issue affecting document search and listings"* — **a state-side outage, not a block.** Worth retrying rather than routing around. |
| Wyoming | `rules.wyo.gov/Default.aspx` | 200, chrome only, plus a scheduled-maintenance notice. |
| New Mexico | `srca.nm.gov/nmac-home/` | 200, 4.4 KB of navigation. NMAC index not yet walked. |
| New Hampshire | `gencourt.state.nh.us/rsa/html/NHTOC/NHTOC-X-151.htm` | **404** — guessed path. |
| Maine | `legislature.maine.gov/statutes/22/title22ch1666-Asec0.html` | 200 — **and it is a real statute page**, but the chapter I guessed is *Appointment of Receivers*, not home care. **Wrong citation, right host.** |
| Vermont | `legislature.vermont.gov/statutes/chapter/33/071` | 200, 7 KB — Human Services title loads. Chapter not yet identified. |
| Rhode Island | `rules.sos.ri.gov/organizations/216` | **404** — guessed organisation id. |

**Two working hosts identified** (`legislature.maine.gov`,
`legislature.vermont.gov`) and **one confirmed transient failure** (Idaho).
**Nothing substantive read.** Every failure above is a **guessed path**, which is
the exact habit five earlier states already taught me to drop — the index-first
rule was applied to *choosing the host* but not to *choosing the path within it*.

**Next step for these eight, stated so it is not re-derived:** fetch each host's
statute/rule **table of contents** and read the section titles, rather than
constructing a citation. That is what worked for South Carolina, Tennessee,
Colorado, Oklahoma, Louisiana and Oregon.

---

## 3. Tier 2

| Item | Status |
|---|---|
| Oregon OARs implementing ORS 443.105 | **NO ROUTE** — OARD bot-walled. |
| ORS 443.090, 443.095, 443.305–443.350 (in-home care agency licensing) | **NOT READ** — only the index surveyed. |
| ORS 410.430–410.450, 410.602, 410.605 | **NOT READ** — cross-referenced by 443.360. |
| Montana, Idaho, Wyoming, New Mexico, New Hampshire, Rhode Island | **NO ROUTE YET** — see ledger. |
| Maine, Vermont | **HOST FOUND, CHAPTER NOT IDENTIFIED** |
| Alabama, Mississippi, Utah, Connecticut, Kansas | **NO ROUTE** — carried. |
| Indiana | **ON HOLD** — per instruction. |
| The remaining states | **NOT ATTEMPTED** — thirty-four touched is not coverage. |

## 4. Method notes

- **Two over-counts in two rounds, one caught late and one caught immediately.**
  Nevada's referral agency hardened into a published table before the definition
  was read; Oregon's was checked in the round it was raised. The rule earning its
  place: **a category is not counted until its definition has been read.**
- **A facility-referral category and a caregiver-matching category look identical
  from the index.** Nevada and Oregon each have one of each. Only the definition
  separates them.
- **Index-first applies to the path, not just the host.** Every failure in § 2 is
  a path I invented after correctly identifying the publisher.
- **Distinguish a site outage from a block.** Idaho says outright that its search
  and listings are broken. That is a retry, not a workaround.
