---
name: sairn-employee-auth-scaffold
description: 'How to add real per-employee authentication to a SAIRN app — PIN credentials, signed session tokens, failed-attempt lockout, and the credential-deactivation lifecycle — by reusing what thirteen apps already ship rather than hand-writing a fourteenth copy. Extracted 2026-08-27 from the real, live implementations, not designed from scratch. Trigger whenever a new SAIRN app needs employee login, whenever someone says "auth", "login", "PIN", "session token", "employee credentials", "roster", "deactivate an employee", "set_active", "whoami", "lockout", or "who can provision"; before writing any new api/*-auth.js; and before adding a *_employee_auth table. Also read it before changing api/_lib/auth.js, which all thirteen apps share. Companion to sairn-app-scaffold (which says the deactivation lifecycle is required in v1) and sairn-grant-sweep (which owns the grant lines these schemas carry).'
---

# Per-employee auth: reuse the thirteen, do not write a fourteenth

Thirteen SAIRN apps ship per-employee auth today. This skill exists so the
fourteenth costs an afternoon instead of a week, and so it inherits the fixes
the other thirteen paid for in production rather than rediscovering them.

**Read this before writing any `api/*-auth.js`.** The single most expensive
mistake available here is writing one from memory of "the pattern" — the
pattern has two generations, four real divergences that break clients, and one
decision (the bootstrap trapdoor, §5) that will permanently brick a customer's
licence if you get it backwards.

---

## 0. Two things that are already done — do not rebuild them

### 0.1 The crypto is shared. It is not per-app.

`api/_lib/auth.js` (639 lines) is required by **all thirteen** auth endpoints.
There is **zero** `scrypt`, `randomBytes`, `createHmac` or `timingSafeEqual` in
any endpoint file. If you find yourself importing `crypto` into an auth
endpoint, stop — you are about to fork something.

What it gives you:

| Export | What it does |
|---|---|
| `hashPin(pin)` | scrypt, per-credential random 16-byte salt → `{pin_hash, pin_salt}` |
| `verifyPin(pin, hash, salt)` | Constant-time. **Runs a full scrypt against a dummy salt even when no row was found** — see below |
| `signSessionToken({app, employee_id, role, license_hash})` | HMAC-SHA256 over a JSON payload, 12h TTL, `typ:'session'` |
| `verifySessionToken(token, license_hash, expectedApp)` | Checks signature, `typ`, app, role-validity, expiry, **and licence match** |
| `tokenFromRequest(req)` | Pulls the token out of `X-SD-Auth` |
| `ROLES_BY_APP` | Every app's role vocabulary, with per-app reasoning in comments |
| TOTP + OIDC helpers | Only SAIRNlaw uses these. Ignore unless building MFA/SSO |

**The `verifyPin` dummy-salt branch is load-bearing and is not an
optimisation.** From a real 2026-08-03 security-auditor finding: the original
short-circuited when no row was found, so a real `employee_id` took
scrypt-cost milliseconds to reject and an unknown one returned in under a
millisecond. That gap let an attacker enumerate valid employee IDs, then
brute-force PINs against only the confirmed-real ones. Never "optimise" it back.

### 0.2 Adding your app to `ROLES_BY_APP` is a real step, not boilerplate

`api/_lib/auth.js:44-165`. `signSessionToken` **throws** on an unknown app or a
role not in that app's list, so a missing entry fails loudly at first login.

Every existing entry carries a comment explaining where the role vocabulary came
from. Match that. Several say in terms *"Judgment call, not confirmed with
Michael ahead of building"* — that disclosure is the convention. Inventing a
role list silently is what cost SAIRNcare a scope correction.

---

## 1. The two generations — know which one you are copying

| | Generation 1 | Generation 2 |
|---|---|---|
| Files | `sd-auth.js`, `sd-sub-auth.js` | the other eleven |
| Table reference | Inlined at all nine call sites | `const TABLE` |
| App id | Literal `'stonedesk'` at each check | `const APP` |
| Helpers | None — every query written inline | `loadEmployee`, `patchEmployee`, `recordFailure`, `clearFailures`, `isLocked` |
| Diagnostics | Two-line `upstream()` stub | `NOT_PROVISIONED` / `NOT_GRANTED` branches |

**Copy generation 2.** The cleanest complete example is `api/rf-auth.js`
(SAIRNroofing) — it is the only endpoint with *both* `whoami` and `set_active`,
and it carried the caller-still-active fix from its first commit rather than
rediscovering it. Its own header says it was modelled on `api/alf-auth.js`.

Do not copy `api/sd-auth.js`. It is the ancestor everything cites, and it is the
one file whose header comment has drifted from its own code (`sd-auth.js:23-26`
still says "No lockout/rate-limit here yet"; lockout has been at `sd:171-200`
since 2026-08-03).

---

## 2. What is genuinely invariant — lift it verbatim

The 10-step prelude runs before any action, in this order, in all thirteen:

1. `req.method !== 'POST'` → 405
2. `Authorization: Bearer <licence key>` → missing → 401 `NO_LICENSE`
3. String body parsed as JSON → failure → 400
4. Action allowlist check
5. Env check (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SD_AUTH_SECRET`) → 500
6. `validateLicenseKey()` → `CONFIG` → 500, else → 502
7. `!lic.valid` → 401 `INVALID_LICENSE`; `!lic.active` → 403 `LICENSE_INACTIVE`
8. **`check_license` short-circuits here**, before `licHash`/`headers` exist
9. `licHash`, `headers`, `rest()`, `enc` defined
10. One `try { ... }` wrapping a flat sequence of `if (action === 'x')` blocks

Also invariant, and deliberately so:

- **`const pinOk = row ? verifyPin(pin, row.pin_hash, row.pin_salt) : verifyPin(pin, null, null);`** — byte-identical in every file.
- **One generic failure**: 401 `INVALID_CREDENTIALS` / `'Incorrect employee ID or PIN'`. Never tell the caller which half was wrong.
- **`LOCKOUT_THRESHOLD = 5`, `LOCKOUT_MINUTES = 15`** — identical in all thirteen.
- **Every REST query filtered `license_hash=eq.<licHash>`.** There is no unfiltered read anywhere. `license_hash` is also signed *into* the token and re-checked on verify, so a token minted for one licence cannot be replayed against another.
- **`expectedApp` passed on every session verification.** Without it a valid SAIRNbiz owner token would pass a StoneDesk owner check — `'owner'` exists in both role lists. Found while wiring the second app's mirror of the first's endpoint.

### The tenancy key is not per-app — a recurring false belief

`license_hash` is `sha256(license_key)` hex, derived **once**, in
`api/_lib/license.js:57`. Every endpoint does the identical
`const licHash = lic.license_hash;`. There is no per-app derivation, no
per-app branch, and no app that differs — this has been claimed and disproved
more than once. If someone tells you a specific app derives it differently, the
thing they are probably remembering is that **SAIRNcode owns the platform's only
DELETE path** (`SC_RESOURCES` in `api/sd-data.js`), which is a different table
and a grant question entirely.

---

## 3. Per-app parameters — the complete list

Everything else is these:

```js
const APP = 'sairnyourapp';                       // must exist in ROLES_BY_APP
const TABLE = 'sairnyourapp_employee_auth';
const ROLES = ROLES_BY_APP[APP];
const PROVISIONING_ROLES = ['owner'];             // who may mint credentials
const MANAGEMENT_ROLES = { owner: true, admin: true };  // who may read the roster
const BOOTSTRAP_ROLE = 'owner';
const AUDIT_TABLE = null;                         // or 'sairnyourapp_audit_log'
```

Plus the human-readable role nouns in error messages, and the `payload.app`
literal in the client's session-restore check.

**Export the tier constants.** `rf-auth.js:103-105` exports
`MANAGEMENT_ROLES`/`BROAD_READ_ROLES` specifically so gates elsewhere import
them instead of re-listing role names. That drift cost SAIRNsenior a real bug on
2026-08-20 when one function used `senIsManagement()` where the rest used
`senIsBroadRead()`.

**Then actually use `PROVISIONING_ROLES`.** Both `sc-auth.js:47-49` and
`sd-auth.js:42-45` state the reason for the constant — *"if this list ever
grows, that guard grows with it automatically"* — and then **use literals in
their own `setup` and `roster` gates anyway** (`sc:208`, `sd:228`, `sd:272`).
Only `set_active` uses the constant. `rf-auth.js` follows its own rule in all
three. Follow rf.

---

## 4. The action set — and which ones the platform actually skipped

| Action | Ships in | Build it? |
|---|---|---|
| `bootstrap` | 13/13 | Always |
| `login` | 13/13 | Always |
| `setup` | 13/13 | Always |
| `check_license` | 10/13 | Yes — see below |
| `roster` | 8/13 | Yes if you have `set_active`, which you should |
| `whoami` | 7/13 | Yes — see §6 |
| `set_active` | **3/13** | **Yes. This is the one everyone skips.** |

`check_license` exists so the licence-entry screen can confirm a key *before*
storing it — otherwise a bad licence key gets misattributed to a wrong PIN and
the customer chases the wrong problem. Missing from `grd`, `sb`, `scp`.

`roster` must include **inactive** rows. StoneDesk originally filtered
`active=eq.true` and flipped it on 2026-08-23: once `set_active` exists, an
owner has to be able to *see* a deactivated person in order to turn them back
on. And gate it — `sc-auth.js:238-248` denies its `auditor` role deliberately:
*"read-only on the app's DATA is its job; the credential roster is not data, it
is the access-control surface itself."*

---

## 5. The bootstrap trapdoor — get this backwards and you brick a licence

**`bootstrap` refuses once ANY row exists for the licence, and the existence
probe deliberately does NOT filter on `active`.**

This is the single most important decision in the whole pattern, and it is a
deliberate trade rather than an oversight. Read both halves:

- Deactivating the last owner produces a licence where nobody can log in, nobody
  can run `setup`, and `bootstrap` still 409s — permanently unusable through the
  API, recoverable only by direct database access. **That is exactly how
  SD-AUDIT-2026 was lost.**
- Changing `bootstrap` to fall back to "no *active* rows" would auto-heal that
  lockout — and would also let anyone holding the licence key deactivate their
  way to a fresh bootstrap and **seize the account**.

The existence check stays absolute. Recovery goes through another owner. The
protection against the lockout is the **last-admin refusal in `set_active`**
(§7), not a softer bootstrap.

Put the comment at the probe itself, the way `rf-auth.js:222-226` does, not
three hundred lines away at `set_active` — the probe is where someone will be
tempted to add `&active=eq.true`.

---

## 6. `whoami` — and the failure mode it exists to close

Only 7 of 13 have it. It re-checks two things: the token's own
signature/app/licence/expiry, **and then a real employee-row read filtered
`active=eq.true`**. It returns the role **from the database row, not from the
token**, so a role change via `setup` also takes effect on the next call.

Why it matters (`law-auth.js:24-36`, from a real 2026-08-18 finding): the page
load restored a cached token and trusted its decoded payload for the UI's
identity with no server round-trip, so **a revoked account could render as
logged in indefinitely.**

A session outlives its own credential's deactivation by **up to 12 hours**. That
one fact drives `whoami`, the caller-still-active re-checks, and §7.

---

## 7. The deactivation lifecycle — four rules, and a platform-wide gap

`sairn-app-scaffold` says this is **required in v1**. Here is the real state as
of 2026-08-27:

| Layer | Coverage |
|---|---|
| `active boolean not null default true` column | **12/12 schemas** |
| Login filters `active=eq.true` | **13/13 endpoints** |
| `set_active` server action | **3/13** (`rf`, `sc`, `sd`) |
| **Client UI that calls it** | **0/13 — zero callers in any `.html` on the platform** |

So today **no SAIRN app can deactivate a departing employee through its own
interface.** It takes a hand-written SQL edit, which is precisely the thing that
lost three StoneDesk licences (`sd-auth.js:304-308`). Build the endpoint *and*
the UI, or you have shipped the same gap.

### The guard ordering — copy it exactly

1. Token + provisioning-role gate → 403 `FORBIDDEN`
2. `employee_id` present → 400
3. `typeof body.active !== 'boolean'` → 400
4. `!nextActive && !reason` → 400 — **`reason` required only to deactivate.** Reactivating is self-explanatory and always safe; a deactivation is the thing someone reconstructs months later
5. `reason.length > 500` → 400
6. **Self-deactivation refusal** → 409 `SELF_DEACTIVATE`. The likeliest accidental route to a licence with zero active owners, and there is no legitimate reason to do it to yourself rather than have another owner do it
7. **One** roster read: `?license_hash=eq.<h>&select=employee_id,role,active`
8. **Caller-still-active re-check, computed off that read** → 403 `CREDENTIAL_INACTIVE`. Costs no extra query
9. Target exists? → 404 `NOT_FOUND`
10. **Last-admin refusal** → 409
11. `target.active === nextActive` → 200 `unchanged: true`
12. PATCH, recount, respond

Step 6 before step 7 is deliberate: an already-deactivated caller deactivating
themselves gets `SELF_DEACTIVATE`, not `CREDENTIAL_INACTIVE`.

**Deactivate, never delete.** The row stays; only `active` flips. Login already
filters on it, so the flag is enforced the moment it is written — there is no
second mechanism to keep in sync. Keeping the row preserves `created_at`, role
history, and any audit entries referencing that `employee_id`. Deleting is what
made the earlier cleanups both unrecoverable and unauditable.

### The last-admin guard is quarantined, not dead — do not delete it

It is currently unreachable by construction: reaching it needs an active
provisioning-role caller, a *different* active provisioning-role target, and
exactly one active such row — and the first two conditions imply at least two.
Before the caller-still-active re-check existed it **was** reachable and was
proven firing live on 2026-08-23.

It stays because reachability is a property of the *current* rule set. Adding a
second provisioning role, a service-to-service caller, or any path that skips
the active re-check makes it live again. Keep the comment explaining this
(`sc-auth.js:368-387` is the definitive version) so nobody removes it as unused.

---

## 8. The lockout — the one thing genuinely worth extracting

`LOCKOUT_THRESHOLD = 5` / `LOCKOUT_MINUTES = 15` is **copy-pasted into all
thirteen endpoint files and is not in the shared lib.** All thirteen agree
today. Nothing prevents drift, and this is a security policy.

If you are touching auth anyway, consider lifting `recordFailure` /
`clearFailures` / `isLocked` into `api/_lib/auth.js` — they are already
identical functions in `rf` and `law`. That is a real change with real blast
radius across thirteen apps, so it is a deliberate task, not a drive-by.

Rules the implementation must preserve:

- **The lock check precedes `verifyPin` and returns immediately.** A locked account never reaches the hash comparison.
- **Increment only on a wrong PIN against a row that exists.** An attempt against an unknown `employee_id` writes nothing — the timing equalisation in §0.1 is what hides that, not the counter.
- **On hitting the threshold, reset `failed_attempts` to 0 and set `locked_until`.** After a lock expires the next wrong PIN starts a fresh 5-strike window.
- **On success, clear both fields** — condition on `failed_attempts || locked_until`, not just `failed_attempts`. `sc` and `sd` test only the counter, so a post-lockout success leaves a stale `locked_until` in the row permanently. Harmless today (the check is `> Date.now()`) but it is real divergent stored state. `rf`/`law` get this right.
- **Failure to write the counter never fails open.** Refuse the login either way.
- **If you add a second factor, it shares this counter.** A 6-digit TOTP with a ±1-step window is brute-forceable at high request rates otherwise (`law-auth.js:228-231`).

---

## 9. Per-employee permissions are a COLUMN, not a role

When one role needs a capability only *some* of its members have, do not add a
fourth role. Add a boolean column on the employee row.

The worked example is SAIRNlegacy's `shared_knowledge_access`:

- Setter: `api/leg-auth.js:285-300`, management-gated, target must be active
- Enforcer: `api/sd-data.js:1683-1697` — and this is the load-bearing part:

> *checked fresh against the employee row on every call, not embedded in the
> session token, so a revoke takes effect immediately rather than waiting out
> the token's 12h lifetime*

Fail closed: an upstream failure on that check returns 502, never fail-open.

Contrast with SAIRNroofing's `certifications` jsonb — that is **capability data
for the UI, not an access gate**, written by an owner-only action against a hard
key allowlist (`KNOWN_CERTIFICATION_KEYS`) so it can never become a free-form
store for client-supplied jsonb. Know which of the two you are building.

---

## 10. The schema — one template, and the parts that are not optional

All twelve share this exactly, modulo the role list:

```sql
create table if not exists <app>_employee_auth (
  id uuid primary key default gen_random_uuid(),
  license_hash text not null,
  employee_id text not null,
  display_name text,
  role text not null check (role in ('owner','...')),
  pin_hash text not null,
  pin_salt text not null,
  active boolean not null default true,
  failed_attempts integer not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (license_hash, employee_id)
);

create index if not exists idx_<app>_employee_auth_license
  on <app>_employee_auth (license_hash);

alter table <app>_employee_auth enable row level security;
drop policy if exists "svc only <app>_employee_auth" on <app>_employee_auth;
create policy "svc only <app>_employee_auth" on <app>_employee_auth
  for all using (false) with check (false);

revoke all on public.<app>_employee_auth from service_role;
grant select, insert, update on public.<app>_employee_auth to service_role;
revoke all on public.<app>_employee_auth from anon, authenticated;
```

Notes that are not style preferences:

- **The column is `active`. Never `is_active`.** All twelve agree; don't be the first to differ.
- **No DELETE grant, ever.** Nothing in the codebase deletes a credential row — deactivation is `active=false`. Withholding it costs nothing and removes a way to lose an audit subject. SAIRNscape once granted it by writing the full CRUD verb list reflexively and had to walk it back (`scp_employee_auth_schema.sql:47-62`).
- **The leading `revoke all ... from service_role` matters** and only SAIRNroofing has it. Without it the table inherits `TRUNCATE`/`REFERENCES`/`TRIGGER` from the platform default ACL — and TRUNCATE on a credentials table wipes every employee's access at once. See `sairn-grant-sweep`.
- **Write the grants into the file.** SAIRNbiz shipped without them and every employee login broke in production with a 42501; SAIRNlaw hit the same thing live. `grd_employee_auth_schema.sql` still has **no privilege statement at all** — it happens to work, and it is not self-sufficient on a fresh provision.
- **`public.`-qualify.** Six files do, five don't. Pick the qualified form.

Naming: the four oldest tables use a short prefix (`sd_`, `sb_`, `grd_`,
`scp_`); everything from SAIRNlaw onward uses the full app name. **No file
anywhere explains why the convention changed.** Use the full app name for a new
app. Note the endpoint prefix stayed short regardless — SAIRNcare is table
`sairncare_employee_auth`, endpoint `alf-auth.js`, data branch `alf_clients`:
three naming schemes for one app. Don't add a fourth.

---

## 11. The client — copy roofing/senior/legacy, not sairncode

`sairnroofing.html`, `sairnsenior.html` and `sairnlegacy.html` are the same
module with different prefixes. `sairncode.html` is a different generation and
should be treated as a rewrite target, not a model: no `whoami`, no
session restore, never calls `check_license`, and **its auth transport never
sends `X-SD-Auth` at all**, so `setup`/`roster`/`set_active` are unreachable
from its own UI.

The shape:

- Licence key on a separate earlier `#gate` screen; sign-in collects **employee ID + PIN only**.
- `<prefix>Auth(action, payload, withSession)` — one helper, token opt-in via the third argument. Licence rides as `Authorization: Bearer`, session as **`X-SD-Auth`**. Two secrets, two headers, deliberately.
- **No client-side first-run detection.** The bootstrap pane is reached by a link; the server is the sole arbiter and answers 409 `ALREADY_PROVISIONED`. Do not add a "does an owner exist?" probe — it is an unauthenticated existence oracle.
- Session restore: decode the payload, check `exp`, check `payload.app` matches, enter the app, then fire a **non-blocking `whoami`** that logs out on rejection.
- Sign-out is local only. No server call, no revocation. Say so in a comment — `sairnlegacy.html:1483-1491` does.
- Role-driven UI gating is **cosmetic only**. Every app has a comment saying the server is the real boundary. Keep writing it. `rf`'s version is the clearest: *"the server refuses regardless, this just stops offering a button that would always 403."*

Known client-side rough edges worth not copying: `sen`/`leg` write a duplicate
`<prefix>_role` key alongside the session blob and **never clear it on logout**;
`sairncode` uses three flat keys instead of one JSON blob; and **none of the
three has a global 401 interceptor** — a token rejected mid-session is only
`console.warn`ed, so the user keeps clicking a dead UI until reload.

---

## 12. Response-shape divergences that actually break clients

Two apps disagree on the wire format for the same action. A client written
against one breaks against the other:

| | `rf` | `sc` / `sd` |
|---|---|---|
| Last-admin error code | `LAST_OWNER` | `LAST_ADMIN` |
| Remaining-count field | `remaining_owners` | `remaining_admins` |

Pick one for a new app and say which you picked. There is no third option worth
inventing.

Also inconsistent, in descending order of how much it will cost you:

- `sd` and `sc` have **no `NOT_PROVISIONED` and no `NOT_GRANTED` diagnostics** — their `upstream()` is a two-line stub, so a missing migration or a missing grant both surface as an unactionable 502. `rf` and `law` distinguish them and name the fix. That is the difference between a five-second fix and an hour of guessing.
- `sc`, `sd` and `law` **never re-check caller-active in `setup`** — only `rf` does. So a just-deactivated owner can still provision credentials for up to 12h in three apps, even though the same files block them from `roster` and `set_active`.
- `law` has **no `roster` and no `set_active`** — no deactivation path at all. Its only credential-lifecycle action is `mfa_reset`.
- Every 400-level validation error omits `code` entirely in all four files read.

---

## 13. Audit posture — and how to be honest when you have none

`api/_lib/audit.js` allowlists exactly three tables: `sairnlaw_audit_log`,
`sairncode_audit_log`, `stonedesk_audit_log`. **If your app is not one of those,
it cannot audit**, and the right move is to say so rather than let silence read
as coverage. `rf-auth.js:490-494` is the model — it names the gap, says why it
is deferred, and hardcodes `audited: false` in the response.

Where audit does exist:

- A failed log write **never blocks the action** — a login that succeeds but fails to log beats a login blocked by a logging outage.
- But for a **credential change**, return an `audited` boolean to the caller. `sc-auth.js:331-334`: without it, "refusals are logged" is unverifiable from outside, because no endpoint reads the audit table.
- Report `audited` on **refusals** too, not just successes.
- Note the honest limit: even in `sc`/`sd`, the `NOT_FOUND` and `unchanged` branches write nothing and carry no `audited` key. "Audit on every outcome" is aspirational there, not literal.

---

## 14. Checklist for a new app

1. Add the app to `ROLES_BY_APP` in `api/_lib/auth.js`, with a comment recording where the role vocabulary came from and whether it was confirmed or a judgment call.
2. Write `sql/<app>_employee_auth_schema.sql` from §10. Include the grants and the leading `revoke all from service_role`.
3. Copy `api/rf-auth.js`. Set `APP`, `TABLE`, `ROLES`, `PROVISIONING_ROLES`, `MANAGEMENT_ROLES`, `BOOTSTRAP_ROLE`.
4. Keep every action: `check_license`, `bootstrap`, `login`, `setup`, `roster`, `whoami`, `set_active`.
5. Add the caller-still-active re-check to `setup` as well as `roster` and `set_active` — `rf` is the only app that does, and it is right.
6. Build the **client UI for `set_active`**. No app has one. See §7.
7. Run the migration before the first login, or the first call returns `NOT_PROVISIONED` (if you kept `rf`'s diagnostics) or an unactionable 502 (if you didn't).
8. Verify live, not in isolation: bootstrap → 409 on second bootstrap → login → wrong PIN ×5 → 429 → wait → login → `whoami` → `setup` a second employee → `roster` → `set_active` off → their login fails → `set_active` on → it succeeds. Then try to deactivate the last owner and confirm the 409.
9. Confirm the grants landed: a missing one is a 42501 that looks like nothing else.

---

## What this skill does NOT cover

- **MFA/TOTP and SSO/OIDC.** Only SAIRNlaw has them. The shared lib supports both; `api/law-auth.js` is the only worked example, and its own history (`law-auth.js:383-391` — a live-found bug where re-enrolling silently switched two-factor *off*) says that path deserves its own pass.
- **WebAuthn.** `api/sd-webauthn.js` exists and is StoneDesk-only. Unexamined here.
- **Extracting the lockout into the shared lib.** Recommended in §8, scoped as a deliberate task across thirteen apps, not done.
