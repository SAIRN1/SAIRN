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

**Nothing is RETIRED yet.** That is the honest state on the day the register was created, and it is stated rather than left as an empty section somebody reads as "all clear".

---

## How to retire a row

1. Land the change that reduces the concentration.
2. Run `python tools/dependency_graph.py --register`.
3. If the component is still at or above the threshold, **the checker refuses the retirement** and says the current number. That refusal is the feature.
4. When it is genuinely below, change the status to `RETIRED`, **leave the row in place**, and add what was done and the measured before/after to the last column.

A retired row is never deleted. The value of this page after a year is the list of concentrations that *were* fixed, with the numbers that prove it.
