# b19 — routed out, because the files are claimed by live sessions

**Written 2026-10-19 by hank, batch b19, which was STOPPED MID-BATCH on
instruction.** Two of the four dispatched build items need files another live
session holds. `python tools/sairn_claim.py check` **BLOCKED** on both, by name:

    session   : cody    blocked by: same declared FILES: api/sd-data.js
    session   : fourth  blocked by: same app: sairnlegacy

**cody's claim says why, and it is not a guess:** *"docs/CRITICALITY-TIERS.md
IS NORMALLY HANK'S AND I AM TAKING IT ON MICHAEL'S EXPLICIT INSTRUCTION this
batch because hank's window is stalled -- declared rather than assumed.
api/sd-data.js likewise."* **So Michael reassigned `api/sd-data.js` to cody for
b25.** Writing it anyway would be overruling a reassignment Michael made, in
the platform's most critical shared file, while the holder is live. I did not.

Both sessions were LIVE at check time (`sairn_status.py` showed running PIDs
that started exactly when the lock says). **This is not a dead-claim
situation**, which is the only case the tool says may be overruled — and even
then only after confirming with the other session.

---

## ROUTED TO cody — `api/sd-data.js`, two changes, both small

### 1. The `law_trust_reconcile` gate reads the module instead of re-listing

`api/sd-data.js:18769` currently carries a hand-written literal and, directly
above it, **its own comment calling this the open question**:

> *"ADDING `attorney` IS THE OPEN QUESTION, not a rejected one. An attorney is
> usually a principal on the firm's trust account and the app already shows
> them the Trust Accounting tab, so the present behaviour may well be wrong --
> but widening it is a bar-rules judgement for the firm, and `paralegal` is a
> separate question again. Tracked as an open decision; NOT closed by this
> fix."*

**b19 answers it in the module that owns law role policy.** The change:

```js
// WAS:
const LAW_RECONCILE_ROLES = roleSet({ owner: true });
if (!LAW_RECONCILE_ROLES[recSess.role]) {
  res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Trust reconciliation is available to the firm owner' } });
  return;
}

// BECOMES -- derived, never re-listed:
if (lawRoles.LAW_RECONCILE_ROLES[recSess.role] !== true) {
  res.status(403).json({ error: { code: 'FORBIDDEN',
    message: lawRoles.denyMessage('law_trusttx', recSess.role,
                                  lawRoles.LAW_RECONCILE_ACTION) } });
  return;
}
```

**THREE THINGS TO KNOW BEFORE PASTING IT.**

* `lawRoles` is **already required** at `api/sd-data.js:103`. No new import.
* **`roleSet` may become unused in that branch.** Check before deleting the
  import — it is used elsewhere in the file.
* **`tests/law_reconcile_role_vocab_check.py` READS THAT LITERAL** and fails if
  it names a role `ROLES_BY_APP.sairnlaw` does not have. Deriving the set
  removes the literal it parses, so **that probe will need re-aiming at
  `api/_lib/law-roles.js` instead.** It is ALREADY exit 2 for an unrelated
  reason (its `const ROLES_BY_APP = {...};` regex matches neither my auth.js
  nor `origin/main`'s — measured in b18, pre-existing), so it is red either
  way and `tests/` is cody's.

### 2. `leg_settings` is NOT registered as a resource, so F2 and F3 are inert

`api/_lib/leg-roles.js` has carried the policy since b18 and
`sql/sairnlegacy_settings_schema.sql` is **NOT WRITTEN** — b19 stopped before
it. What is needed, in order:

1. the schema (NOT written — see "what b19 did not do" below);
2. a `leg_settings` entry in `LEG_RESOURCES` with id column `settings_id`;
3. the read of that row in the `LEG_RESOURCES` prelude, passed as the FIFTH
   argument to `legRoles.decide(resource, role, action, grants, home)`.

**(3) IS THE ONE THAT MATTERS AND IT IS CURRENTLY A DELIBERATE OMISSION, NOT A
BUG.** `api/sd-data.js` passes no `home` today, so every apprentice gets the
empty default and F3's countersign branch is unreachable in production. b18's
own comment at that call site says so in as many words. **Until the settings
row is read and passed, F2 and F3 are policy nothing consults.**

---

## ROUTED TO fourth — `sairnlegacy.html`, one new panel

**NOT AUTHORED.** fourth holds all thirteen app files for the b31 WCAG contrast
pass and a new panel landing mid-sweep is a conflict in a 1MB single-file app.
The spec, so whoever builds it does not have to re-derive it:

* **A "Needs your signature" list in the funeral-home panel**, driven by the
  `status` action of `api/leg-countersign.js`.
* **Render the COMPUTED STAGE, never the four nullable columns.** The endpoint
  already returns one of `awaiting_signature` / `signed` / `filed` / `expired`
  precisely so a panel cannot show "signed" for a spent-and-expired row. Four
  columns is four chances to get that wrong.
* **`idx_sairnlegacy_countersign_open` exists to serve this query** —
  `(license_hash, resource, expires_at) WHERE spent_at IS NULL`. The index is
  in the schema and nothing calls it.
* **Gate it on the SIGNER roles, UX-only**, the way
  `sdRefreshLoginAccessGate()` does in stonedesk: `legRoles.LEG_REGULATED_WRITE_ROLES`
  is `{ owner, director }`. The server re-checks; the panel only hides.
* **It must say what a countersignature does NOT mean.** A witness attests that
  somebody looked, not that they were right —
  `api/_lib/countersign.js`'s header carries the argument.

**AND THE SAME PANEL IS OWED FOR `sairnlaw.html`** ("Needs your
authorisation", same shape, signer set `LAW_BAR_ADMITTED_ROLES`).
`sairnlaw.html` is NOT claimed by anybody and was mine to write this batch —
**b19 stopped before it.** It is not blocked; it is simply not done.

---

## What b19 DID land, so this document is not read as "nothing shipped"

* `api/_lib/law-roles.js` — C1's IOLTA carve-out: `LAW_RECONCILE_ACTION`,
  `LAW_RECONCILE_LEGS`, `LAW_RECONCILE_ROLES`, `LAW_RECONCILE_ATTESTATION`,
  the second lock exception, the named-verb narrowing, and the bookkeeper
  refusal message.
* `api/b19-iolta-reconcile-carveout.test.js` — **32 arms, 0 failed.**
* `docs/2026-10-19-hank-b19-concepts.md` — the concept statements, written
  before the code, including **where the research CONTRADICTS the dispatch's
  premise.**

## What b19 did NOT do, in full

1. `sql/sairnlegacy_settings_schema.sql` — **not written.**
2. The `leg_settings` handler wiring — **cody's file.**
3. The `sairnlegacy.html` panel — **fourth's file.**
4. The `sairnlaw.html` panel — **not blocked, not done.**
5. The Grant-App-Login-Access confirmation — **not re-driven this batch.** b18
   verified the original cause fixed and closed three residuals of its class;
   b19 was asked to confirm and did not get to it, so **the status is b18's,
   not a fresh measurement.** Saying so is the point.
6. No handler arm, no ablation and no live probe for the carve-out. The 32 arms
   are module-level only.
