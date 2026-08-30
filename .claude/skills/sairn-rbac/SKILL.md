---
name: sairn-rbac
description: Per-employee role-based access control for multi-tenant apps that share one backend. Every rule here comes from a failure that shipped and was found live across thirteen SAIRN apps — the cross-app role collision, the last-admin lockout that stranded a real licence, the session that outlived its own deactivation. Trigger before writing or reviewing ANY auth branch, role check, session verification, provisioning flow, or credential-lifecycle action; before adding a role to any app's vocabulary; and any time a role name, table name, or session token is shared by more than one app.
allowed-tools: Read Grep Glob Bash
---

# SAIRN RBAC

Access control for a fleet of apps on one backend and one session library.

**Every numbered rule below is a bug that shipped, not a principle.** Where a
rule looks obvious, it is there because the obvious thing was got wrong anyway,
and the note says how.

**Installed 2026-08-30.** Rebuilt as a SAIRN original from the settled
list in `docs/2026-08-30-skill-rebuild-classification.md`. Every factual claim
machine-verified against this codebase before install.

---

## 0. The shape of the problem, because it is not the usual one

Thirteen apps share `api/_lib/auth.js`, one Supabase project, and one session
token format. They do **not** share a role vocabulary. `'owner'` is a real role
in most of them and means something different in each.

That single fact produces most of what follows. A role check that is correct
inside one app is not automatically correct when the token came from another.

## 1. A role check must verify WHICH APP the session is for

`verifySessionToken(token, license_hash, expectedApp)` takes three arguments.
The third is not optional and is not decoration.

**What happened.** Building StoneDesk's per-employee RBAC (2026-08-03),
`api/sd-data.js`'s employees WRITE branch trusted a client-supplied
`body.app_id === 'sairnbiz'` with **zero verification** — any holder of a shop's
licence key could set that field.

**Then the fix shipped with the same bug class twice more in the same session.**
`sd-auth.js`'s `setup` action and `sd-data.js`'s employees READ gate both called
`verifySessionToken(token, hash)` **without** the third argument. Since `'owner'`
is a valid role in both StoneDesk's and SAIRNbiz's vocabularies, a valid
SAIRNbiz owner token would have passed StoneDesk-only checks.

Caught by manual self-review before push. Nothing automated saw it.

**Mechanically:** `.semgrep/verify-session-token-app-scope.yml` now blocks any
two-argument call. Run it. A grep for `verifySessionToken(` with a manual read
of every call site is the fallback, not the plan.

**The generalisation, which is the part worth carrying:** anywhere a role name,
table name, or credential value is shared across apps, verify it is *explicitly
scoped* — not that the value happened to match. A shared name without a scope
check is an auth bypass waiting to be found by someone else.

## 2. Never trust a role, app id, or tenant id from the request body

The client sends *which* record to act on. It never sends *who it is* or *what
it may do*. Both come from the verified token.

Corollary that has bitten: hiding a button is UX, not enforcement. Every SAIRN
card that hides itself for a non-manager says so in its own comment, and the
server re-checks regardless. If the only thing stopping an action is
`style.display='none'`, the action is unprotected.

## 3. Read the roster from the database, never from the request

Decisions about "is this the last admin", "does this employee exist", "what role
do they have" are made from a **single fresh read of the real roster**, never
from what the client claimed about the target or about who else exists.

## 4. The last-admin guard, and the lockout it exists to prevent

Deactivating the final provisioning-role credential leaves a licence that
**cannot log in, cannot run setup, and cannot re-bootstrap** — dead through the
API, recoverable only by direct database access.

**This is not hypothetical.** RF-PINNACLE-2026 was found live with zero active
owners and no API route back. Three StoneDesk licences were lost to untracked
credential state before `set_active` existed: SD-PINNACLE-2026's PIN is still
undocumented, SD-AUDIT-2026 needed a hand-written DELETE in Supabase, and
SD-PARTNER-2026 was provisioned purely to route around both.

**`bootstrap` must refuse once ANY row exists for the licence — not once any
ACTIVE row exists.** Making it fall back to "no active rows" would auto-heal the
lockout, and would also let anyone holding a licence key deactivate their way to
a fresh bootstrap and seize the account. The lockout is the lesser bug. Keep the
refusal and fix the cause.

**Keep the quarantined guard even when it is unreachable.** SAIRN's last-admin
check is provably unreachable while the caller-still-active check stands, since
an active caller plus a different active admin implies at least two. It stays,
because reachability is a property of *today's* rule set — a new provisioning
role or any path skipping that check makes it live again.

## 5. Deactivate. Never delete.

The row stays; only `active` flips. Login already filters `active=eq.true`, so
the flag is enforced the moment it is written.

Deleting is what made those three StoneDesk cleanups both unrecoverable and
unauditable. Keeping the row preserves `created_at`, role history and audit
linkage — and, where the credential is attached to a compliance record, deleting
the person deletes the evidence they were trained.

## 6. A session outlives its own deactivation. Re-check the caller.

Tokens carry a role claim and stay valid for their full life — **12 hours**
(`SESSION_TTL_MS` in `api/_lib/auth.js`). Deactivating a credential does not
invalidate tokens already issued from it.

So every privileged branch re-reads the caller's own row and refuses with
`CREDENTIAL_INACTIVE` if it is no longer active. Found live on SAIRNcode
2026-08-23 and carried to the others rather than rediscovered.

**Say the window out loud in the UI.** SAIRN's Access panels state that a
signed-in session can outlive a deactivation by up to 12 hours and that the
person should be confirmed signed out if access must end immediately. A silent
12-hour tail is the difference between "we removed their access" and "we
removed their access tomorrow morning".

## 7. Require a reason to remove access. Not to restore it.

Reactivating is self-explanatory and always safe. A **deactivation** is the
thing someone will be trying to reconstruct months later, so the reason is
mandatory, capped, and written to the audit log with the actor, target,
previous state, new state and remaining-admin count.

Audit the **refusals** too, not only the successes. SELF_DEACTIVATE and
CREDENTIAL_INACTIVE both write a `credential_change_refused` record — an
attempted lockout is exactly the event worth having.

## 8. Nobody deactivates themselves

Refuse with a distinct code and a message naming who *can* do it. This is the
one case the client may also gate (render no button on your own row), but the
server refuses regardless — the client gate is convenience, and the server's
answer is the one shown.

## 9. `unchanged: true` is a real answer. Report it as one.

Setting active to what it already is returns success **and says nothing
changed**. Dressing a no-op as a change is how a UI reports success for an
action that did not happen.

## 10. THE DIVERGENCE THAT BREAKS CLIENTS — read the app's own contract

**Five apps ship `set_active`. They do not agree, and the disagreement is
load-bearing:**

| App | `PROVISIONING_ROLES` | Refusal code | Response field |
|---|---|---|---|
| SAIRNdental (`dnt-auth`) | `['owner']` | `LAST_OWNER` | `remaining_owners` |
| SAIRNmechanical (`mech-auth`) | `['owner']` | `LAST_OWNER` | `remaining_owners` |
| SAIRNroofing (`rf-auth`) | `['owner']` | `LAST_OWNER` | `remaining_owners` |
| SAIRNcode (`sc-auth`) | **`['admin']`** | **`LAST_ADMIN`** | `remaining_admins` |
| StoneDesk (`sd-auth`) | **`['owner','admin']`** | **`LAST_ADMIN`** | `remaining_admins` |

Three different values across five apps, and the error code splits along the
same line.

**Read the server file you are writing a client for.** Copying a working panel
from another app prints `undefined active owners` on every success — and worse,
computes the wrong active-provisioner warning on StoneDesk, the one app where
*two* roles keep the licence reachable.

StoneDesk is also the only app where an `admin` can provision but **cannot mint
an Owner** — `sd-auth.js` refuses that specifically. A privilege-escalation case
that cannot arise in the other four.

## 11. Predict nothing client-side

Offer the button. Let the server refuse. Show **the server's message verbatim**.

A locally-computed admin count is a *warning beside the button*, never a gate —
this browser's roster can be stale and the server's cannot. The one exception is
self-deactivation (rule 8), and even that is belt-and-braces.

## 12. Credential mechanics that are already settled — do not re-litigate

- **PIN 6–8 digits**, never 4. Four digits is 10,000 combinations, guessable
  against a live endpoint even with lockout.
- **Lockout at 5 failed attempts**, uniform across every app.
- **Constant-time PIN verification.** When no matching employee exists, still
  run a hash against a fixed dummy salt — otherwise response time reveals which
  employee IDs are real.
- **The same generic error for wrong-PIN and no-such-employee.** Note the cost:
  it makes "is this credential live?" untestable from outside, which is why
  SAIRN keeps a documented recovery credential on a non-production licence
  instead of guessing.
- **`scrypt`, 64-byte, per-credential random salt.** A seeded credential must be
  produced by the app's own `hashPin()` and round-tripped through its own
  `verifyPin()` before being written anywhere.

## 13. Provisioning is a lifecycle, not a create form

Any app with per-employee credentials needs all of it in v1: grant, roster
(including deactivated people, or an owner cannot turn anyone back on), reason-
required deactivation, reactivation, last-admin refusal, self-deactivation
refusal, caller-still-active re-check, and an audit record on every outcome
including refusals.

Shipping grant without revoke is the state StoneDesk sat in for three weeks: a
card that could hand out sign-in and nothing in the app that could take it away.

---

## Before you call an RBAC change done

1. Every `verifySessionToken` call passes `expectedApp`. Semgrep clean.
2. No role, app id or tenant id is read from the request body for authorisation.
3. Roster read fresh from the database for every decision.
4. Last-admin and self-deactivate refusals return **and audit**.
5. Caller's own `active` re-checked on every privileged branch.
6. Field names and refusal codes read from **this app's** auth file.
7. Deactivation reason required, capped, audited. Reactivation needs none.
8. The 12-hour session window stated in the UI.
9. Round trip verified against the deployed endpoint — deactivate, confirm the
   account can no longer sign in, reactivate, confirm it can. A clean write is
   not evidence.

---

## What this does NOT cover

- **Any app's own role vocabulary.** It says read the app's auth file; it does
  not list the roles, because they diverge and a list here would go stale the
  first time one changes.
- **Authentication itself** — PIN hashing, session minting, WebAuthn. Rule 12
  states the settled mechanics so they are not re-litigated; the implementation
  lives in `api/_lib/auth.js`.
- **Row-level security in Postgres.** These rules govern the API gate. RLS is a
  second layer with its own file conventions.
- **Non-SAIRN authorisation models** — OAuth scopes, ABAC, policy engines.
  Everything here assumes one shared backend and per-employee credentials.

**Precedence.** Replaces the general `access-control-rbac`, which covers roles,
permissions and policies in the abstract. Use that one outside SAIRN. Adjacent
here: `sairn-guardian-v2` (checks 22/25/26/28 catch these mechanically),
`sairn-employee-auth-scaffold` (building the auth surface in the first place),
and `sairn-differential-review` (whether a diff touching an auth gate is safe).
