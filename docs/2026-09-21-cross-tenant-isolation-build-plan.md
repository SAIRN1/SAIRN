# Cross-tenant isolation tests for Tier A — the scoped, sequenced build plan

**Findings #276/#278 (HIGH).** Scoped 2026-09-21 by Hank. Not built — this is
the plan the build is dispatched from, plus one proven reference implementation
so the other units are transplants rather than inventions.

**Do not read a number out of this document.** Every figure below is produced by
`python tools/cross_tenant_isolation_scope.py --plan` and moves as work lands.
Run it. This file explains what the numbers mean and in what order to spend
them; the tool is the source.

---

## What the finding actually says, in two halves

The hover auditor's **#269** swept `license_hash` *filtering* to 84/84 Tier A
resources: every Tier A query is scoped by tenant. Verified independently here
against `docs/CRITICALITY-TIERS.md` — the register yields exactly 84 Tier A
rows, and all 84 have locatable serving code.

**#276/#278 are the other half, and it is the half that decays.** That filtering
is asserted by almost nothing. A filter nothing tests is a filter the next
refactor drops, and the failure is silent in the worst possible direction:
tenant A reads tenant B's row and the response looks completely normal. No
error, no log line, no failing test. On this platform the rows in question are
IOLTA trust transactions, patient charts, controlled-substance logs and payroll
runs.

Starting state, measured rather than asserted:

```
  Tier A resources         84
  GENUINE isolation test    0        <- before this session
  WEAK -- looks like one   ..
  NONE                     ..
```

---

## The correction that changes the size of the job

**The unit is not 84.** It is the number of places the tenant filter is actually
*built*, and that is materially smaller, because most Tier A resources are served
by **generic dispatchers**:

```js
const LAW_RESOURCES = { law_invoices: 'invoice_id', law_opaccounts: 'opaccount_id', ... };
if (LAW_RESOURCES[resource] && action === 'read') {
  const r = await fetch(rest(resource + '?license_hash=eq.' + enc(licHash) + '&select=data'), { headers });
```

One query, built one way, for every member of the map. One parameterised test
covers all of them — and, far more importantly, **breaks once for all of them**
if the filter is ever dropped. That is the property worth buying.

Current split, from `--plan`:

```
  TEST UNITS                     48   <- the real size of the job
    shared dispatchers           11   covering 50 of the 84 resources
    own-branch resources         37   one test file each, paid individually
```

**11 units buy 50 resources. The other 37 units buy 34.** That ratio is the
entire argument for the phase order below, and it is the thing a per-resource
worklist would have hidden — the first version of the scoping tool produced
exactly that worklist and it was wrong in the expensive direction.

---

## Three test shapes, not one — and this is the main finding of the scoping

`api/sairndental/complaint-respond.test.js:100-137` is the one genuine
cross-tenant isolation test on the platform today, and it is correctly named as
the pattern to build from. **But it is a single-id fetch, and most of the 48
units are not that shape.** A session that transplants its 404 assertion onto a
list read will write a test that passes against a handler with no tenant filter
at all.

| Shape | Where | The refusal is | The trap |
|---|---|---|---|
| **L — list read** | `?license_hash=eq.<h>&select=data`, no id clause | **an absence**: 200 OK carrying only tenant A's rows | asserting `length` instead of **content**. A handler that returns `[]` for everybody passes a length check and serves nobody |
| **I — id read** | `license_hash` **AND** an id clause | 404 / empty. complaint-respond's shape | none new — this is the documented one |
| **W — write** | `?on_conflict=license_hash,<idCol>` upsert | nothing visible at all | **the dangerous one.** See below |

**Shape W is the one nothing on this platform tests today.** The upsert is keyed
`(license_hash, idCol)`, so tenant A writing tenant B's id creates a *separate*
row under A's hash instead of overwriting B's. That is correct — and it is
correct *by accident* unless two things are asserted:

1. **`license_hash` is in the `on_conflict` key.** Drop it and the upsert
   collides on the id alone, so tenant A's write **replaces tenant B's row**.
   The API response is a normal 200 either way.
2. **The body carries the handler-derived `licHash`**, not anything the caller
   sent. A handler that read `license_hash` off the payload would let a caller
   write into any tenant it can name.

Neither is visible to a test that only checks the response status.

---

## What is NOT covered by this work, said before anyone claims otherwise

- **The database half.** These tests drive the handler; the handler builds the
  query it builds. A wrong RLS policy or an over-wide GRANT passes all of them.
  That is a different control needing a structurally different method — see
  `tools/service_role_tier_a_gate_check.py` and the grant-sweep skill.
- **The app boundary.** `tests/app_session_isolation.js` already tests whether
  one *app's* session reaches another *app's* data, with a single `LIC_HASH`.
  **That is not tenant isolation** and the scoping tool deliberately grades it
  `NONE` for this purpose. Do not let its existence be read as coverage here.
- **Non-Tier-A resources.** Out of scope by the tier register's own decision.

---

## The reference implementation — proven, not described

`api/sd-data-cross-tenant-isolation.test.js` covers the `LAW_RESOURCES`
dispatcher (`law_invoices`, `law_opaccounts`, `law_barcerts`) in all three
shapes. **9 assertions pass; 3 of 3 deliberate sabotages caught**, and
`api/sd-data.js` restored byte-identical afterwards:

| Sabotage | Result |
|---|---|
| `license_hash` filter removed from the LAW read branch | **CAUGHT** — 4 arms fail |
| `license_hash` dropped from the upsert `on_conflict` key | **CAUGHT** — 3 arms fail |
| Row body takes `license_hash` from the **payload** | **CAUGHT** — 1 arm fails |

Three properties of it are load-bearing and must survive every transplant:

1. **The fetch mock parses every `<col>=eq.<value>` clause out of the URL and
   filters by all of them, the way PostgREST does. The mock *is* the test.** A
   mock returning a fixed array, with an assertion that the URL *contains*
   `license_hash=eq.`, is a string check wearing a behaviour check — it passes
   when the filter is present but ANDed wrong, when the handler ignores the rows
   it gets back, and when a second query on the same path lacks it. The scoping
   tool grades that `WEAK`, not covered.
2. **Both directions are driven.** Tenant A must see only A's rows *and* tenant
   B only B's. A handler hardcoded to one tenant passes the A-only arm.
3. **A negative control on the mock itself.** An unfiltered query must return
   *both* tenants. If that ever returns one row the mock has stopped filtering
   and every other arm is passing for the wrong reason.

**Every member of a dispatcher is driven individually, not one representative.**
A test that drives one member proves the dispatcher and proves nothing about
whether the other members are still in its map.

### Session prerequisites that cost real time if discovered independently

- `process.env.SD_AUTH_SECRET` must be set **before** `api/_lib/auth` is
  required — it reads the secret at module load and throws if absent.
- The session token must be signed against **the hash the handler derives** from
  the bearer key. Sign it against anything else and the handler answers
  `NO_SESSION` — which reads as "isolation works" and is a false pass.
- `loadHandler()` must clear `require.cache` for both `./_lib/license` and
  `./sd-data.js` per tenant, or the second tenant inherits the first's stub.

---

## The phases

Run `python tools/cross_tenant_isolation_scope.py --plan` for the live list.
Rank is ordinal — it orders work and is **not** a probability. It combines the
tier register's own harm sentence (money / a person), how many serving branches
a resource has, and whether a dedicated endpoint reaches it outside
`sd-data.js`'s shared preamble.

| Phase | What | Units | Resources | Why here |
|---|---|---|---|---|
| **1** | Shared dispatchers where money **or** a person is at stake | 7 | 33 | Best ratio on the board. `DNT_RESOURCES` alone is 9 resources for one test |
| **2** | The remaining shared dispatchers | 4 | 17 | Same leverage, lower harm class |
| **3** | Own-branch resources where **both** money and a person are at stake | 11 | 11 | `rf_invoices`, `alf_payer_rules`, `sen_claims`, `law_trusttx` … |
| **4** | Own-branch, one harm class | 25 | 25 | The long tail |
| **5** | The remainder | 1 | 1 | — |

**Phases 1 and 2 are 11 sessions' worth of work and close 50 of the 84.** That
is where to stop and re-measure before committing to phases 3–5, because the
tail is 37 units for 34 resources and the case for it should be made against a
fresh number, not this one.

### Dispatch rules

- **One unit per claim.** `python tools/sairn_claim.py claim <app> "cross tenant
  isolation <UNIT>"`. Do not claim "phase 1".
- **A unit is dispatched whole.** Every Tier A member of the map, all three
  shapes, or the unit is not done. A partial unit reported as done is worse than
  an untouched one.
- **Sabotage-verify or it does not count.** At minimum the three arms in the
  table above, per unit, against that unit's own branch. Assert the anchor is
  unique before mutating; a non-unique anchor is refused, not guessed at.
- **Every unit is a Tier A change** and opens a review obligation
  (`tools/tier_a_review_gate.py --open`). Reviewed by a session other than the
  author. At 11+ units this queue is the thing that will go stale first —
  it is already 66h overdue on unrelated items as of this writing.
- **Re-measure after each unit**, with `--plan`. If GENUINE does not rise by the
  number of members in the unit you just built, the test is not being recognised
  and something is wrong with it, not with the tool.

---

## The tools, and the control on them

- `tools/cross_tenant_isolation_scope.py` — the measurement and the phasing.
  Exit 1 is a finding (GENUINE < 84), exit 2 is **COULD NOT TELL**, never folded
  into either.
- `tests/run_cross_tenant_scope_probe.py` — **the control on the grader.** Seven
  fixtures, both directions: two genuine spellings, three near-misses each one
  property short, two shapes that must never be mistaken for tenant isolation.

**The grader has already been wrong once in the inverting direction**, and it is
recorded rather than quietly fixed. Criteria derived from a single file encoded
*that file's spelling* rather than the property, so
`api/sd-data-cross-tenant-isolation.test.js` — which parses the query generically
and binds its tenants to constants, both strictly better than the reference —
graded `WEAK`. **A test that did the more general thing scored worse.** Same
inversion `sabotage_control_check.py` recorded about its UNIQUENESS guard. Both
spellings are fixtures now. `CRITERIA_VERSION` is stamped so a future widening
is visible rather than silent.

The locator has been wrong three times in the other direction and that is
recorded too: UNLOCATED read 57, then 22, then 8, then 0, as four distinct
serving shapes were added. **A 0 in that column means "no fifth shape has been
introduced yet", not "the parser is finished."**

---

## RESULT — phases 1 and 2 are built (2026-09-21, Hank)

**49 of 84 Tier A resources now have a genuine cross-tenant isolation test**, up
from 0 when this was scoped. `api/sd-data-cross-tenant-dispatchers.test.js`,
112 assertions, **18 of 18 sabotages caught** across every dispatcher, with
`api/sd-data.js` restored byte-identical after each. Re-measure with
`python tools/cross_tenant_isolation_scope.py --plan`; do not quote the figure
from here.

**Read this before starting phase 3**, because three things below contradict
what is written above them.

### The grader had to be fixed first, and that was not optional

CC's review of the reference implementation found that the scanner **graded the
reference WEAK** — `_REFUSAL` matched a status code and a bare length check and
had no expression for a content assertion, which is the shape a *list* read
must use. Every phase-1 and phase-2 unit, done correctly, would have landed as
WEAK and this plan's own progress measure would have read zero while the work
was being done properly. Three more findings came with it: the self-check was
anchored on the old reference only, the grader's own control file was counted
as platform coverage, and a file-level GENUINE was crediting resources its
genuine arm never touched. All four are fixed; see the commit.

### Per-resource coverage is now DECLARED, not inferred

A file says what its arms cover:

```
// CROSS-TENANT-ISOLATION: law_invoices, law_opaccounts, law_barcerts
```

Cross-checked, never trusted: a file that declares and does not grade GENUINE
credits nothing; a file that grades GENUINE and declares nothing credits
nothing and is disclosed. **Two proximity heuristics were tried first and both
scored the better-structured test worse** — a parameterised suite declares its
resources in a table and drives them in a loop, so no line-window can attribute
an arm to a name. `none (<reason>)` is a declaration too, for a genuine test
whose subject is not Tier A.

**The control now checks the signature**: every declared resource must appear in
the suite's own `UNITS` table. That arm immediately caught `sd_quote_requests`
declared and never driven — it has its own named branch and belongs to phase 3.

### One file, not ten — a deliberate departure from the phasing above

The plan said one unit per claim, one file each. Driving the dispatchers showed
they differ only in the owning app, the session role and the id column. **The
mock is the test**, and ten near-identical files would be ten places for it to
drift. One harness, one mock, ten configurations keeps the load-bearing property
where a single sabotage arm reaches it for all of them.

### Three things found while building, none of them fixed here

1. **`SF_RESOURCES` has no session gate at all.** `sf_accounts`, `sf_ledger` and
   `sf_vendor_prices` — money — are authorised by the **licence alone**;
   `sairnfreedom` is not even in `api/_lib/auth.js`'s `ROLES_BY_APP`, so no
   session token can be signed for it. Same shape the defect register already
   carries for `law_trusttx`. Isolation is asserted; *who may call* is a
   separate question and a separate finding.
2. **`sv_controlled` WRITE is not covered**, and says so in the file. The
   controlled-substance register needs a witness co-signature from
   `api/sv-witness.js`; forging one in a test would be forging the control.
   READ isolation is covered.
3. **Six write arms could not reach the conflict key on the first run** — a
   coverage rule needs a payer, a denial needs a stage, a timesheet needs a real
   Monday. Each is now given the minimum its validator demands. **An arm that
   still cannot get through is reported `UNREACHED`, never passed**: a write arm
   that silently never ran is indistinguishable from one that ran and found
   nothing.

### What remains

35 resources, all phase 3–5, all **own-branch** — no dispatcher leverage left.
The 11-unit ratio that justified doing dispatchers first is spent: the tail is
roughly one unit per resource. Re-derive the case for it against a fresh number
rather than against the one at the top of this document.
