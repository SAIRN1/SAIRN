# SAIRN Open Work Index

**One place to see everything that is open across the whole platform.**
Last rebuilt: **2026-08-23**, at repo HEAD `2304054`.

Before this file existed, open work lived in `SAIRN-BACKLOG.md`, in
`SAIRN-ACTIVE-WORK.md`, in ~40 per-app handoffs, and in skill files — so real
items got missed and sessions sat idle while work existed. This is the index.
It does not replace those files; each row points back at the source of truth.

---

## How to use this in 30 seconds

1. Filter by **Owner** — `unassigned` rows are the ones a free session can take.
2. Skip anything whose **Blocked by** is not empty unless you can clear the block.
3. Do what **Next action** says. If it says *verify*, the row's status is a claim
   that has not been re-checked; verify before building on it.

**Every row is a claim, not a fact.** Same standard as a handoff: re-verify
before you act on one. Rows marked ⚠️ are ones this rebuild could not confirm.

---

## Open items

Legend — **Sz**: S = under a session, M = one session, L = multi-session.

| App | Item | Status | Owner | Blocked by | Next action | Sz |
|---|---|---|---|---|---|---|
| **SAIRNbuild** | Zero server-side backup for any real business data | Open | unassigned | — | Scope the resource set, then add to `api/sd-data.js` allowlist + schema. Largest single item in the backlog | L |
| **Platform** | No app clears local data on a license/device re-key; storage keys are not license-scoped | Open | unassigned | — | Decide scope (all 13 apps or lead app first), then namespace keys by license hash | L |
| **Platform** | No delete capability via `api/sd-data.js` for any resource, any app | Open | unassigned | — | Design soft-delete vs hard-delete, then one handler | M |
| **SAIRNlaw** | AI Chain of Custody gap 2: `matter_id` is an unvalidated localStorage id | Open (gap 1 closed) | unassigned | `law_matters` must be server-backed first | Blocked — do the SAIRNlaw server-sync item first | M |
| **SAIRNlaw** | `law_check_and_insert_disbursement` can return a null row on a cross-client `trusttx_id` collision | Open ⚠️ | unassigned | — | The idempotency lookup keys on `(license_hash, trusttx_id)` and does **not** filter by client. Verify a cross-client collision reproduces, then add the client predicate | S |
| **SAIRNlaw** | `ai_list` derived-status window can go stale at high license-wide volume | Open (accepted nit) | unassigned | — | Per-license row-count or per-entry status query. Fails safe toward `Unreviewed`, never fabricates a status | S |
| **SAIRNlaw** | `public.canlii_rate_limit_log` has nothing writing to it since CanLII was deleted (`b747ecb`) | Open | **Michael** | Needs Supabase schema owner | Decide drop vs leave. Destructive on a shared DB, deliberately not done by a session | S |
| **SAIRNlaw** | Illinois holiday list: statute (205 ILCS 630/17) vs court-observed (M.R. 5272) disagree both ways | Open — legal judgment | **Michael** | Needs a lawyer's read | Confirm the statutory list is the right basis for 5 ILCS 70/1.11. Encoded that way; changes real dates (Good Friday, Pulaski Day) | S |
| **SAIRNlaw** | Deadline engine coverage: 7 of 50 states | In progress | **Hank** | — | Batch 1 order is IL ✅ → FL ✅ → **CA next**. Then re-decide: more states, or a third domain | L |
| **SAIRNlaw** | Court e-filing: readiness check built, transmission not possible | Closed as scoped | — | EFSP certification is a contract, not code | Nothing to build. Revisit only if an EFSP relationship is pursued | — |
| **StoneDesk** | ~28 `sdDemoCleared() ? [] : SEED` fallback sites unaudited (Slabs fixed in `501d15b`) | Open ⚠️ | unassigned | — | Count is `grep -c` measured, not authoritative — Guardian's note says 29 constants / 56 sites. **Re-count precisely first**, then apply the two-part test per site | L |
| **StoneDesk** | Procedural stone texture likely inflates `canvas.toDataURL()` PNG snapshots against an existing quota risk | Open | unassigned | — | Measure a real textured snapshot's byte size before changing anything | M |
| **StoneDesk** | Saved-quote Load: overwrite confirm fires on a merely-opened Drawing Tool tab | Open | unassigned | — | Gate the confirm on actual unsaved drawing state | S |
| **StoneDesk** | `dcMode` doesn't reset to `preset` on a same-session Custom-Draw-then-preset quote Load | Open | unassigned | — | Reset `dcMode` in the Load path | S |
| **StoneDesk** | Stone-texture visualization — accepted cosmetic nits | Open (accepted) | unassigned | — | None unless a client raises one | S |
| **SAIRNbiz** | AP "Pay" button doesn't mark anything paid | Open | unassigned | — | Real status write + server sync | M |
| **SAIRNbiz** | No way to update a training cert's status at all | Open | unassigned | — | Add status transition + persistence | M |
| **SAIRNbiz** | Budget "actual" spend never syncs with recorded expenses | Open | unassigned | — | Derive actuals from the expense store rather than a separate field | M |
| **SAIRNbiz** | Payroll runs are never recorded anywhere | Open | unassigned | — | Persist a payroll-run record | M |
| **SAIRNbiz** | Benefits panel has no way to enroll anyone | Open | unassigned | — | Enrollment write path | M |
| **SAIRNdental** | Real-sync sweep can silently exhaust localStorage once photo-bearing bookings accumulate | Open | unassigned | — | Quota guard + honest failure. Silent-failure class — treat as higher priority than its size suggests | M |
| **SAIRNdental** | `public-book.js` returns a generic 502 on a real slot race instead of 409 `SLOT_TAKEN`, and orphans a patient record | Open | unassigned | — | Distinguish the race, return 409, clean up the orphan | M |
| **SAIRNdental** | Pediatric guardian fields: `onPtDobChange()` not called at page init | Open | unassigned | — | Call it on init | S |
| **SAIRNdental** | Per-patient photo history panel | Open (feature) | unassigned | — | Scope before building | M |
| **SAIRNdental** | Vendor/supply ordering — deferred whole-branch-review items | Open | unassigned | — | Re-read the review list, triage | M |
| **Tooling** | Rebuild graphify's knowledge graph, properly scoped | Open | unassigned | — | Decide scope first; the last attempt was unscoped | M |
| **Platform** | `C:\Users\marsh\` is itself a working-tree checkout of the repo, 33+ commits behind | Open | **Michael** | Needs repo/clone-setup owner | Retire it as a checkout. Complication: it is also the user-level skill store, so the store must move too | M |
| **SAIRNlaw** | `CANLII_API_KEY` | **Closed** | — | — | No longer a blocker — Canada is out of scope and the code is deleted | — |

---

## Recently closed (kept briefly so nobody re-opens them)

| App | Item | Closed | Evidence |
|---|---|---|---|
| SAIRNlaw | Trust disbursement cross-device atomic check | 2026-08-17/18 | `law_check_and_insert_disbursement` live in `api/sd-data.js` + `sql/sairnlaw_trust_disbursement_atomic_check.sql`; 4 `law_` resources in the allowlist. **`SAIRN-BACKLOG.md` still lists this as open — that entry is stale.** |
| SAIRNlaw | Void-of-deposit could retroactively negative a client balance | 2026-08-17/18 | `law_check_and_void_deposit`, browser-verified |
| SAIRNlaw | CanLII / Canada coverage | 2026-08-23 | `b747ecb` — deleted, live-verified |
| SAIRNlaw | Court e-filing (Ohio-first) | 2026-08-23 | `a183a07` — readiness check; transmission scoped out with reasons |
| SAIRNlaw | Deadline engine: Illinois | 2026-08-23 | `b8250a2`, 39/39 isolation + live-loaded |
| SAIRNdesign | Invoicing server-side uniqueness constraint | 2026-08-10 | Backlog marked resolved |
| SAIRNlegacy | Merchandise reservation server-side lock | 2026-08-10 | Backlog marked resolved |
| StoneDesk | Saved quote history didn't capture drawing-tool state | 2026-08-13 | Backlog marked resolved |
| StoneDesk | `SD-AUDIT-2026` credential blocker | 2026-08-23 | CC — fixed and verified |
| Guardian | `vercel_config_check` false 404s, `nav_panel_check` conventions, dead Check 23 | 2026-08-23 | `158999f` — 12/12 apps pass |

---

## What this index does NOT cover, stated so the gap is known

- **Per-app handoffs were not read line by line.** Rows come from
  `SAIRN-BACKLOG.md` (section-by-section), `SAIRN-ACTIVE-WORK.md`, and work
  done in-session on 2026-08-23. There are ~40 handoff files; an item that
  exists **only** inside one and never reached the backlog is not here yet.
  That is the first thing to improve on the next rebuild.
- **Sizing is judgment, not estimation.** S/M/L is a rough shape, not a
  commitment.
- **Owners are observed, not assigned.** `unassigned` means no session has
  claimed it in `SAIRN-ACTIVE-WORK.md` — not that it is unimportant. Rows
  owned by **Michael** need a decision or an access level a session does not
  have.
- **⚠️ rows carry a number or claim this rebuild could not confirm.** They say
  so in Next action.

---

## Keeping it alive

This file rots the moment it stops being updated, and a stale index is worse
than none — it makes work look handled when it is not.

1. **When you close something, move the row** to *Recently closed* with the
   commit SHA. Do not delete it silently.
2. **When you find something new, add a row** in the same action as logging it
   in `SAIRN-BACKLOG.md`. Two places, one action, or they diverge.
3. **Re-derive, don't trust.** Before a planning decision, spot-check the rows
   you are about to rely on. This rebuild found one stale backlog entry
   (SAIRNlaw trust disbursement, listed open, actually shipped) out of 26 —
   assume a similar rate next time.
4. **Do not renumber or restructure the backlog to match this file.** The
   backlog is the detailed record; this is the index over it.
