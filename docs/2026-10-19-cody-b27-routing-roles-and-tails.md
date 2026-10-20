# cody b27 — the routing primitive, three routed role changes, and the twelve unproducible tails

2026-10-19. Six items. **Three of the routed instructions turned out to be
incomplete, and each was found by DRIVING the routed change rather than by
reading it** — which is the single pattern this batch is about.

---

## 0. TWO CLAIM BLOCKS, BOTH VERIFIED, ONE REAL

`sairn_claim.py check` blocked twice. Both are recorded because a block is a
claim to verify, not a fact — and because the second one changed the work.

**BLOCK 1, `fourth` on `rt_routes` — A WORD COLLISION.** fourth's active claim
declares **no `api/` and no `sql/` path**: it is `sairndental.html`,
`sairnmechanical.html`, `docs/CRITICALITY-TIERS.md`, a cloud-research document
and its own three reporting files. And fourth's **own** document —
`docs/2026-10-19-fourth-b34-routing-phase1.md` §3 — routes this handler branch
**to cody**, saying `api/sd-data.js` *"is claimed by cody on b26 … It was not
touched."* Verified and proceeded.

**BLOCK 2, `hank` on `api/_lib/leg-roles.js` — A REAL FILE OVERLAP, AND THE
FILE WAS DROPPED RATHER THAN ARGUED OVER.** It was in cody's first FILES list
and in hank's live b22 claim. It turned out not to be needed at all:
`decide(resource, role, action, grants, home)` **already takes the fifth
argument** (`api/_lib/leg-roles.js:490`) and `LEG_RESOURCES` lives in
`api/sd-data.js:16524`. Likewise `ALF_NON_MGMT` is at
`api/sd-data-alf-isolation.test.js:362`, not in `api/_lib/alf-roles.js`. **The
task text was not reworded; only the FILES list was corrected to what the work
actually touches**, and the correction is stated in the claim string itself.

---

## 1. Item 1 — `rt_routes` landed exactly as routed, and the feature was STILL DEAD

### 1.1 The paste, and "exactly as written" asserted rather than intended

> **THE CONCEPT:** *the `rt_routes`/`rt_stops` endpoint must answer all four
> verbs behind BOTH a licence and an employee session — a licence proves the
> shop, and a list of addresses joined to a named employee is not shop
> metadata — and the registry must declare the three non-read verbs IN THE SAME
> EDIT, because `api/_resources/index.js` asserts extra actions at load and a
> verb declared without a handler asserts a capability that answers 400.*

`docs/b27-logs/land_rt_routes_branch.py` **extracts the 151-line block out of
the document's own fenced code** rather than retyping it, inserts it with four
spaces of indentation to match the file's per-resource branches, then **strips
those four spaces back off and requires the result to be BYTE-IDENTICAL to the
document**. Indentation is not the code; a byte comparison that ignored it
could not tell a reformat from an edit.

*"And nothing else in that change"* is asserted as a **diff property**: exactly
one contiguous insertion, no line removed or altered, line counts reconciled.

It also **fails closed on its dependencies before writing anything** — it
refuses unless `api/_lib/routes.js` exists and exports `validateRouteKey`,
`validateStops`, `applyOrder` and `optimize`, because a branch that requires a
module which is not there is a ReferenceError at request time and
`node --check` says nothing about it.

**ONE POST-CONDITION WAS WRONG ON THE FIRST RUN AND REFUSED THE WRITE**, which
is the arm working. It checked the branch sat above the handler's fallthrough by
comparing against the first occurrence of `'Unsupported action/resource
combination'` — a string that appears **three times** in this file, twice inside
**comments** thousands of lines above the statement. The comparison was against
prose. Re-anchored on the comment-plus-statement pair the insertion point is
itself located by. **Same defect class as b26's 1400-character window, this
time in a post-condition.**

### 1.2 THE FINDING: a FOURTH gate nobody knew about

> **THE CONCEPT:** *a registry module may declare `visibleToAllApps: true`, and
> `isVisibleTo` must honour it — so a genuinely cross-app resource can be
> reachable by every licence WITHOUT being hidden in `shared.js`, where
> `tools/criticality_tier_check.py` skips it by name and its tier goes
> unchecked.*

`isVisibleTo()` had exactly **two** routes to visibility: be in `shared`, or be
owned by the caller's own app. `api/_resources/routes.js` registers both names
under the **pseudo-app `routes`**, which no licence is ever issued for.
Measured:

```
isVisibleTo('rt_routes','stonedesk')        false
isVisibleTo('rt_routes','sairngrounds')     false
isVisibleTo('rt_routes','sairnmechanical')  false
```

**Every wired consumer got 400 `FOREIGN_RESOURCE` from `checkEnvelope` before
the handler branch ran.** The branch, the registry entry and the `extraActions`
declaration were **all correct** and the feature was dead — in a fourth place
the routing document did not know about.

**WHY NOT MOVE THE TWO NAMES INTO `shared.js`, the existing mechanism:**
`api/_resources/routes.js`'s own header argues against it and is right.
`apps_with_registries()` skips `'index'` and `'shared'` **by name**, so all
seven of `shared.js`'s resources have no criticality row and the completeness
arm reports no finding about it. These two are **Tier A on confidentiality**.
Moving them would have bought reachability with invisibility to the tier arm —
one silent failure traded for another.

### 1.3 The one arm item 1 asked for, and five more

`api/_lib/routes.test.js` section 10, **63 arms total, exit 0** (was 56):

| arm | what it proves |
|---|---|
| **D0** | PRECONDITION, comment-stripped: the branch is in `api/sd-data.js`. A third state — if the handler will not load, nothing below is about routing |
| **D1** | a read **reaches the branch**: 200 with `provisioned`, and **not** a 400 |
| **D2** | NEGATIVE CONTROL: no session is refused **by the branch** at 403, not by the allowlist at 400. **A 403 can only come from inside the branch**, which is what makes D1 attributable |
| **D2b** | DISPATCHER-HEALTH CONTROL on `employees` (`shared.js`, visibility independent of the flag), green in **both** legs |
| **D3** | NEGATIVE CONTROL: a **declared** verb reaches the branch's own validator and an **undeclared** one does not — without the second half this could not tell *"extraActions let the verb through"* from *"every verb is allowed"* |
| **D4** | NEGATIVE CONTROL: the flag did **not** open the boundary — `law_matters` and `alf_clients` are still invisible to a stonedesk licence, and `CROSS_APP_NAMES` is exactly the two names |
| **D5** | ABLATION: remove the flag in a copy of `api/` and D1 must go **RED with the exact 400 the feature had**, while D2b stays green |

**D5's CONTROL WAS WRONG ON THE FIRST SPELLING AND THE RUN CAUGHT IT.** It
required **D2** to stay green. D2 goes red too, because **the visibility gate
runs before the branch**, so with the flag gone every `rt_routes` arm fails
together — which is precisely what *"the feature was dead"* means. Re-aimed at
D2b, a resource the mutation does not touch. **A control has to sit outside the
blast radius.**

---

## 2. Item 2 — the three routed role and policy changes

### 2.1 `office_manager` joins `ALF_NON_MGMT`

> **THE CONCEPT:** *the `alf_facility` write gate must refuse every
> non-management SAIRNcare role and the suite's loop must NAME all of them — an
> excluded role nothing drives is an exclusion nobody is testing.*

hank's 522h review found it: `office_manager` is in
`ROLES_BY_APP.sairncare` (`api/_lib/auth.js:291`), offered in both
`sairncare.html` dropdowns, has **zero** `roleSet()` hits, and was **not** in
`ALF_NON_MGMT`. `ALF_MANAGEMENT_ROLES` is `{owner, billing}`, so 7 − 2 = **five
excluded roles and four driven**.

**AND A COMPLETENESS ARM, because the token alone fixes only today.** `ROLE-all`
asserts `ALF_MGMT + ALF_NON_MGMT` is **exactly** `ROLES_BY_APP.sairncare`, read
out of `api/_lib/auth.js` rather than retyped, with a parse-sanity guard so a
regex that stops matching cannot pass vacuously. **The sixth role cannot repeat
this.** 30 arms, exit 0 (was 28).

### 2.2 The `law_trust_reconcile` gate reads the module

> **THE CONCEPT:** *this gate must READ the policy from `api/_lib/law-roles.js`
> rather than re-list it, because the hand-written literal said OWNER-ONLY
> while the module's `LAW_RECONCILE_ROLES` has said `{owner, attorney}` since
> b19 — so an attorney was refused in production by a copy the policy owner had
> already superseded.*

The paragraph above the literal called `attorney` *"the open question, not a
rejected one"*. **b19 answered it, in the module, and this call site never
heard.** Two copies of one policy is how that happens, so the fix deletes the
copy rather than editing it. The message is derived through `denyMessage()` too
— *"available to the firm owner"* became untrue the moment attorney was added
and nothing would have caught it. `roleSet` is still used **33 times** in this
file, so the import stays; **checked before deleting anything**, as the routing
asked.

### 2.3 The fifth argument — and the routing was incomplete TWICE

> **THE CONCEPT:** *the gate must read the home's own settings row and pass it
> as `decide`'s fifth argument, because without it every apprentice gets the
> empty default and F3's countersign branch is unreachable in production — and
> an ABSENT row must still produce the NARROW default.*

`sql/sairnlegacy_settings_schema.sql` states the gap in its own words:
*"NOTHING READS THIS TABLE YET … `api/sd-data.js` passes no `home` argument, so
every apprentice currently gets the empty default."* That is this call site, and
this is the read. **The table is `sairnlegacy_settings`, not `leg_settings`.**

**AN UNREADABLE SETTINGS TABLE FALLS TO THE NARROW DEFAULT, AND THAT IS WHY IT
IS NOT A PR §1.11 VIOLATION.** Every use of `home` inside `decide()` can only
**widen**: `liveryBilling()` of a missing value is `through_the_home`, which
grants nothing, and `apprenticePolicy()` of a missing value has an empty
countersign list, which allows no prepare. A failed read therefore refuses
**more**, never more than it should. Failing closed here would mean refusing the
whole request — taking all 36 resources down for every role, on a settings table
that is optional by design.

#### ROUTED STEP 2 WAS TRIED, DRIVEN AND REMOVED

Registering `leg_settings` in `LEG_RESOURCES` breaks an invariant two arms
assert — **measured, not predicted**:

```
FAIL A1. the handler dispatches 36 leg_ resources and the table carries 36 rows
         handler=37 table=36
FAIL A2. every resource the handler dispatches has a row ... READ from the source
         no row: ["leg_settings"]
```

**The suite is right and the routing is incomplete.** A2's invariant is that no
`leg_` resource may reach that gate without a `LEG_ROLE_MATRIX` row, and
`LEG_ROLE_MATRIX` is in `api/_lib/leg-roles.js` — **hank's file, in hank's live
b22 claim**. Routed back. The entry is inert without that row for three
independently measured reasons anyway, so nothing is lost by waiting.

#### THE READ IS CONDITIONAL AND THE CONDITION IS PROVED

The **unconditional** read was written first and **driven**, and it broke four
green arms:

```
FAIL L1. a deprecated staff token writes an invoice -> 403 ... and NO data
         fetch happened          -> calls=1       (and L2, L3, L4 the same)
```

**Those arms are right.** `decide()` consults `home` only for `apprentice` and
`livery` — and that list is a **copy of a module fact**, which goes stale in
silence. So arm **H1** drives **6 roles × 36 resources × 3 actions = 648
comparisons** under two **opposite** settings rows and requires every
non-listed answer to be **identical**. **H2** requires the two listed roles to
actually move, so H1 is a comparison that could have come out the other way. **A
third settings-sensitive role turns H1 red.**

**L2/L3 RE-AIMED — NARROWER, NOT LOOSER.** *"No data fetch"* is now asserted on
the **resource tables**, derived from `LEG_RESOURCES`, with any other call
counted as a **stray**. `sairnlegacy_settings` is this home's configuration and
holds nothing about a decedent or a case. **The file already contained the
precedent** — L6's own comment: *"The token lookup itself IS a fetch, so
`calls.length === 0` cannot be asserted here — `no POST` is the property that
matters."* Same situation, same answer, one layer over.

#### AND A SECOND GATE IS RECORDED RATHER THAN MISSED

**`prepare` is not a declared `extraAction` for ANY `leg_` resource**, so the
dispatcher answers **400** before the role gate — and past that, the
`LEG_RESOURCES` branches dispatch only `read` and `write`.

**MY FIRST SPELLING OF S2 ASSERTED `statusCode !== 403` AND THAT 400 SATISFIED
IT.** It would have reported F3 working while every request was refused as an
unknown verb. Arms **V1/V2** now measure that gate explicitly, and S0b/S2/S2b
were moved to `decide()` directly — the **policy** half, which is what the fifth
argument changes.

**NOT FIXED HERE, and the reason is a boundary rather than an oversight:** the
declaration needs the handler branch beside it (the `rt_routes` lesson exactly),
and that branch is the countersignature flow in `api/leg-countersign.js` —
**hank's, and explicitly out of bounds this batch.**

`api/b27-leg-settings.test.js`: **18 arms, exit 0.**

---

## 3. Item 3 — R1c, R1f and R2 re-aimed

All three were red because **the policy moved**: hank's b20 (`89c17849e`) took
`paralegal` **off** `LAW_RECONCILE_ROLES` on Michael's answer — *"with the grant
and no attestation step the app lets a non-lawyer produce a finished
reconciliation that nothing records a lawyer as having reviewed, and the duty
under Rule 1.15 is the lawyer's and non-delegable."*

**The module's own comment predicted this red and asked for exactly this
re-aim:** *"the arm is in api/ and is re-aimed when the suite's owner updates
it, not suppressed here."*

* **R1c / R1f** → assert **DENY**, and name the deferral: the grant is
  **deferred behind a mechanism, not refused**. Rule 5.3 still supports the
  delegation and `LAW_RECONCILE_ATTESTATION.candidate` still names what would
  make it safe. Arm **M2** proves the refusal still offers C2's `prepare` route.
* **R2** → the relationship is now **equality**. **It is not weaker for that**,
  and that is checked rather than asserted: it still fails in **both**
  directions — an extra non-bar-admitted reconciler lands in `extra`, a
  bar-admitted role silently dropped lands in `missing`.
* **R2a** (new) refuses a comparison between two **empty** sets, which the
  equality alone would have satisfied.
* **R2c** (new) requires `paralegal` **absent** *and* the attestation record
  still saying the review is required-but-unimplemented. **Re-adding paralegal
  without building the mechanism turns R2c red**, so *"deferred behind a
  mechanism"* cannot decay into *"quietly granted"*.

**34 passed, 0 failed** (was 29/3).

### 3.1 The `leg_clergy` rollup row is NOT closed, and cody could not close it

`tools/criticality_tier_check.py` → `PROBLEMS:14`, of which **five** are cody's
own retiers never reconciled with the rollup — **three from b26's `leg_clergy`
B→A and two from b25's `customers` B→A**. A retier that updates the row and not
the rollup is the defect that checker exists for, and cody did it twice.

**The fix is three commands and was DRIVEN in a disposable worktree, not
suggested:** `--fix-rollup-list` plus two count cells, `PROBLEMS:14 → 9`,
`md_table_check` clean. **cody did not apply it: `fourth` holds
`docs/CRITICALITY-TIERS.md` under a live claim** whose own subject is that
register. Full route, with the exact diff and the measured result:
`docs/b27-logs/ROUTED-TO-fourth-rollup-close.md`.

---

## 4. Item 4 — a STABLE LAST LINE in each of the twelve

> **THE CONCEPT:** *a known-red row is only ATTRIBUTABLE if the tail it records
> is a line the runner really produces, so the fix belongs in the SUITE — each
> prints ONE deterministic final line on every exit path — rather than in the
> register, where a tail copied from one run goes stale the next time an arm is
> added.*

**Michael asked for the suite side, and here is why it is the better half:**
copying the observed line into the register would close all twelve today and
reopen them on the next change, because for most of them **the observed line IS
an arm name or an arm list**. The register would be correct and fragile.

```
process.on('exit', …)  /  atexit.register(…)      ->  SUITE-RESULT <path> END
```

**Last on every exit path**, including the `process.exit(1)` / `sys.exit(1)` an
arm failure takes, and carrying **no digits** — `known_red_check`'s comparison
normalises digits away, so a count would make a RED run and a GREEN run compare
**equal**. The path is in the line, so each row's tail stays unique to its file.

**A CONSTANT RATHER THAN A VERDICT, and the second reason was a real bug caught
before writing:**

1. `known_red_check.py` decides RECOVERED from the run's **green** list, by exit
   code, so the tail's only job is to identify the last line.
2. **`atexit` handlers receive no exit code, and `sys.last_value` is an
   INTERACTIVE-mode artefact of an uncaught exception — it is NOT set by
   `sys.exit(1)`**, which is the path these probes take. The first draft read it
   and would have printed one verdict for every run, in a tool whose whole
   purpose is to make a tail trustworthy.

**The Python hook is registered at the END of the file, not the top**, and that
is not cosmetic: `atexit` handlers run in **reverse** registration order, so the
earliest registration fires last. These probes register their own cleanup.

**WHAT THIS CANNOT DO, STATED:** a suite killed by a **timeout** or a hard crash
never reaches the hook. `tests/run_report_only_checks_probe.py`'s stored tail is
literally *"TIMED OUT after 300s"*, so that row's history includes a state this
cannot stabilise. It completes today, and if it hangs again the tail is the
timeout line again — correctly, because **a hang is not a result**.

**The subject list is read out of the register** (`tail_verdict_2026_10_19 ==
UNPRODUCIBLE`), never typed, and the tool **refuses when that selector returns
nothing** rather than reporting success over an empty set.

**No stored tail was overwritten. New entries sit beside the old ones**, each
carrying `supersedes`, so the record of what the row used to claim survives.

---

## 5. Item 5 — the ten timeouts, and the four undiagnosed recoveries

### 5.1 The ten, re-driven at 300s and reported as RESULTS

b26 drove the census at **120s**, not the runner's 300s, and said so: *"TIMEOUT
10 is an upper bound on hangs and a lower bound on completions."* Re-driven at
300s in a disposable worktree. **Figures and per-row verdicts are in
`SAIRN-report-cody-b27.txt`; they are not restated here, because a figure typed
into two documents drifts in one of them.**

### 5.2 The four rows that went green without a fix of cody's — DIAGNOSED

| row | why it is green |
|---|---|
| `api/sf-auth.test.js` | **`28f7744ee` (2026-10-13), hank:** *"a post trustee gets a login — view-only on financial records, and the scope is DERIVED not transcribed."* The row's `why` described `trustee.audit` existing on one side of a three-way agreement as **an open product question rather than a defect**; that commit built the other two sides (`api/_lib/auth.js`, `api/_lib/sf-roles.js`) and added `api/role-vocabulary-agreement.test.js`. **The question was answered, not the arm weakened.** |
| `tests/faults/transport_timeout_sweep.js` | **77 passed / 4 FAILED → 81 passed / 0 failed, 15 apps.** The row recorded *"FOUR REAL DEFECTS IN THREE APPS"*; all four transports were bounded by the 2026-09-11/09-12/09-15 sequence (`22270df7c` bounded twelve unbounded write transports, `a3d8c8551` and `f2b1b35b4` fixed StoneDesk's, `a40065e91` fixed a hand-written transport name that rotted against a correct refactor). **The arm count went UP, 81 from 81 — it did not shrink to pass.** |
| `tests/sql_preflight/run_probe.py` | **`29c8fc612` (2026-10-14): "license_keys catalogue gap + function-as-table false positive."** The row recorded `UNDECLARED_TABLE webhook_events`. The tool's own documentation at `:778` says **`UNDECLARED_TABLE` IS EXPLICITLY NOT BLOCKING** in DECLARED mode; that commit closed the catalogue gap the finding came from. Its own message says *"tests/sql_preflight/run_probe.py still PASS"* — **the suite was green at that commit and the register row was never retired.** |
| `tests/run_b12_routed_findings_probe.py` | **`NO FINDINGS -- all 8 arm(s) hold.`** The row was **red on purpose**, written by cody b12 with *"EVERY FINDING IS IN api/, WHICH IS HANK'S, so each is ROUTED AND NOT FIXED."* All four routed findings have since been fixed by their owner. **This is a routing arm that did its whole job**: it held the evidence until the owner acted, then went green on its own. |

**The pattern across all four: not one went green because an assertion stopped
reaching anything.** Three were closed by a named commit and one by four routed
fixes landing. That distinction is the thing the register could not tell from an
exit code, and it is why the b26 rows carried an **undiagnosed** `why` rather
than a guessed one.

---

## 6. What is NOT done

* **No live endpoint check and no live render.** Every verification here is
  source-level or in-process. **Nothing establishes that `rt_routes` answers a
  real request against a real Supabase** — the branch is landed, reachable in
  the dispatcher, and unproven in production.
* **`prepare` is still an undeclared verb** with no handler branch. F3's policy
  is live; the verb is not. Routed, with the reason.
* **`leg_settings` is not in `LEG_RESOURCES`** and the `LEG_ROLE_MATRIX` row it
  needs is hank's. Routed.
* **The F2 livery GRANT is not wired end to end.** `decide()`'s branch 4 needs a
  per-employee grant and `api/sd-data.js` passes `null`. S1c asserts the request
  is **still refused** for exactly that reason, so the half that landed is not
  mistaken for the whole.
* **The 3 rollup findings are routed, not closed** — fourth holds the register.
* **The deployed `alf_facility` role gate is still UNVERIFIED.**
  `tools/alf_facility_role_gate_live_probe.py` exits 2 for want of
  `ALF_LICENSE`. Every arm on that gate is against a mock and the probe is right
  to refuse rather than report clean.
* **`tests/law_reconcile_role_vocab_check.py` still needs re-aiming.** It parsed
  the literal that 2.2 deleted. It was **already exit 2 for an unrelated
  reason** (its own `ROLES_BY_APP` regex matches neither file), so it is red
  either way — but the re-aim target is now `api/_lib/law-roles.js` and that is
  recorded rather than left to be rediscovered.
