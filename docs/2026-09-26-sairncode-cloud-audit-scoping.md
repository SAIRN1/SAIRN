# SAIRNcode scoped against the cloud wide-lens external audit — 2026-09-26

**Scoping only. Nothing built. No app file touched.**

**HEADLINE: the cloud research is excellent and its internal baseline is stale
in the direction of understating SAIRNcode. Three items it carries as open are
closed — one of them closed on the same day the internal audit found it — and the
single most valuable thing in the cloud material is a question neither document
asks, because neither had the other: cloud's unresolved CPT-licensing question
lands precisely on a customer-upload design SAIRNcode scoped internally on
2026-08-20 and has not built.**

Measured against `sairncode.html`, `api/`, and `sql/` at **`56887cd5`**,
2026-09-26. Every count below was re-run here, not copied from either document —
which is the only reason §2 exists.

---

## 1. Where the cloud research actually is — the dispatch blocker, resolved

The dispatch recorded this as blocked: *"`docs/cloud-research/` contains only
SAIRNlaw and SAIRNvet audit docs. The SAIRNcode wide-lens audit (7 docs, cloud's
commit `1adefca0`, supposedly on PR #18) is not there."*

**It is there, on a branch, unmerged.** Both halves of the dispatch's premise
were slightly off and the correction matters for anyone else looking:

| Claim | Verified 2026-09-26 |
|---|---|
| "not there" | **On `origin/claude/wizardly-ride-wtun13`**, 8 doc commits ahead of `main`, **9 files / 7,732 insertions**, none merged. `docs/cloud-research/` on `main` legitimately holds only the two `-2026-09-25` files |
| "7 docs" | **Eight**, plus a handoff. The two SAIRNcode ones are `130f8408` (the audit, 937 lines) and `1adefca0` (the wide-lens supplement, 602 lines) |
| "PR #18" | Correct. Open, not draft, not merged |

**Read the branch's own handoff first** —
`docs/cloud-research/SAIRN-PLATFORM-2026-09-26-cloud-research-lane-handoff.md`,
on the same branch. It explains why the docs are not on main, and records that
PR #18's one red check (`github-advanced-security`) is **GitHub-side**: the
Copilot scanning agent errors `CAPIError: 400 The requested model is not
supported` before analysing anything, and has failed all of its last 8 runs
across three PRs. That is a repository-settings matter, not a reason to withhold
a docs-only merge.

**Both cloud documents carry a network caveat that governs how they may be
used.** `WebFetch` returned `EGRESS_BLOCKED` for essentially every vendor,
court, academic and government domain — the sole exception across all six
research passes was a direct fetch of `sourceforge.net`. **Nothing in them is
quotable to a health system, a prospect or a proposal without a re-read from a
network that can reach the primary source.** That constraint is theirs, stated
plainly, and this document does not relax it.

---

## 2. THREE ITEMS THE CLOUD RESEARCH CARRIES AS OPEN THAT ARE CLOSED

The cloud audit is explicit that it treats `docs/competitive-gap-audit-sairncode.md`
(2026-09-23) as the internal baseline and **does not re-derive it**. That was the
right division of labour — but it means every internal verdict three days old
travelled into a 2026-09-26 document unchecked, and two of the three had already
moved. **The third was never right.**

### 2.1 The GP modifier — CLOSED 2026-09-23, the same day it was found

Cloud's §5 item 4 calls this *"real, narrow, and … a small, well-scoped,
high-value fix, not a speculative one,"* reinforced by an OIG finding that 82% of
Medicare chiropractic payments were unallowable through the analogous AT-modifier
failure. **The reinforcement is welcome; the gap is gone.** At this commit:

- `pt-gp` input at `sairncode.html:1496`, placeholder *"GP applied to e.g. 97110, 97140"*;
- the validator at `:8497`–`:8539`, which raises a **block** finding — *"a therapy
  line without GN, GO or GP is returned as UNPROCESSABLE"* — and a separate
  **warn** when GP is recorded on a code not in session;
- a cited rule at `:8380` (CMS Claims Processing Manual Ch. 5) that names its own
  limit: *"THE CHAPTER IS CITED, NOT A SUBSECTION … a precise-looking citation
  nobody checked is worse than an honest one"*;
- `:8381` pins the RTM half to **MLN Matters MM14250** and keeps it a warn rather
  than a block, because the requirement attaches to services *rendered by
  therapists* and the panel cannot see who rendered a line;
- the panel tooltip at `:779` now reads *"GP and CQ modifiers"* — the exact string
  the internal audit flagged as listing CQ where GP belonged.

`\bGP\b` is now **25**, against the audit's measured zero.

### 2.2 A2, the eligibility→coding edge — CLOSED 2026-09-24

Cloud's §0 carries this as *"the join, not the data, is missing."* The join
shipped two days before the cloud pass ran. `scEligibilityConcerns()` at
`sairncode.html:7260` is read by the confidence deriver at `:7194`, under a
comment that states the problem it closes: *"a payer could answer 'inactive' on
Monday and a coder could clear the same encounter on Tuesday with nothing
connecting the two, because the only thing joining them — `encounter_ref` — was
never read across."*

**And it holds the line the whole module holds:** it escalates only on the
payer's own quoted words or on a disagreement between two of the practice's own
recorded checks. It does not invent a coverage verdict, and the comment says why
a CPT-to-service-type mapping would have been exactly that.

### 2.3 A1's exception queue — BUILT 2026-08-20, and this one was never right

**This is the correction that matters most, because both documents are wrong
about it and the direction of the error sends a builder at work that exists.**
The internal 09-23 audit states: *"`confidence` appears 20 times, but as
per-suggestion confidence, not as a route-to-auto-post threshold. **There is no
exception queue and no auto-post path**."* Cloud's §0 and §5 item 1 inherit that
and externally corroborate it as *"the largest gap."*

**The exception queue exists and is five weeks old.** `scRouteCodedItems()` at
`sairncode.html:7393`, headed *"EXCEPTION-BASED ROUTING (2026-08-20, Phase 2
item 3)"*, splits items into two separate tables rather than one list with a
badge — *"the exceptions table is the work queue; the auto-assigned table is a
record you can audit but do not have to work through."* Around it:

- `scDeriveCodedItemConfidence()` at `:7111` returns
  `{confidence, confidence_basis, review_status, escalation_reason}` and sets
  `review_status` to **`auto_assigned`** or **`needs_human_review`** at `:7203`;
- four rendered states at `:7377`–`:7380` — Auto-assigned, Needs human review,
  Reviewed accepted, Reviewed rejected;
- `reviewCodedItem()` at `:7344` is, in its own comment, *"the ONLY way an item
  leaves needs_human_review — nothing in this app promotes a flagged item on its
  own"*;
- the quote gate at `:7118` fails **closed** on purpose: `quote_verified !== true`
  rather than `=== false`, because *"treating 'don't know' as 'verified' would
  auto-assign a code on no grounds."*

**Why the audit missed it: it searched for the word.** `autonomous` is genuinely
**0** at this commit, and that zero was read as the mechanism's absence. The
mechanism is there under the vocabulary the file actually uses — `auto_assigned`,
`needs_human_review`, `exceptions`. This is the audit's own recorded limit
(*"every BUILT verdict is a vocabulary-and-resource measurement"*) running in the
false-negative direction, the same shape as SAIRNroofing's `fall-protection`
hyphen.

---

## 3. What A1 STILL lacks, stated precisely enough to build or refuse

Two halves, and only one is missing.

| Half | State |
|---|---|
| **Confidence + exception-only routing** | **BUILT** (§2.3). Rule-based, not model-based: a label plus the explicit list of checks that failed |
| **The auto-SUBMIT path** | **NOT BUILT, and not merely unbuilt — structurally absent.** `auto_assigned` means *"did not need a coder's attention"*, never *"sent to a payer."* There is no 837 anywhere in `api/`, `sql/` or any app file — `\b837\b`/`\b835\b` appear in exactly two files, both SQL/JSON unrelated to claims. `FHIR` × 3 in `sairncode.html` and one of them is a disclosed refusal at `:2564`: *"No 'FHIR PAS' submission option exists here on purpose"* |

**So the gap is not "SAIRNcode cannot score confidence or route exceptions." It
is "nothing leaves this app to a payer without a human, by construction."** That
is a materially smaller and much better-defined gap than either document
describes, and it is a product decision before it is a build — which is what the
internal audit said about A1 in the first place, for a different reason.

**And the cloud research independently validates the shape of what IS built.**
Cloud's §4 (supplement) is the sharpest argument available for the decision
already taken here:

- Soroush et al. (NEJM AI, 2024) measured GPT-4 at **45.9% / 33.9% / 49.8%**
  exact-match on ICD-9-CM / ICD-10-CM / CPT in unconstrained generation;
- the same lab's 2025 retrieval-narrowed follow-up performed far better — *"a
  published accuracy number is uninterpretable without knowing which task was
  tested"*;
- a genuine randomized crossover trial (JMIR 2025, 15 coders, 300 notes) found
  **no significant accuracy benefit** from AI assistance; only a ~46% cut in
  coding *time* was significant;
- a 2024 neuroimaging study found three neuroradiologists agreed with each other
  at Krippendorff's α = 0.39–0.63 — **there is no stable human baseline** for a
  vendor percentage to be measured against.

`scDeriveCodedItemConfidence()`'s own header already says this: *"a percentage
implies a measured accuracy rate, and nothing in this app measures one … This
file already had fabricated 82%/71% confidence numbers removed from the Fraud
panel in the 2026-08-18 audit."* **The cloud research turns that from a local
discipline into a defensible market position.** Verified here: no numeric
confidence percentage exists anywhere in `sairncode.html`.

---

## 4. THE FINDING NEITHER DOCUMENT MAKES — and it is a stop, not a build

**Cloud's §3 (supplement) is an unresolved legal question. SAIRNcode already has
a scoped, unbuilt design that sits exactly on it.**

Cloud §3, in its own words: *"Whether a platform needs its own CPT license
merely to store and redisplay a customer's own uploaded code set is genuinely
unresolved anywhere in published guidance"* — no AMA guidance, no litigation, no
compliance-firm analysis addresses it; the AMA's licence language is
**source-agnostic**, conditioning the requirement on the organisation's own
use/display with no exception for content it did not originate; and **CodaMetrix
and Nym disclose no AMA licensing arrangement publicly at all**, so there is no
precedent to point at either way.

**And `docs/superpowers/specs/2026-08-20-sairncode-cpt-license-and-specialty-coverage-scope.md`
recommends, for CDT specifically, exactly the scenario with no published
guidance:** *"the practice exports/uploads their own licensed CDT data … into
`sc_encoder`-shaped rows scoped to their `license_hash`."*

**The three code sets are NOT equally exposed, and separating them is the whole
value of this finding.** Verified state at this commit:

| Code set | Internal 08-20 recommendation | Built? | Exposure to cloud §3 |
|---|---|---|---|
| **ICD-10-CM** | free public NLM API, build regardless | **BUILT 2026-08-20.** `findIcd10Match()` at `:10462` against `clinicaltables.nlm.nih.gov/api/icd10cm/v3/search`; the host is in the CSP `connect-src` at `:47`; the UI states *"Free, public, no license required"* at `:12417` | **None.** Public domain |
| **CPT** | the practice's own AMA CPT Developer Program credential, as a second `ALLOWED_SERVICES` entry, same encrypted pattern as Stedi | **NOT BUILT.** `ALLOWED_SERVICES` in `api/sc-credentials.js:58` is still `{ stedi: true }`; there is no `api/sc-cpt-lookup.js` | **Low, and this is the safe shape.** The licence is the customer's, held by the customer, used under their own credential |
| **CDT** | the **upload** path, because no ADA self-serve API was found | **NOT BUILT** | **THIS IS THE ONE.** Storing and redisplaying a customer's uploaded licensed code set is precisely the unresolved case |

**Scoping conclusion, and it is a refusal rather than a plan:** the CDT upload
path must not be built until counsel answers cloud §3 against SAIRNcode's actual
data-handling architecture. The cost of being wrong is not a bug — it is
platform-wide copyright exposure on the one code set with no authoritative API to
fall back on. **Note also that this is live rather than theoretical:** cloud §3
records that on 2026-08-12 PatientRightsAdvocate.org sued the AMA in N.D.
Illinois seeking a declaration that CPT copyright is invalid, that Senate HELP
has an open investigation into CPT licensing as an *"abusive monopoly"*, and that
CMS's proposed CY2027 PFS solicited comment on CPT alternatives. **The ground is
moving; do not build onto it on an assumption.**

**One thing cloud §3 establishes that IS immediately actionable and costs
nothing:** the AMA's AI addendum permits retrieval-based AI referencing CPT on
demand and **explicitly prohibits using CPT content to train or fine-tune a
model.** SAIRNcode does neither today — it has no training pipeline — so this is
a constraint to record before anyone proposes one, not a finding against current
state.

---

## 5. What is scoped as buildable, blocked, or a decision

**Tier 1 — buildable in-house, un-gated, and defined well enough to start:**

1. **The CPT BYO credential** (`cpt: true` in `ALLOWED_SERVICES`, plus
   `api/sc-cpt-lookup.js` shaped like `api/sc-eligibility.js`). Scoped 2026-08-20,
   architecture already settled there (jsonb, no schema change, no new crypto),
   and it is the *licensed-by-the-customer* shape rather than the exposed one.
   Five weeks old and unbuilt.
2. **A depth check on the eight enterprise RCM panels** — claims, prebill, HCC,
   DRG, RAC, denial, AR, revenue. The internal audit is explicit that its §5 is
   *"on paper"* and that *"a direct depth check on those eight panels is owed
   before pitching a large hospital system."* Cloud does not touch it either, so
   this remains exactly as unmeasured as it was. **This is measurement, not a
   build, and it is the cheapest item here.**

**Tier 2 — blocked on something outside engineering:**

3. **The auto-submit half of A1** (§3). Needs an 837 path and a product decision
   about whether anything leaves this app without a human. The 837 half is also
   what SAIRNsenior A4 and SAIRNdental A2/A3 need — see §6.
4. **EHR interoperability.** `Epic` × 0, `HL7` × 0, `interoper` × 0. The internal
   audit did not measure it in either direction and still has not; cloud names
   Epic dominance as the enterprise bar. **Not a gap row yet, because nobody has
   decided SAIRNcode should be an EHR-integrated product.**

**Tier 3 — refused or decided, and should not be reopened:**

5. **Denial-probability scoring.** Refused in code with a measured reason
   (`scPreSubmissionRisk()` produces counts, never a percentage). Cloud §4 of the
   audit doc is the strongest external support this decision has: Experian,
   Inovalon and Waystar all ship the exact percentage, **none publishes a
   calibration methodology** — no reliability diagram, no Brier score, no
   validation cohort — while the closest real-world analogue is under active
   independent scrutiny (Texas AG/Pieces, *Kisting-Leung v. Cigna*,
   *Lokken v. UnitedHealth*, GAO-26-109116). Cloud's supplement §2 re-verified all
   three matters as **still live** as of 2026-09-26. **Sell the refusal.**
6. **Germany / Hybrid-DRG.** `Hybrid-DRG`, `115f`, `SGB` all still × 0. Correctly
   unbuilt for the reason the internal audit gives.

---

## 6. What this changes for the rest of the platform — SAIRNcode is the precedent

**SAIRNcode already ships a working clearinghouse integration, and it is the
answer to a question three other apps are recorded as blocked on.**
`api/sc-eligibility.js` runs live X12 270/271 through **the practice's own Stedi
account**, using a key stored by `api/sc-credentials.js`. Its header states the
structural reason: *"SAIRN never holds a clearinghouse account on their behalf
(see that file's header for the BAA reasoning)."* Its anti-fabrication contract
is the part worth copying — no credential configured returns **503
NOT_CONFIGURED**, never a simulated result, and a payer or Stedi error surfaces
that real error text rather than a friendly *"not covered."*

The header also records a defect worth carrying into any reuse: the
`Authorization` scheme word is **`Key`**, not bare and not `Bearer`. A bare key
**still authenticates**, so every check returned a well-formed 271 and nothing
looked broken — while mock requests were being forwarded to real payers. **A
working response is not proof the integration is configured correctly.**

**This is direct input to the Tier 2 clearinghouse question** (SAIRNsenior A4,
SAIRNdental A1/A2/A3 — `docs/2026-09-26-gap-triage-four-verticals.md` §3). Two
things it settles and one it does not:

- **Settled: the commercial model.** Those rows are recorded as needing "a
  clearinghouse relationship." SAIRNcode's shipped answer is that the *customer*
  brings the relationship, which removes the BAA and the account from SAIRN
  entirely. Dental A1 (real-time eligibility) is the **same 270/271 transaction
  already working here.**
- **Settled: the code pattern.** `sc-credentials.js` + a per-app proxy endpoint,
  with the 503-not-configured contract.
- **NOT settled: 837/835.** Senior A4 and dental A2/A3 are claim submission and
  remittance, not eligibility. **No 837 or 835 code exists anywhere on the
  platform**, so this is a genuine build behind the pattern, not a copy of it.

---

## 7. What this pass did NOT do

- **It did not re-derive every SAIRNcode row.** §2 re-derived the three the cloud
  documents carry as open, plus the four state claims in §4 and §5. A row
  recorded as BUILT elsewhere was taken on trust; that is the weaker half of this
  pass and is stated rather than glossed.
- **It did not verify one competitor claim.** Every vendor, funding, KLAS,
  litigation and academic figure above is cloud's, inherited under cloud's own
  snippet-only caveat, and re-checking any of it needs a network that can reach
  the sources.
- **It did not resolve whether Nym Health's explainability reaches SAIRNcode's
  verbatim-quoted-span granularity.** Cloud flags this as genuinely undetermined
  and it is the one checkable fact that would settle whether A5 is still ahead.
  Do not assert either way. Internally, `sc_coded_items` stores `quote`,
  `quote_verified`, `reasoning` and `source_rule` — verified present, 6 hits each
  for the two flags.
- **It did not measure the eight enterprise RCM panels** (§5 item 2). Naming the
  measurement is not performing it.
- **It did not build, and it did not touch `sairncode.html`.** The CPT/CDT items
  in §4 are deliberately left as a refusal and a scope.
- **It did not merge or modify PR #18.** The cloud documents are cloud's; the
  corrections in §2 are recorded here rather than edited into another session's
  files.

## 8. Decay

State cells here are *"this vocabulary appears N times"* plus line numbers in a
940KB file, both measured at `56887cd5`. **§2 exists because a three-day-old
baseline had moved twice** — treat every verdict above the same way and re-derive
before acting. The cloud documents decay faster and on a different clock: two
active federal dockets past their known deadlines, funding and KLAS figures in a
segment adding vendors monthly, and an AMA copyright suit filed six weeks ago.
**Do not quote any external figure from them without re-reading the source.**
