# `SD_ENCRYPTION_KEY` — the revoke procedure that did not exist

**Written 2026-09-24 (Cody).** The NHI register entry for this credential said,
in its own words, *"REVOKE: there is no revoke"* — accurate, and not a
procedure. This is the procedure that sentence was standing in for.

**It is not tax-advice-shaped hedging: there genuinely is no way to un-leak a
symmetric key.** What a revoke means here is *invalidate everything it
protected*, and that turns out to be entirely possible — but it runs into a
deadlock the API cannot resolve, and the deadlock is why this had to be written
down rather than improvised during an incident.

---

## 0. What the key protects, measured

| Store | Column | What it holds | Reader |
|---|---|---|---|
| `sairnlaw_employee_auth` | `mfa_secret_encrypted` | attorney TOTP secrets, per employee per licence | `api/law-auth.js:384`, `:445` |
| `sc_credentials` | `data->>'enc'` | one stored Stedi API key | `api/sc-eligibility.js:190` |

Both go through `encryptSecret()` / `decryptSecret()` in `api/_lib/auth.js`,
AES-256-GCM, and **nothing else on the platform uses them** — checked across
`api/` rather than assumed.

**THE FORMAT CARRIES THE KEY IT USED.** `legacy` (`iv.tag.ct`) was encrypted
with `sha256(SD_AUTH_SECRET)`; `v2` (`v2.iv.tag.ct`) with
`sha256(SD_ENCRYPTION_KEY)`. `decryptSecret()` **refuses to fall back** for a v2
value, because that fallback would silently re-couple the two duties the split
exists to separate.

---

## 1. The finding that makes this a build and not a paperwork item

**Rotating the key locks every MFA user out, and every route out of that state
runs through a session the state prevents.**

1. `mfa_verify` cannot pass — `decryptSecret()` returns null and `law-auth.js:385`
   answers **500 `MFA_UNAVAILABLE`**. It fails closed and never skips MFA,
   which is correct and is also the trap.
2. `mfa_setup` refuses **409 `MFA_ALREADY_ENABLED`** while `mfa_enabled` is true
   (`:421`), so an attorney cannot re-enroll themselves.
3. `mfa_reset` requires an **Owner session** — and the Owner's own MFA is
   equally broken.

**So there is no API path out.** The direct database write in
`sql/sd_encryption_key_revoke_2026-09-24.sql` is not a shortcut around the
procedure; it is the only door.

**The Stedi side has no equivalent deadlock.** An undecryptable `enc` answers
503 `CREDENTIAL_UNREADABLE` and blocks nothing else, and the key is re-entered
through `api/sc-credentials.js` after being rotated at Stedi.

---

## 2. The procedure

**ORDER MATTERS AND IT IS THE OPPOSITE OF THE OBVIOUS ONE.** The instinct is to
migrate the ciphertexts first so nothing is lost. Do not: the leaked key already
reads every existing ciphertext, so keeping them readable buys the attacker
time and buys you nothing. **Neither secret needs its old plaintext to be
replaced** — a TOTP secret is re-enrolled by scanning a new QR, and the Stedi
key is reissued at Stedi. So destroy access first.

| # | Step | Who | Confirm by |
|---|---|---|---|
| 1 | **Rotate at Stedi first.** Issue a new API key and revoke the old one in Stedi's own console. This is the only part that is genuinely urgent — it is a live third-party credential and it is revocable at the source. | Michael | the old key is refused by Stedi |
| 2 | **Set a new `SD_ENCRYPTION_KEY` in Vercel (Production AND Preview) and redeploy.** From this moment every v2 ciphertext is dead, which is the revoke. | Michael | `vercel env ls production` shows the new value's timestamp |
| 3 | **Run `sql/sd_encryption_key_revoke_2026-09-24.sql`, scoped to the affected licence hash.** This breaks the deadlock: `mfa_enabled = false`, secret cleared. Ask for the three confirm counts back rather than accepting "it ran". | Michael | `still_enabled` 0, `orphan_ciphertext` 0, `still_active` unchanged |
| 4 | **Owner signs in** — now possible, because their `mfa_enabled` is false — and re-enrolls via `mfa_setup` → `mfa_enable`. | firm Owner | `mfa_enrolled` audit row |
| 5 | **Every other attorney re-enrolls** the same way. The Owner does not need `mfa_reset` for them; step 3 already cleared the flag. | each attorney | one `mfa_enrolled` audit row each |
| 6 | **Re-enter the new Stedi key** through the SAIRNcode credentials panel, which encrypts it under the new key. | Compliance Admin | an eligibility check returns something other than 503 |

**WHAT IS EXPOSED BETWEEN STEPS 2 AND 5, said plainly:** two-factor is OFF for
that firm. It is off *visibly* — the security panel reports it and every
re-enrolment is audit-logged — which is the better of the two bad states, and
it is why step 1 comes first: the credential that an attacker can use
*remotely and immediately* is the Stedi key, not a TOTP seed.

---

## 3. What this procedure does NOT cover

- **Whether `SD_ENCRYPTION_KEY` is set in Vercel at all.** `api/_lib/auth.js`
  says *"until `SD_ENCRYPTION_KEY` is set this deploy changes nothing"* — new
  writes stay legacy and the duty stays with `SD_AUTH_SECRET`. **If it is
  unset, this document describes a split that has not happened in production,
  and a leak of `SD_AUTH_SECRET` is simultaneously a session-forgery and a
  secrets-at-rest incident.** One command settles it; it is not asserted here.
- **Legacy ciphertexts.** Anything written before the split decrypts with
  `sha256(SD_AUTH_SECRET)`, so rotating `SD_ENCRYPTION_KEY` does *not* revoke
  them. A full revoke of the at-rest surface therefore also requires the
  `SD_AUTH_SECRET` procedure in the NHI register. **Which rows are still
  legacy is not measured here** and needs a `select` nobody has run.
- **Detection.** Nothing on this platform would tell you the key had leaked.
  This is a containment procedure, not a monitoring one.
- **It has never been executed.** Every step is derived from reading the code
  and the SQL is unrun. The deadlock in §1 is the part I am most confident
  about because three separate refusals had to be read together to see it; the
  step ordering is a judgement.

---

## 4. Two stale error messages, found on the way — FIXED 2026-09-24

Both undecryptable-ciphertext paths used to blame the wrong secret:

- `api/law-auth.js` — *"tampered, or SD_AUTH_SECRET was rotated"*
- `api/sc-eligibility.js` — *"SD_AUTH_SECRET rotated?"*

Since 2026-09-17 a v2 ciphertext fails because **`SD_ENCRYPTION_KEY`** changed,
not `SD_AUTH_SECRET`. During an incident those two lines pointed the responder
at the wrong variable.

**Fixed in a separate change on 2026-09-24**, and not by naming both keys —
naming two candidates is only half an improvement when the log could name one.
Each site now reads the stored format (`v2.` prefix or not), the same
discriminator `decryptSecret()` itself uses, and prints the single variable
that actually wrote that ciphertext. Line numbers are deliberately dropped
here: an anchor to a line is the thing that goes stale next.
