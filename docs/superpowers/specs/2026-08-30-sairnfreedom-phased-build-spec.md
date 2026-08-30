# SAIRNfreedom — phased build spec

**Written 2026-08-30 (CC). This is a SYNTHESIS, not new research.** Everything
statutory here traces to
`docs/superpowers/specs/2026-08-30-sairnfreedom-research.md` (canonical) and its
two appendices. Feature scope comes from the expanded deep-dive list. Where a
feature arrived as a *name* without detail, it is listed in **§9 Needs source
detail** rather than guessed at.

**Status: nothing built. No schema, no app file, no API branch.**

---

## 1. The two structural decisions everything else hangs off

### 1a. Capability-based permissions, with officer titles as a per-org-type MAPPING

The named officer structure — **Commander, Vice Commander, Adjutant, Finance
Officer, Chaplain, Judge Advocate, Historian, Service Officer,
Sergeant-at-Arms** — is the basis of the permissions model, as directed. But it
must not be the *enum*.

**Reason, and it is the same lesson the statutory research already forced:** the
verified finding in the canonical doc is that ORC 2915.01 gives veteran's
organisations **(V)(2)** and fraternal organisations **(V)(3)** different
charitable-purpose tests inside one state. Organisation type is already a
first-class axis of this product. **Officer titles vary on that same axis** — a
VFW post's finance officer is the *Quartermaster*; Elks and Moose use different
titles again. Hardcoding one vocabulary produces a product that is wrong for
three of the five target orders in exactly the way a shared `charitable_purpose`
enum would have been.

**So:** `capability` is the stable thing; `officer_title` is display and is
mapped per `org_type`.

| Capability | Held by (Legion/VFW vocabulary given) | Notes |
|---|---|---|
| `post.govern` | Commander | Sole holder. The "last active provisioner" role |
| `post.govern.deputy` | Vice Commander | Acts when Commander unavailable — this is the recovery path, see §1c |
| `records.write` | Adjutant | Minutes, roster, membership records |
| `finance.write` | Finance Officer (VFW: Quartermaster) | **Bonded.** Personally responsible for post funds |
| `finance.approve` | Commander + Finance Officer | Two-party. See §4 |
| `gaming.operate` | designated bingo workers | **Cannot be compensated** — ORC 2915.09(D)(1) |
| `gaming.report` | Finance Officer | Owns the 2915.10 record set |
| `canteen.operate` | bar staff | Shift-scoped, not officer-scoped |
| `canteen.close` | Canteen manager + Finance Officer | Nightly reconciliation |
| `member.admit` | Adjutant | |
| `services.refer` | Service Officer | **See §9 — regulated, research first** |
| `ceremonial.manage` | Sergeant-at-Arms | Honor guard equipment, details |
| `history.write` | Historian | |
| `legal.review` | Judge Advocate | Bylaws, disputes |
| `chaplain.pastoral` | Chaplain | Likely no data capability at all — confirm |

**Reuse, do not reinvent:** `sairn-employee-auth-scaffold` already ships PIN
credentials, signed session tokens, lockout and the credential-deactivation
lifecycle across thirteen apps. The officer model is a role vocabulary on top of
`api/_lib/auth.js`, not a new auth system.

### 1b. Tenancy: the auxiliary distinction is a schema decision, not a UI one

- **Sons of the American Legion (S.A.L.)** — a **sub-category of the same
  entity**. Same licence, same treasury, same tenant. Model as a
  `member_category`, not a separate post.
- **Auxiliary / Women of the Moose** — **genuinely separate, co-located legal
  entities.** Own treasury, own officers, own reporting. Model as a **separate
  tenant** that shares a physical location.

**Getting this wrong is unrecoverable in the direction of merging.** Two entities
merged into one tenant means one treasury where the law expects two, and
un-merging afterwards means re-attributing every historical transaction. The
canonical research already establishes each post is independently governed and
independently licensed; the auxiliary is the same fact one level down.

**Consequence:** `location` and `entity` are different keys from day one, and the
district rollup (§7) aggregates *entities*, not buildings.

### 1c. The provisioning trapdoor — design it in, do not discover it

The platform already has a live failure of this shape: a licence with credential
rows and **zero rows that are both active and hold a provisioning role** is
unrecoverable through the API. RF-PINNACLE-2026 sat in that state and nothing
noticed.

A post whose only `post.govern` holder is deactivated is the same trapdoor.
`post.govern.deputy` exists partly to prevent it. `tools/employee_auth_guard_check.py`
already enforces the two safe end states — zero rows, or at least one active
provisioner — and any SAIRNfreedom credential SQL must carry that guard.

### 1d. Banner: animated app-wide, static on onboarding — DECISION 2026-08-30

**This supersedes the earlier "static everywhere" branding call.**

- **Animated flag banner, consistently, on the dashboard and every other page.**
  One banner component, one behaviour, everywhere. An animation that appears on
  some pages and not others reads as a bug, not a choice.
- **Onboarding is the exception and is STATIC.** The one place a new member is
  being asked to concentrate is the one place the banner does not move.

**The constraint that produced the earlier call still stands and is why this is
recorded rather than just changed.** Animated distortion was previously
attempted and rejected as visually broken — it read as water or TV static — and
the guidance was to avoid canvas/SVG turbulence-filter animation on a working
dashboard. **That failure was a bad implementation, not a bad idea.** The
decision now is that it gets built properly, by an agent, as real work — not
attempted again in a quick mockup tool.

**So the prohibition that survives is on the technique, not the effect:** do not
reach for turbulence filters and call it done. Whatever is built must be
reviewed against `sairn-visual-review` on a rendered page at real size before it
is called finished, because the last attempt looked fine in source and wrong on
screen.

**Still holds, unchanged:** no literal reproduction of the American flag —
trademark/copyright caution — so this is a red/white/blue diagonal-stripe motif
with a small star cluster, not a flag.

---

## 2. Phase 1 — Foundation (no dependencies; everything else needs this)

| # | Feature | Notes |
|---|---|---|
| 1.1 | Entity + org_type + licence model | `org_type` drives §1a titles AND the §5 charitable categories |
| 1.2 | Officer roles / capability model | §1a. On `sairn-employee-auth-scaffold` |
| 1.3 | Member roster, categories, S.A.L. sub-category | §1b |
| 1.4 | Dues, renewal, **three-layer fee structure** | **§9 — structure named, not defined** |
| 1.5 | Conditional dues/fee waivers | **§9 — conditions not defined.** Note: waiver eligibility is a governance decision with audit implications, not a discount code |
| 1.6 | Post profile: licence types, **15-year test** for fraternal orgs | OAC 109:1-4-08 Types I/II/III gate lawful activity; ORC 2915.01(V)(3) 15-years-continuous-existence gates fraternal disbursement eligibility |
| 1.7 | Branding shell | Red/white/blue, **diagonal** stripe, small star cluster, no literal flag reproduction. Post name + org type + city in header. **ANIMATED banner across the whole app — see §1d** |

**Phase 1 exit criterion:** a real post can be created, its officers provisioned,
its members enrolled and dues taken — and the app knows its org type, licence
types and eligibility facts, because everything downstream branches on those.

---

## 3. Phase 2 — Canteen and events (depends on 1.1–1.3, 1.7)

| # | Feature | Notes |
|---|---|---|
| 2.1 | In-house POS: bar + kitchen | **Stripe/Square for payment rails only** — the POS is SAIRN's. This is the pillar Arrow's Tab King already ships; see the competitive doc |
| 2.2 | Nightly shift close-out + cash reconciliation | Feeds §4. VFW's own materials: trustees are **required** to physically inventory canteen liquor regularly |
| 2.3 | Bottle fill-level estimation | **AUTOMATIC determination only.** Binding decision, patent-avoidance. No slider, no tap-to-set, no adjustable guess. See canonical doc *Binding decisions* |
| 2.4 | Lodge events + live-music calendar | Public-facing side of the same calendar the gaming module constrains |
| 2.5 | Hall rental | Weekday/weekend rates, member vs public tier, **larger damage deposit for alcohol-serving events** |
| 2.6 | Vendor/supplier management | Gaming supplies, alcohol, food, entertainment bookings |
| 2.7 | AI vendor price search | **§9 — scope undefined.** Grounding and citation discipline required before build |

**Dependency note:** 2.4 must be built as one calendar with the Phase 3 gaming
constraints, not a second calendar bolted alongside. See §4.

---

## 4. Phase 3 — Gaming compliance and the money model (depends on Phase 1; interlocks with Phase 2)

**This is the regulated core and the actual moat.** Build order inside the phase
matters.

| # | Feature | Notes |
|---|---|---|
| 3.1 | **Bingo account as a first-class entity** | ORC 2915.10(C): **gross profit** — receipts *minus prizes* — into an account **devoted exclusively** to the session; expenses and distributions paid **only** from it |
| 3.2 | Separate **electronic instant bingo** account | Ohio AG requirement, distinct money type, **quarterly reports due Feb 28 / May 31 / Aug 31 / Nov 30** |
| 3.3 | Session model + calendar **constraint enforcement** | Max **3 sessions per 7 days**; **$6,000** prize cap per session; **no sessions 2 a.m.–10 a.m.** (instant sales may begin 9 a.m. for a 10 a.m. session). Session = 5 continuous hours + 2-hour instant windows either side — and per the canonical doc this is a **definition**, not a rule: anything longer is *not a session*, and every per-session calculation keys to nothing |
| 3.4 | Profit chain | receipts − prizes = gross profit; − expenses = net profit. `(GG)(11)` makes canteen cost an allowable expense **paid out of the segregated account** |
| 3.5 | 2915.10(A) record set | By game type; itemised expenses with payee; prize list; participant count; **food and beverage sales AND expenses**; 3-year retention; supply inventory **due Nov 1**; AG notified of where records are kept |
| 3.6 | Operator eligibility | Under-18 barred; felony/gambling conviction barred; **no compensation of any kind** to operators — interacts with paid canteen staff |

**PII gate before 3.5 exists as a table:** 2915.10(A)(3) requires storing winner
**Social Security numbers** for prizes ≥ $600. Encryption, access role and
retention must be decided **before** the column exists, not retrofitted.

---

## 5. Phase 4 — Disbursement, donations and outreach (depends on Phase 3)

| # | Feature | Notes |
|---|---|---|
| 4.1 | Disbursement log, **two independent taxonomies** | `ohio_charitable_purpose` (conditioned on org_type — **(V)(2) veteran's list vs (V)(3) fraternal list are different lists**) and `national_program_category`. Neither derives from the other |
| 4.2 | Instant-bingo tiered distribution engine | 2915.101: ≥25% on the first $250,000, ≥50% above, 5% own-purpose allowance. **Cumulative annual running total**, calendar year, and the threshold is *"or adjusted amount"* — configuration, never a constant |
| 4.3 | Disbursement record fields | `funding_source` (gaming net profit vs general), `game_type`, `disbursement_direction` (given away vs cost-to-post). Per the appendix: the CPR's ~15 "cost to post for X" fields are legitimate nationally and are **not** permitted (V)(2) destinations |
| 4.4 | Donations received + **automatic emailed tax receipts** | Reuse the platform's Resend integration — **`RESEND_FROM_EMAIL`**, not `RESEND_FROM_ADDRESS`, which has never existed here and silently broke two apps |
| 4.5 | Donor-tier recognition | **§9 — tiers not defined** |
| 4.6 | AI-directed community outreach tied to disbursement categories | Must propose only within the org's *own* legal category set. An outreach suggestion outside (V)(2)/(V)(3) is a compliance hazard dressed as marketing |
| 4.7 | Volunteer / service-hour tracking | Full schema implications in the service-hour appendix. **Decimal hours** (5 min = .08), cumulative person-hours, round-trip miles × occupants, member/non-member split, `counts_toward_national_service` flag, per-org reporting periods as **configuration** — four different fiscal years, none shared |

---

## 6. Phase 5 — Member experience and operations (depends on Phase 1; low regulatory risk)

| # | Feature | Notes |
|---|---|---|
| 5.1 | New-member onboarding | "World-class." **See §9 on the animated flag** |
| 5.2 | Volunteer scope-of-work / liability paperwork | Reuse StoneDesk's HR e-sign pattern (`sd_hr_*`, e-sign + durable storage). **§9 — the documents themselves need legal review** |
| 5.3 | Ceremonial duties | Honor-guard equipment, shell-casing tracking, shared-team details across posts |
| 5.4 | Vehicle / maintenance tracking | Post-owned vehicles. Distinct from the deferred *building* maintenance item |
| 5.5 | Automated AI monthly newsletter | Grounded in the post's own live data. Depends on Phases 2–4 having data worth reporting |
| 5.6 | Named youth programs | **§9 — programs not named** |
| 5.7 | Veteran-services availability across ALL lodge types | Explicitly not veteran-org-only. Elks and Moose posts run veteran services too |

---

## 7. Phase 6 — District/state rollup (depends on everything; build last)

Read-only aggregation across independently-governed entities for an overseeing
body. **One of the three defensible moat items** — no verified competitor has it.

- Aggregates **entities**, not locations (§1b).
- **Read-only by construction.** A district officer must not be able to write
  into a post's books; the posts are separate legal entities with separate
  treasuries.
- Cross-tenant read is a genuinely new authorisation shape for this platform —
  every existing app is single-tenant-per-licence. Design it with
  `sairn-software-architect` before writing it.

---

## 8. Deferred — logged, not built

Building maintenance/facilities tracking · officer election, term and bonding
tracking · Phase 2 passive bottle sensor hardware (**needs its own patent pass**;
it was not scanned).

---

## 9. NEEDS RESEARCH OR SOURCE DETAIL BEFORE BUILDING

**Blocking-for-that-feature only; nothing here blocks Phase 1.**

### 9a. Regulated — do not build on assumption

1. ~~**Service Officer VA-claims referral** — blocked pending primary-source
   research.~~ **RESEARCHED AND SCOPED 2026-08-30.** See
   `docs/2026-08-30-sairnfreedom-va-claims-accreditation-boundary.md`.
   **38 U.S.C. § 5901** prohibits acting *"as an agent or attorney in the
   preparation, presentation, or prosecution"* of a claim without recognition —
   narrower than the feature name implied. **§ 5902(a)(1) names the American
   Legion and the VFW in the statute** as organizations whose representatives
   the Secretary may recognize, so a post's Service Officer is typically already
   accredited. **Safe to build (Phase 5):** referral directory, appointment
   scheduling and log, accreditation-status tracking, attributed general
   information. **Out of scope:** anything that prepares, presents or prosecutes
   a claim — including form auto-fill, drafting statements in support, or
   assembling an evidence package. **Two hard product rules** come out of it, in
   §9d below.
2. **Tips received — tax treatment.** Already flagged. Reporting obligations,
   tip credit, allocation between employees and volunteers. **Do not build
   fields until researched.**
3. **Liquor licensing — entirely unexamined.** ORC 4301/4303 and OAC 4301:1-1-*.
   The canteen has its own regulator, licence, records and inspection regime, and
   **nothing verified so far covers it.** Do not read gaming coverage as canteen
   coverage.
4. **OAC 109:1-4-* beyond `-08`**, and the AG's actual licence-renewal forms.
   The renewal report this product feeds may impose its own categories.
5. **ORC 2915.091 / .092 / .093** — instant bingo conduct and location rules,
   unread.
6. **Volunteer liability documents (5.2)** — templates need legal review; this
   is document *drafting*, not schema.

### 9d. Two hard product rules from the VA research — not optional

**No fee may attach to claims assistance, anywhere in the product.** Every
recognition route in 38 U.S.C. §§ 5902, 5903 and 38 CFR 14.630 requires
certifying that **no compensation of any nature** is charged. A post is a
nonprofit and its officer serves free, so this is satisfied naturally — **but
the Service Officer function must never sit behind a paid tier, subscription
gate or upgrade prompt.** Doing so creates exactly the compensation the
certification denies.

**The AI assistant must DECLINE claim-strategy questions in its system prompt.**
Not a disclaimer, not a warning banner — a refusal. This platform already made
this call once on SAIRNroofing, where the operations assistant was changed to
refuse claim-strategy questions because *"nothing stopped it answering a
negotiation question from general knowledge, and an app-branded answer of that
shape was the real exposure."* Here the stakes are higher: an AI answering
*"what should I claim for?"* is producing claim preparation, under the post's
brand, for an unaccredited asker, at scale.

### 9b. Named but not defined — need the source detail

7. **Three-layer fee structure** — layers not enumerated.
8. **Conditional dues/fee waiver rules** — conditions not specified.
9. **Donor recognition tiers** — thresholds and names not given.
10. **Named youth programs** — not listed.
11. **AI vendor price search** — scope, sources and citation discipline undefined.

### 9c. A conflict to resolve, not research

12. **The animated flag visual (5.1) contradicts the branding direction.** The
    branding guidance says a **static** design with subtle fold-shadow banding is
    acceptable and safer, and that **animated distortion effects were tried and
    rejected as visually broken** (water/TV-static), with canvas/SVG turbulence
    animation to be avoided. The onboarding item asks for "a properly-built
    animated flag visual."

    These may be reconcilable — the rejection was specifically of *turbulence
    filters on the header*, and a one-time onboarding moment is a different
    surface from a working dashboard. **But it is a direct tension between two
    stated directions and needs an explicit call rather than a builder picking
    one.**

---

## 10. Dependency summary

    Phase 1 (entity, roles, members, fees, branding)
      ├── Phase 2 (POS, canteen, events, hall, vendors)
      │     └── shares ONE calendar with ─┐
      ├── Phase 3 (gaming: accounts, sessions, records) ◄┘
      │     └── Phase 4 (disbursement, donations, outreach, service hours)
      ├── Phase 5 (member experience, ceremonial, vehicles, newsletter)
      │     └── 5.5 newsletter needs Phases 2-4 producing real data
      └── Phase 6 (district rollup) — needs all of the above

**The one interlock worth stating twice:** Phase 2's events calendar and Phase 3's
session constraints are **one calendar**. Building them separately produces a
booking surface that cheerfully schedules a fourth bingo session in a seven-day
window, and a compliance surface that reports the violation afterwards. The
calendar must **refuse**, in the fail-closed posture the roofing rescission
engine already uses.

---

## 11. What this spec does not settle

- **Trade/market build order beyond the phases.** Phase order is dependency
  order, not commercial priority.
- **Whether Tab King already does the membership half properly.** Still the
  single most important open competitive question; Arrow publishes no pricing
  and no feature matrix. **Request a demo before locking strategy.**
- **Pricing, licensing tier, or contract shape.** `sairn-contract-drafter` owns
  that when the time comes.
- **Anything in §9.** Those are named gaps, not assumptions to be quietly filled
  by whoever builds first.
