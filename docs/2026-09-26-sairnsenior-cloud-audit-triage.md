# SAIRNsenior's cloud audit, triaged for build-worthy findings — 2026-09-26

**Triage only. Nothing built. `sairnsenior.html` not touched — `cc-queue12` holds
it and the two EVV items are already cc's.**

**HEADLINE: the highest-value build in this audit is not in its gap list. A
caregiver whose CPR certification has EXPIRED can be assigned to a client, and
the app already knows — it renders a red "Expired" badge for that same caregiver
on another screen. The data exists, the computation exists (`certDaysUntil`), and
nothing reads either at the moment of assignment.** That is the SAIRNmechanical
G3 shape one step further along: mechanical had an engine with no caller; senior
has the computation with no caller *at the decision point*.

**And cloud's newest gap is half built.** §7.1 item 2 says visit maintenance with
reason codes *"does not exist"*; cloud's own §8 flags that finding as a **grep
floor, not a read**. Read: the **detection and the list exist** — three named
exception types, a table naming client, caregiver, date and issue. What does not
exist is any way to **resolve** one. `reason code` × 0.

Measured against `sairnsenior.html` at `1be35856`. Source:
`docs/cloud-research/sairnsenior-external-competitive-gap-audit-2026-09-26.md` on
`origin/claude/wizardly-ride-wtun13` (PR #18, unmerged).

---

## 1. THE BLOCKER CORRECTION, which is the most consequential thing in the audit

SAIRNsenior's own blocker list — in `api/_lib/sen-evv-readiness.js`'s header and
repeated in every status document since — says EVV transmission needs **"a
trading-partner agreement per aggregator"**.

**Cloud's §5.1 establishes that this is the wrong document at the wrong layer,
and it matters because it changes who has to do something.**

| | As SAIRNsenior recorded it | As cloud found it |
|---|---|---|
| The gate | a **TPA SAIRN signs** with each aggregator | **a pilot agency, per state, that names SAIRNsenior as its vendor** |
| Who acts | SAIRN, legal | **a customer**, in the state they operate in |
| Can it be pre-cleared? | in principle yes, speculatively | **no** — Colorado: vendors *"must have a sponsoring Colorado provider before access to onboarding and testing activities can be granted"*; Connecticut: the vendor *"will register for Connecticut and select one Provider Agency which has named them"*; Indiana: **the provider** emails to request vendor certification |
| What the layer actually has | — | registration, testing, certification, and for Tellus a *"Third Party Attestation"*. **No signed TPA was found at this layer at all** |

**The TPA is real but it lives one layer down**, at the 837/EDI level (§5.4),
where a Medicaid trading partner may be *"any Provider, billing service, software
vendor, … clearinghouse"* and the shape is one submitter ID with providers
registered under it. **Which is why every competitor in cloud's §2 names a
clearinghouse rather than direct state connections** — the clearinghouse route
absorbs the per-state TPA work.

### 1.1 Three consequences, and the third is a correction to our own sequencing

1. **Blocker (a) is a go-to-market dependency, not a legal one.** It cannot be
   worked on in advance by anybody in this repo.
2. **The first state is chosen by where the first Medicaid customer is**, not by
   which spec is cleanest. The 2026-08-27 groundwork ranked NY, LA and TX **by
   spec quality**; cloud is explicit that *"ranking still holds for learning, but
   not for sequencing."*
3. **Certification is once per vendor per state, and later agencies are add-ons**
   — Ohio from 2021-09-15 requires *"only … new vendors to pass certification"*,
   Pennsylvania says *"vendors can pass certification by testing successfully with
   one agency account."* So the cost curve is front-loaded per state and flat
   after. **First-agency timelines: Wisconsin says allow up to three months and
   the provider cannot record EVV meanwhile; Netsmart says 6–8 weeks.**

**Unresolved and kept rather than reconciled** (cloud's own list): Ohio
certification per vendor vs per Medicaid ID; Sandata production credentials going
to the vendor in CT and *"to providers only"* in PA.

### 1.2 And the credential-custody decision now has three named market models

Directly relevant to the open credential-storage decision, and this is
**information for it, not the decision**:

| Model | Who holds it | Seen at |
|---|---|---|
| Agency obtains credentials and enters them in the vendor's software | agency | **Sandata norm** — Axxess, ShiftCare |
| Agency generates a **delegated, revocable** credential in the aggregator portal | agency, revocable | **HHAeXchange** OAuth2 client id/secret; providers can add and remove sets |
| One **vendor-level** credential, each agency's data in a separate file | vendor | **CareBridge** SFTP |

**The market norm is the hardest one for us**: SAIRN would hold **per-tenant
secrets entered by the agency**, on a platform whose tenants share one backend.
**HHAeXchange's revocable agency-generated credential is the safest shape to copy
where it is offered**, and CareBridge's vendor-level model is the easy exception.
No state guidance on how a vendor must store per-agency credentials — encryption,
rotation — was found at all.

**Cross-reference, because it is the same decision twice:** this is the identical
question `docs/2026-09-26-tier2-clearinghouse-engagement-scoping.md` §5 raises for
the clearinghouse key, and the answer there was blocked on
**`SD_ENCRYPTION_KEY` not being set**. One environment variable gates both.

### 1.3 On fees — and one number that must not be repeated

Mostly no charge at the aggregator (CareBridge, HHAeXchange MN, Alora on
Florida); costs pushed to the provider or vendor in Ohio, Wisconsin and
California. **Cloud explicitly refuses the figure "$3,360"** — one summariser
answer attributed it to no single source and neither the state nor the currency is
known. **Do not quote it.** Only one competitor discloses a pass-through fee
(Generations, $25/month plus per-visit verification fees).

**The real cost is engineering and support time per state, not fees.**

---

## 2. BUILD-WORTHY, ORDERED — and item 1 is not in cloud's gap list

### PRIORITY 1 — Assignment does not check whether a caregiver's certification is current

**NEW IN THIS TRIAGE.** Cloud's §7.3 lists *"scheduling gated on caregiver
credentials"* as a candidate it **recorded but did not investigate**, with a note
to *"check before claiming"* and a pointer to the SAIRNmechanical 09-17
precedent. Checked:

- **The data exists.** `cpr_expiry` and `bgcheck_date` are stored per caregiver
  and editable (`:2564`, `:2574`).
- **The computation exists.** `certDaysUntil()` drives two dashboard KPIs — *Certs
  Expiring (30d)* and *Certs Expired* — and renders a per-caregiver badge:
  `days<0` → **red "Expired"**, `days<=30` → amber (`:2592-2593`).
- **The assignment path does not read either.** `assigned_employee_id` is written
  at `:2342` and `:2355` with no certification check anywhere near it, and a
  scoped search for any scheduling line mentioning training, cert or credential
  returns **nothing**.

**So an agency can assign a caregiver with a lapsed CPR to a client, and the same
app will show that caregiver as "Expired" on the compliance screen.** Two screens,
two answers, no disagreement flagged.

**Why this is first:**
- **It is the smallest real build in the list.** No aggregator, no state, no
  vendor, no statute to date — the inputs and the arithmetic are already in the
  file.
- **It has a working platform precedent to copy, not invent.**
  SAIRNmechanical's `evaluateEligibility()` + the 2026-09-17 caller fix is this
  exact shape, and its own comment records the trap: *"WHAT THIS IS NOT: a gate.
  Nothing here refuses a dispatch"* — i.e. **surface the answer, do not silently
  refuse the assignment.** That is the right posture here too; a hard refusal
  would block an agency covering a shift in an emergency.
- **Cloud's §4.2 gives it external weight**: a New Mexico OIG finding, and
  Colorado's OIG faulting units paid above approved.

**Named limits before anybody builds it:** `cpr_expiry` is ONE certification.
Real HCBS credentialing is several (TB, background check re-run, state-specific
training hours), and `sen_training_records` / `sen_training_rules` exist as
separate resources that this KPI does not read. **Gate on what is recorded and
say what is not gated** — the alternative is a green light that means less than it
looks.

### PRIORITY 2 — Visit maintenance: detection is BUILT, resolution is not

Cloud's §7.1 item 2 calls this *"new in this pass"* and says it **does not
exist**. Its §8 correctly labels that a grep floor. Read:

**What exists** (`:5482-5504`): an exception detector with three concrete types —
clocked in and never clocked out, no GPS on clock-in, no GPS on clock-out — an
**EVV Exceptions** KPI, and a **table** naming client, caregiver, date and the
specific issue. That is the detection half, and it is real.

**What does not exist:** any way to resolve one. `reason code` × 0, `visit
maintenance` × 0. No edit, no reason, no record of who corrected what and when.
So the panel is a list of problems with no action beside them — the *"a count with
no list behind it"* shape this platform keeps finding, one step better (there IS a
list) and still short of useful.

**This is cc's.** `cc-queue12` holds *"SAIRNsenior visit time correction with
reason code (VERIFY first)"*, which is this gap. **The verification cc was told to
do is the finding above: build the resolution onto the existing detector rather
than building a detector.** Recorded here so cc does not start from cloud's "does
not exist".

**Cloud's framing to keep:** exception resolution is *"a prerequisite of
transmission, not a follow-on"* — Pennsylvania regulates the edit rate and
Colorado's OIG reportedly faulted unreviewed exceptions.

### PRIORITY 3 — Per-state EVV quality reporting, and a metric distinction cloud's ordering hides

Cloud's §7.1 item 5: *"per-state, per-quarter EVV quality reporting against the
state threshold. New in this pass, and the one EVV item that does not need
transmission"* — but *"needs item 2 first to compute an edit rate."*

**Half of that is already available and half is genuinely blocked, and they are
different metrics:**

- **EVV Completion (30d) already exists** (`:5481`) — completed visits over
  scheduled visits in the last 30 days, and it correctly shows `--` when the
  range is empty rather than 0%.
- **An EDIT RATE does not and cannot yet**, because nothing records an edit. Its
  numerator is created by Priority 2, not measured by this item.

**Do not treat completion as the edit rate.** They are different numerators
against different denominators, and a state threshold written for one is not a
threshold for the other. **This item is genuinely behind Priority 2** — but the
completion half being live means the reporting *surface* can be scoped now.

### PRIORITY 4 — Telephony (A2's second half): unchanged, still vendor-gated

`telephony` × 2, and both are **comments** explaining why a phone system is still
needed for rural and no-signal visits. Openly claimed by Alora, WellSky and
MatrixCare. **Needs a telephony provider**; nothing to build first.

### PRIORITY 5 — 837 / clearinghouse (A4): already scoped, and cloud sharpens it

Covered by `docs/2026-09-26-tier2-clearinghouse-engagement-scoping.md`. **Two
things cloud adds:**
1. **In claim-embedded states — Washington, and Virginia FFS if the snippet holds
   — A4 and A1 are the same gap.** The clearinghouse work and the EVV work
   collapse into one there.
2. **Billing is where 7 of 10 products draw complaints**, which is an opening and
   a requirement at once.

---

## 3. NOT BUILD-WORTHY YET, and why each is held

- **80/20 compensation-share reporting.** Cloud: *"Do not build until the
  rescission question resolves"*, and it does not know whether CMS-2442-F was
  rescinded by 2026-09-26. Reporting window 2027–2030. **And SAIRNsenior's
  refusal of the B5 profit figure is still correct** — if 80/20 survives, the
  compensation share becomes a *reported* number, and a number this app invented
  would be worse than none.
- **Open-shift broadcast / shift-fill matching.** `open shift` × 0. A real
  feature, no regulatory forcing function, and no evidence in this audit that it
  is why anybody switches.
- **Tasks-against-plan-of-care.** `plan of care` × 0. Kansas OIG cited. **Needs
  the plan of care to exist as an object first**, which it does not.
- **Device-vs-server time signal.** `device time` × 0, `server time` × 0. This is
  cc's other item (*"clock-in server-side check"*), and `api/_lib/sen-evv-clock.js`
  exists, so start by reading that rather than from cloud's grep.

---

## 4. Where SAIRNsenior is on the right side, and should say so

Worth carrying into any sales conversation, and all five are already true:

- **`state_rules: 'not_verified'`** — cloud calls this *"the KanTime-style honesty
  the market rarely shows."*
- **Offline replay-unchanged** — addresses *the most repeated caregiver complaint*
  in cloud's practitioner lens, which lands on **the aggregators' own apps**.
- **Point-in-time location with the refusal disclosed** — the privacy posture the
  advocates in §4.3 argue for.
- **Authorization unit burn-down** — directly on Colorado's OIG finding of units
  paid above approved.
- **The refused profit figure (B5).**

---

## 5. What this triage did NOT do

- **It did not touch `sairnsenior.html`.** cc holds it and two of the five items
  are cc's.
- **It verified no external claim.** Every competitor, state, timeline, OIG
  finding, case and fee above is cloud's, and cloud's §0.1 states that **every
  external claim is `[SNIPPET]` and none is OPENED.** Nothing here is quotable to
  a customer or a state.
- **It did not resolve cloud's fourteen kept conflicts** — Ohio certification
  scope, Sandata credential destination, the Virginia live-in exemption, Wisconsin
  Sandata-mandatory-vs-open, Maryland closed-vs-integrate, and the rest. They are
  correctly kept rather than reconciled.
- **It did not read `sairnsenior.html` end to end.** Priority 1's three facts and
  Priority 2's two are targeted reads; the rest of §2 is marker counts, which are
  a floor.
- **It did not measure how many caregivers currently have a lapsed cert**, which
  is the number that would tell anybody how urgent Priority 1 is. That needs real
  tenant data, not a grep.

## 6. Decay

Cloud's document is a snapshot of blocked-egress snippets on 2026-09-26 and says
so. This triage is greps and targeted reads at `1be35856` against a file cc is
actively editing — **Priority 2 and the device-time item are cc's and may have
moved by the time this is read.** Re-measure before acting.
