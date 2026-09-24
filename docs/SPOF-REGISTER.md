# Single points of failure — named, owned, and retired by MEASUREMENT

**Hand-written on purpose. `python tools/dependency_graph.py --register` checks it against the live graph and never rewrites it** — the owner, the mitigation and the judgement about whether a chokepoint *should* exist are not derivable from a graph. Same shape as `docs/CRITICALITY-TIERS.md` and `docs/SOUP-REGISTER.md`: the measurement is generated, the judgement is written down.

## Why this exists rather than a one-off report

Item 88 produced a single-point-of-failure list. **A list generated once and filed is a document**, and a document nobody re-measures is a claim with a date on it. What is wanted — Michael's framing, 2026-09-14 — is a **live, shrinking list**: every chokepoint named, owned, and **retired visibly when a real fix lands**.

So the checker runs in **both directions**, and the second one is the half that keeps it honest:

| The check | Why it is there |
|---|---|
| A component at or above the threshold with **no row** | An unregistered single point of failure is the thing this register exists to prevent |
| A row marked **OPEN** whose component is no longer above the threshold | The fix landed and nobody moved the row, so the list stopped shrinking where it should have |
| A row marked **RETIRED** whose component is **still** above the threshold | **The sharp one.** A retirement that did not happen is how a register becomes a reassuring lie. **Retirement is a measurement, not a decision somebody makes.** |
| A row with no owner | An unowned entry is a note |

## The baseline, frozen

**BASELINE: 11 components at or above the threshold on 2026-09-14, the day this register opened.**

JWST tracked 344 single-point failures, and the number is remembered because it never moved: every retirement was read against the SAME total, so progress was a fraction rather than an anecdote.

This page counted OPEN / ACCEPTED / RETIRED from day one, and that is a **snapshot**. Without a frozen denominator, *"7 OPEN"* a year from now cannot be told from *"7 OPEN"* today — **a register that shrank by four and one that never moved print the same line.** So the opening total is written here once and every `--register` run reports today against it.

**The line above is a historical fact and must not be edited.** `python tools/dependency_graph.py --register` **refuses** when it is missing, rather than defaulting to today's count — a default would silently make progress zero forever, which is the most flattering possible failure.

Raising the threshold would also shrink this list without a single fix landing. The threshold lives in one place (`SPOF_THRESHOLD`) for exactly that reason, and moving it invalidates the baseline: **change one and the other must be re-derived in the same commit.**

## 11 → 32, and 19 of those 21 are NOT growth — measured 2026-09-23

**The baseline line above is unchanged and must stay that way.** What follows is
the reading of it, because *"21 more"* is the kind of number that gets quoted as
decay when most of it is the instrument improving.

| | count | what it is |
|---|---|---|
| **A gap in the baseline itself** | **19** | `api/_resources/index.js` and the eighteen app registries. Created **2026-08-21**, and **21 registry files were already on disk on 2026-09-14**, the day the baseline was taken — checked with `git ls-tree` at that commit, not assumed. They were above the threshold then and were not counted. |
| **Genuine growth** | **2** | `env:SD_AUTH_SECRET_PREVIOUS` and `env:SD_ENCRYPTION_KEY`, both added to `api/_lib/auth.js` on **2026-09-17**, three days after the baseline. |

**So the platform acquired two chokepoints in nine days and the register
discovered nineteen it had always had.** Those are different facts and only one
of them is about the platform getting worse.

**WHY THIS IS NOT A REASON TO RE-BASELINE.** The frozen denominator exists so
progress is a fraction against a fixed total, and moving it to make the
arithmetic tidy is exactly what it was frozen to prevent. The honest record is
a baseline of 11 with a written note that it undercounted by 19, which is what
this section is.

**WHAT IS NOT ESTABLISHED:** *why* the baseline missed them. The graph may not
have traversed `api/_resources/` then, or the register may have been written
from a partial run. Nothing here determines which, and the distinction matters
for whether other components are still uncounted today.

### The retirement schedule — every OPEN row, what retires it, and when it is next looked at

**No row has moved to RETIRED since this register opened.** That is not the
checker failing — it refuses RETIRED while the component is still above the
threshold, so a retirement has to be a real fix.

**THIS TABLE IS THE SCHEDULE, AND THE CHECKER HOLDS IT IN BOTH DIRECTIONS
(item 91, 2026-09-25).** Every OPEN row must appear here with an owner and a
next-review date; a schedule row whose component is no longer OPEN is refused,
so retiring or accepting a row FORCES its schedule line out — the shrink is
visible in this table, not only in a count. The dates below are the cadence
the register runs on until its owner moves them; moving one is a one-cell
edit and a deliberate act, which is the point — a review that never happens
and a review nobody scheduled used to print the same nothing.

| OPEN row | What retirement requires | Owner | Next review |
|---|---|---|---|
| `env:SUPABASE_URL`, `env:SUPABASE_SERVICE_ROLE_KEY` | Splitting the single Supabase project, or per-app credentials against it. **A product and spend decision, not an engineering task**, and it is dispatched as one decision with items 61 and 69 in `docs/SAIRN-OPEN-WORK-INDEX.md`. | **Michael** | 2026-10-08 |
| `env:SD_AUTH_SECRET` | Per-app signing keys. The overlap window (2026-09-17) removed the rotation COST but not the concentration — one secret still signs every app's sessions. | **Michael** | 2026-10-08 |
| `env:SD_ENCRYPTION_KEY` | Per-tenant or per-purpose keys, so one leak is not every firm's second factor. The revoke procedure is drafted (`docs/2026-09-24-sd-encryption-key-revoke.md`) and unrehearsed, which is why this one reviews FIRST. | **Michael** | 2026-10-01 |
| `env:OIDC_CLIENT_ID`, `env:OIDC_CLIENT_SECRET`, `env:OIDC_ISSUER_URL`, `env:OIDC_REDIRECT_URI` | One risk seen four times. Retirement means a second identity provider or a documented fallback, not four separate fixes. Reviewed last of the eight: three of the four are misconfiguration exposure, not credential exposure. | **Michael** | 2026-10-22 |

**None of these is retirable by editing this file**, and that is the point of
recording them here: the list shrinks when the platform changes, and until then
a row saying OPEN is telling the truth. **A PAST-DUE DATE IS PRINTED LOUDLY
AND DOES NOT FAIL THE CHECK**, deliberately: failing a push because a calendar
date passed punishes whoever pushes next for a review someone else owes, which
is how a date column gets set to 2099. What DOES fail is structural drift —
an OPEN row this table forgot, or a schedule line for a row that is no longer
OPEN.

## The threshold, and what the number means

**Blast radius ≥ 10 production modules** (`SPOF_THRESHOLD` in `tools/dependency_graph.py`). Blast radius is how many modules **transitively require** the component — how many stop working if it does. 144 production modules are in the graph, so ten is roughly 7%.

**Test files are excluded.** 157 of the 303 `.js` files under `api/` are `*.test.js`; counting them makes "42 modules stop working" mean *CI stops* while being read as *production stops*. Same node, both populations: `api/_lib/license.js` is **42 in production and 82 with tests included**.

**A threshold is a policy, not a classifier.** It is named in one place so that moving it is a visible act rather than a quiet one.

## What this register cannot see, said before the table rather than after

The graph is `require()` edges and `process.env` reads. It does **not** contain:

- a runtime call that is not a require — one endpoint fetching another over HTTP is a real dependency and is invisible;
- the app HTML files, which reach the API over HTTP;
- whether a dependency sits on a hot path or in a branch that never runs.

**And the rows below are fewer risks than they are rows.** `env:SUPABASE_URL` and `env:SUPABASE_SERVICE_ROLE_KEY` are one risk seen twice; the four `OIDC_*` variables and `api/_lib/auth.js` are one risk seen five times. Counting rows as risks would overstate this page by a factor of two. The **Same risk as** column says which.

## Status vocabulary

| Status | Means |
|---|---|
| **OPEN** | A real concentration nobody has mitigated. Must currently be above the threshold. |
| **ACCEPTED** | Deliberate, with a stated reason and a compensating control. **Not a weakening** — one auth implementation is exactly what `item 94` argued for, and calling it a defect because its blast radius is wide would be the analysis leading the judgement. Exempt from the shrink rules and from nothing else. |
| **RETIRED** | Measured back below the threshold. The checker refuses this while the component is still above it. |

---

## The register

Measured 2026-09-14 against `tools/dependency_graph.py` (module + environment graph, production modules only). **Updated the same day when `--register` refused a run: `api/_lib/calendar-date.js` crossed the threshold from another session's work and had no row. The refusal is the first thing this page did that a static document could not.**

| Component | Owner | Status | Blast | Same risk as | What it is, and what would have to change |
|---|---|---|---|---|---|
| `env:SUPABASE_URL` | **Michael** | OPEN | 70 | — | **The widest concentration on the platform by a factor of 1.7, and the only one with a live incident behind it.** One Supabase project holds every app's data, and 70 of 144 production modules read it. On 2026-09-14 two hourly crons and `/api/claude` all returned 504 in the same minute because they were contending on it — see the cron-collision row in the open-work index. **Mitigating this is a spend and an architecture decision, not a code change:** it is the same question `docs/2026-09-14-backup-restorability-scoping.md` is blocked on. Recorded here so the two are not answered separately. |
| `env:SUPABASE_SERVICE_ROLE_KEY` | **Michael** | OPEN | 70 | `env:SUPABASE_URL` | **One risk seen twice, not a second risk.** Every module that reads the URL reads the key; `{env:SUPABASE_SERVICE_ROLE_KEY, env:SUPABASE_URL}` is a minimal 2-cut precisely because neither is ever read without the other. Listed separately because a credential and an endpoint fail for different reasons — a rotation breaks one and an outage breaks the other — and the mitigations differ even though the blast radius does not. |
| `api/_lib/license.js` | CC | ACCEPTED | 42 | — | **One place decides whether a licence is valid, and that is the design.** 42 modules route through it. The alternative — every endpoint re-deriving licence validity — is the exact shape `item 94` found in SAIRNcash, where five files re-derived "is Stripe configured" and three disagreed about the same environment. **Compensating control:** it is a pure gate with no state of its own, and its failure mode is closed (a licence that cannot be validated is refused, not accepted). **What would change this:** nothing should. It is listed so its width is a known fact rather than a surprise. |
| `env:SD_AUTH_SECRET` | **Michael** | OPEN | 34 | `api/_lib/auth.js` | **The session-signing secret for every app.** Its blast radius is `auth.js`'s plus one, because `auth.js` is the only reader. **A rotation invalidates every live session on every app at once** — there is no per-app key and no overlap window, so the blast radius is also the size of the logout. That is the concrete thing to fix, and it is a decision about session design rather than a bug. |
| `env:OIDC_CLIENT_ID` | **Michael** | OPEN | 34 | `api/_lib/auth.js` | One of four OIDC variables read only by `api/_lib/auth.js`; the four are one configuration, not four risks. Listed individually because a register that silently collapses them would hide a change to only one. |
| `env:OIDC_CLIENT_SECRET` | **Michael** | OPEN | 34 | `api/_lib/auth.js` | See `env:OIDC_CLIENT_ID`. This is the one of the four that is actually a credential, and the only one whose exposure is a security event rather than a misconfiguration. |
| `env:OIDC_ISSUER_URL` | **Michael** | OPEN | 34 | `api/_lib/auth.js` | See `env:OIDC_CLIENT_ID`. |
| `env:OIDC_REDIRECT_URI` | **Michael** | OPEN | 34 | `api/_lib/auth.js` | See `env:OIDC_CLIENT_ID`. |
| `api/_lib/auth.js` | CC | ACCEPTED | 33 | — | **One session/token implementation shared by every app, and that is deliberate.** This is the "one deep module" principle the platform has already applied twice this week. **Compensating control:** `api/_lib/auth.test.js` exists and the module fails closed — an unverifiable token is no session, not a session. **Why it is on this page anyway:** a bug here is a bug in 33 endpoints simultaneously, which is a fact about how carefully it must be changed rather than an argument for duplicating it. |
| `api/_lib/calendar-date.js` | CC | ACCEPTED | 20 | — | **Added to this register by the register, not by a person** — it appeared above the threshold on 2026-09-14 with no row, and `--register` refused the run until one was written. That is the mechanism working on its first real test rather than on a fixture. **What it is:** one module owning *what is a calendar date, and how do two of them compare*, from item 94. **It is ACCEPTED for the reason it exists:** `isDate` was defined FOURTEEN TIMES across `api/`, byte-identical and all wrong the same way — the failure mode of copying rather than importing, where one fix would have been fourteen. A wide blast radius here is the *point*: it is the number that used to be fourteen separate radii nobody could see. **Compensating control:** it is a pure function with no state and no I/O, and its failure mode is a refusal rather than a wrong date. **What would change this:** nothing should; it is listed so its width is a known fact rather than a surprise the next time somebody reads the graph. |
| `api/_lib/employee-lifecycle.js` | CC | ACCEPTED | 13 | — | The shared credential-deactivation lifecycle — `set_active`, last-admin refusal, no self-deactivation, deactivated-caller re-check. **Shared on purpose:** the same gap was found and fixed independently in three apps before this existed, which is the argument against thirteen copies. **Compensating control:** `sairn-app-scaffold` names this lifecycle as required in v1, so a new app inherits it rather than re-deriving it. |
| `api/_resources/index.js` | **CC** | ACCEPTED | 46 | — | **THE REGISTRY LAYER, AND THE EIGHTEEN ROWS BELOW ARE ONE RISK SEEN NINETEEN TIMES.** It `require()`s all eighteen app registries at load and merges them, so every module that reaches any registry reaches all of them and their blast radii are the SAME 46-47 modules — not nineteen independent concentrations. Listed separately because the checker works per component and a row is what makes each one visible; read as one. **ACCEPTED rather than OPEN, and the reason is the opposite of the Supabase rows':** this layer EXISTS to be a chokepoint. `api/sd-data.js` used to carry one shared RESOURCES map that every app appended to, and it was the cause of every merge conflict on that file; splitting it per app and merging at load is the fix. The compensating control is `api/_resources/app-boundary.test.js`, which drives the real handler and refuses a cross-app resource. **WHAT WOULD HAVE TO CHANGE:** nothing, unless the merge itself gains logic that can fail. A registry that only declares names cannot break at runtime in a way a test does not catch; the day it computes something, this becomes OPEN |
| `api/_resources/sairnbiz.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnbiz's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairnbuild.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnbuild's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairncare.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairncare's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairncash.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairncash's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairncode.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairncode's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairndental.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairndental's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairndesign.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairndesign's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairnfreedom.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnfreedom's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairngrounds.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairngrounds's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairnlaw.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnlaw's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairnlegacy.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnlegacy's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairnmechanical.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnmechanical's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairnroofing.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnroofing's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairnscape.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnscape's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairnsenior.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnsenior's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/sairnvet.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares sairnvet's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/shared.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares shared's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `api/_resources/stonedesk.js` | **CC** | ACCEPTED | 47 | `api/_resources/index.js` | **One of the eighteen — see the index row above.** Declares stonedesk's resource names and is merged at load. Blast 47 is the registry layer's radius, not this file's own | 
| `env:SD_AUTH_SECRET_PREVIOUS` | **Michael** | ACCEPTED | 35 | `env:SD_AUTH_SECRET` | **THE OUTGOING SIGNING KEY, AND ITS PRESENCE IS A MITIGATION RATHER THAN A RISK.** Accepted on verify and never used to sign (`api/_lib/auth.js:365`); it is the overlap window that removed the universal-logout cost from rotating `SD_AUTH_SECRET`. Blast 35 is `api/_lib/auth.js`'s radius, shared with every secret that module reads. **ACCEPTED, not OPEN:** its ABSENCE is the normal state — it is set only during a changeover and cleared after one `SESSION_TTL_MS` — so it cannot be a standing single point of failure. **WHAT WOULD CHANGE IT:** being left set permanently, which keeps a retired key valid forever. Nothing currently checks that it was cleared |
| `env:SD_ENCRYPTION_KEY` | **Michael** | OPEN | 35 | — | **NOT a duplicate of the signing secret — it was SPLIT OUT of it on 2026-09-17 so that a session-signing leak would stop also decrypting secrets at rest.** AES-256-GCM key for attorney MFA/TOTP secrets and a stored Stedi API key. Blast 35 is `api/_lib/auth.js`'s radius. **OPEN BECAUSE THERE IS NO REVOKE:** a leak decrypts every ciphertext already written, and those sit in Supabase whether the key changes or not — containment is re-enrolling every attorney MFA secret and rotating the Stedi key at Stedi. **WHAT WOULD HAVE TO CHANGE:** per-tenant or per-purpose keys, so one leak is not every firm's second factor. **AND ONE THING IS NOT ESTABLISHED:** whether it is SET in Vercel at all. `api/_lib/auth.js` says *“until `SD_ENCRYPTION_KEY` is set this deploy changes nothing”* — if unset, the duty is still `SD_AUTH_SECRET`'s and this row describes a split that has not happened in production |

**Nothing is RETIRED yet.** That is the honest state on the day the register was created, and it is stated rather than left as an empty section somebody reads as "all clear".

---

## How to retire a row

1. Land the change that reduces the concentration.
2. Run `python tools/dependency_graph.py --register`.
3. If the component is still at or above the threshold, **the checker refuses the retirement** and says the current number. That refusal is the feature.
4. When it is genuinely below, change the status to `RETIRED`, **leave the row in place**, and add what was done and the measured before/after to the last column.

A retired row is never deleted. The value of this page after a year is the list of concentrations that *were* fixed, with the numbers that prove it.
