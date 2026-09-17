# `SD_AUTH_SECRET` — what a real mitigation looks like

**Nothing was built. This is the look-before-deciding the item asked for.**

Flagged in `docs/2026-09-17-shared-backend-tenancy-map.md` as the widest blast
radius on the platform: one signing secret shared by every app. Investigating it
changed the picture in **both** directions — one thing is better than the map
implied, and one thing is considerably worse.

---

## What is actually true, measured

**The token.** `base64url(payload) "." base64url(HMAC-SHA256(payload))`, where
payload is `{typ, app, employee_id, role, license_hash, iat, exp}`.
`SESSION_TTL_MS` is **12 hours** (`api/_lib/auth.js:43`).

**BETTER THAN THE MAP SAID — app binding is already near-universal.** `app` is a
*signed claim*, checked against `ROLES_BY_APP` and against the caller-supplied
`expectedApp`. Measured across `api/`, counting arguments with balanced-paren
parsing rather than commas:

| | |
|---|---|
| `verifySessionToken(...)` call sites **with** `expectedApp` | **211** |
| **without** | **5** |

Four of those five are comment or re-export matches. **The one real site is
`api/sd-data.js:969`, and it is deliberate** — it runs only *after* the scoped
check has already failed, purely to turn a bare 403 into "yours is a SAIRNvet
session"; it carries a line-scoped suppression and a note recording that both
directions were verified in a throwaway worktree on 2026-09-15.

*(I first measured this as 206 sites **without** `expectedApp` using a
comma-counting regex that truncated at the first `)` inside
`tokenFromRequest(req)`. That number was wrong by two orders of magnitude and is
recorded here because it was nearly reported.)*

**So a stolen token does not roam between apps.** What a stolen *secret* does is
different: it lets you **mint** a token for any app. App binding stops replay,
not forgery — so the blast radius of a leak is still total.

**WORSE THAN THE MAP SAID, AND THIS IS THE FINDING: `SD_AUTH_SECRET` IS ALSO THE
ENCRYPTION KEY.** `getEncryptionKey()` is `sha256(SD_AUTH_SECRET)`, used as the
AES-256-GCM key by `encryptSecret`/`decryptSecret` for secrets at rest:

- `api/law-auth.js` — attorney **MFA/TOTP secrets**
- `api/sc-credentials.js` / `api/sc-eligibility.js` — a stored **Stedi API key**

Two consequences that neither the name nor the tenancy map suggests:

1. **A leak is not only forged sessions — it decrypts every secret at rest.**
2. **The secret is, today, effectively UNROTATABLE.** Changing it silently makes
   every stored ciphertext undecryptable. Nothing would error at deploy time;
   MFA would start failing per-user as each attorney next signed in. **A
   "rotate the secret" instruction executed today is a data-loss event with a
   delayed fuse**, and nothing in the codebase warns about it.

**No key identifier.** The payload has no `kid`/version field, so nothing can
tell which key signed a given token.

**25 non-test endpoint files** read the secret; all go through
`api/_lib/auth.js:getSecret()`, so there is exactly one place to change.

---

## The options, cheapest-first

### A. Accept and document
Zero work. Leaves the compound risk: one string forges every session on every
app **and** decrypts attorney MFA secrets and a payer API key. **Not
recommended, but it is the current state and should be named as a decision
rather than a default.**

### B. Split the two duties — *the prerequisite for everything else*
Introduce `SD_ENCRYPTION_KEY`; `getEncryptionKey()` stops deriving from the
signing secret.

- **Migration is the whole job**, and it is a standard dual-read: try the new
  key, fall back to the old (`sha256(SD_AUTH_SECRET)`), re-encrypt on next
  write. `encryptSecret` already emits `iv.tag.ciphertext` with no key marker,
  so the fallback is trial decryption — GCM's auth tag makes a wrong key fail
  cleanly rather than yield garbage, which is what makes this safe.
- Ciphertext count is small (MFA secrets per attorney, one Stedi key), so a
  one-shot backfill is realistic and the fallback can then be deleted.
- **Highest value per unit of risk, and it converts "unrotatable" into
  "rotatable".** Recommended first.

### C. Add a `kid` claim + dual-key verification — *makes rotation possible*
Add `kid` to the payload; `verifySessionToken` tries the current key, then the
previous.

- **The backward-compatibility pattern already exists in this file.** `typ` was
  added 2026-08-08 exactly this way: absent is treated as the legacy default and
  no live token was invalidated. `kid` absent ⇒ key 1.
- With a **12-hour TTL**, a rotation completes on its own: publish key 2, accept
  both for 12h, drop key 1. **No mass logout.**
- Small and contained. Recommended second, after B.

### D. Per-app signing secrets — *reduces blast radius*
`getSecret(app)` instead of `getSecret()`. Every issuer already knows its app.

- **The subtlety worth naming before anyone starts:** a verifier must choose a
  key *before* it has verified anything, and the only available hint is the
  token's own `app` claim — attacker-controlled. This is safe in fact (forging
  an app's token requires that app's key, so selecting by the claimed app cannot
  help an attacker) but it inverts the usual "verify before you trust" reading
  and will look wrong to the next reviewer unless the reasoning is written down.
- `api/sd-data.js:969`'s deliberate cross-app path needs the same treatment.
- Real reduction; genuinely more operational surface (N secrets to provision,
  rotate and not lose). **Worth doing after B and C, not instead of them.**

### E. Asymmetric signing (Ed25519)
Verifiers hold only a public key. **Overkill here** — issuer and verifier are the
same serverless process, so there is no third party to protect a private key
from. Named so it is a considered rejection rather than an omission.

---

## BUILT 2026-09-17 — B, C and D all landed, and one design choice changed

All three stages shipped the same day this was written. **One thing in the plan
above turned out to be the weaker option and was replaced:**

**B did NOT use trial decryption.** The plan said GCM's auth tag makes trying
both keys safe — that is true, and it is not sufficient. **Trial decryption
cannot tell you whether a backfill has finished**, so the legacy fallback could
never be removed with confidence. The format carries the key instead:
`iv.tag.ct` is legacy, `v2.iv.tag.ct` is the dedicated key. A `v2` value is
**never** tried against the signing secret — a fallback there would quietly
re-couple the duties the stage exists to separate.

**C** is as planned: `kid` (8 hex of `sha256(key)`, derived not hand-named),
`SD_AUTH_SECRET_PREVIOUS` accepted on verify only, four-step rotation that
drains itself over the 12-hour TTL.

**D** added one rule the plan did not state: **an app with its own key stops
accepting the platform key entirely.** Keeping the platform key as a permanent
fallback would be a blast-radius reduction that reduces nothing. The rollout
uses C's window — set `SD_AUTH_SECRET_SAIRNLAW_PREVIOUS` to the platform secret,
set `SD_AUTH_SECRET_SAIRNLAW`, wait one TTL, clear the previous.

**Two arms exist only because a sabotage killed nothing.** "A v2 value fails
when the dedicated key is removed" passes whether or not a legacy fallback
exists, because the two keys differ so the fallback fails anyway — the arm that
tells them apart feeds a `v2`-prefixed value the legacy key *can* read. And
"verify against the current key only" killed nothing because the `kid` reorder
had already moved the right key to the front; the real no-dual-key sabotage is
dropping `PREVIOUS` from the key list. A third arm covers the case
kid-bearing tokens never exercise: a **pre-`kid` token during a rotation
window**, which is every session issued before 2026-09-17.

23 arms → 45. Eight sabotages, all killing at least one arm after the three
above were strengthened.

**THE RUNBOOK LINE IS NOW THE OPPOSITE ONE:** `SD_AUTH_SECRET` *is* rotatable,
provided `SD_ENCRYPTION_KEY` is set first and existing ciphertexts have been
re-written. Until that backfill runs, legacy (`iv.tag.ct`) values are still tied
to the signing secret and a rotation still orphans them — an arm pins exactly
that, so the hazard is measured rather than assumed gone.

---

## Recommendation

**B, then C, then D.** B is the only one that removes a real, currently-live
hazard — an instruction that reads as routine hygiene ("rotate the shared
secret") destroys attorney MFA secrets today. C is what makes rotation a normal
operation rather than an event. D is a genuine reduction and the most expensive.

**Until B lands, `SD_AUTH_SECRET` must not be rotated.** That sentence belongs
in the runbook, and its absence is the most actionable thing in this document.

## What this does not cover

- **Whether the secret has ever leaked.** Nothing here is an incident claim.
- **How it is stored in Vercel**, or who can read it in the dashboard — that is
  outside the repository.
- **Session revocation.** There is none today; a token is valid until `exp`
  regardless of key state. C makes revocation-by-rotation possible for the first
  time, and that is a side effect rather than a design.
