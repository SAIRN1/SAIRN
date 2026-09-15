# Biometric data — retention and destruction policy

**This is the written, publicly-available policy.** Not a design note: the
obligation this exists to satisfy is specifically that a written policy exists
and is *available to the public*, and a policy filed somewhere internal has not
met it. It is committed here so it has a URL, a history, and a date.

**Effective 2026-09-15.** Amendments are commits to this file; the history is
the record of what the policy said on any given day, which is the question that
gets asked afterwards.

---

## 1. Who is who — and this determines everything below

| | |
|---|---|
| **The SAIRN customer** — the shop, practice, agency or firm | **CONTROLLER.** Decides to collect. **The consent duty is theirs.** |
| **SAIRN Technologies** | **PROCESSOR.** Provides the mechanism, records what the controller did, and refuses to collect when they have not done it. |

**This is not a disclaimer, it is a constraint on the software.**
`api/_lib/biometric-consent.js` cannot generate a consent, cannot back-date one,
cannot infer one from an earlier interaction, and does not accept
`consent: true` as an input. It records the three artefacts the controller
produced and answers a yes/no about what they add up to. A module that *could*
manufacture a consent is one that eventually would.

## 2. The rule SAIRN applies before any biometric identifier is collected

Three steps, **in this order**. Not three boxes — a sequence:

1. **NOTICE** — the person is told, in writing, that a biometric identifier
   will be collected or stored.
2. **PURPOSE AND DURATION** — the **specific purpose**, and the **length of
   term** for which it will be collected, stored and used.
3. **SIGNED RELEASE** — a written release, executed by the person.

**Order is enforced, not assumed.** A release signed before the person was told
what it was about is not a release. A purpose disclosed after the signature is
not a disclosure. The software compares the three timestamps and refuses a
record where they run backwards — because three present fields in the wrong
order is exactly the shape of a form assembled afterwards. It is checked in two
independent places: in application code, and as a database CHECK constraint that
a write bypassing that code still cannot get past.

**Equal timestamps are accepted.** One screen can legitimately present the
notice and the purpose together. Refusing that would be a rule about clock
resolution rather than about consent.

## 3. Retention schedule

**A biometric identifier is destroyed at the EARLIER of:**

- **the purpose being satisfied**, as the controller disclosed it to the person;
  and
- **three years after that person's last interaction** with the controller.

**Three years is a ceiling, never a default.** A controller who disclosed a
shorter term is held to the shorter term. The ceiling does not extend anything —
software that quietly relaxed a customer's own promise up to the statutory
maximum would be turning their commitment into our default.

**The clock runs from the LAST interaction, not the first.** Somebody who keeps
using the system keeps a live record; somebody who stops starts the countdown
on the day they stopped.

**A disclosed term longer than the ceiling is refused at write time, not
silently shortened.** Clamping would leave the person holding a signed document
that says something different from what the database does.

### It is enforced in the schema, not only in code

`sql/biometric_consent_schema.sql` computes the destruction deadline as a
**generated column** — no writer chooses it — and carries a separate CHECK
constraint that refuses anything more than three years past the last
interaction. The generated column is the mechanism; the constraint is the rule;
they are deliberately two statements, so editing one does not silently remove
the other.

**Application code is where a rule is applied. A schema is where it cannot be
skipped.** Every earlier retention promise on this platform lived only in the
first place.

## 4. What is destroyed, and what is kept

| | |
|---|---|
| `biometric_template` — **the identifier itself** | **DESTROYED** on the schedule above. Really deleted: the row is removed. |
| `biometric_consent` — **the record that the three steps happened** | **RETAINED.** It is the evidence that collection was lawful. |

**Destroying the consent record destroys the proof.** Conflating the two gives
exactly two outcomes and there is no third: keep everything and blow the
retention limit, or delete everything and have no evidence consent was ever
obtained.

**This is the one place on the platform where a hard `DELETE` grant exists.**
Every other schema had its delete grant removed in August 2026, and soft-delete
is the right answer everywhere else — precisely because elsewhere the record is
worth keeping. Here the whole obligation is that the identifier **stops
existing**, and a `_deleted_at` marker on a biometric template is a template
still sitting in the database with a note on it. The consent record has no
delete grant, so nothing can destroy the evidence.

## 5. Withdrawal

Consent may be withdrawn at any time. On withdrawal, collection stops
immediately and the stored identifier becomes due for destruction **regardless
of its deadline** — the schedule is a maximum, not an entitlement.

## 6. What SAIRN does not do

- **SAIRN does not decide that a feature needs a biometric identifier.** Usually
  it does not. `api/sd-webauthn.js` exists because a passkey achieves the same
  outcome with **no biometric data ever leaving the device** — the platform
  authenticator verifies the person locally and the server receives only a
  public key and a signed challenge. Where that works, it is the correct answer
  and this policy does not apply, because nothing was collected.
- **SAIRN does not judge whether a stated purpose is specific enough.** The
  software refuses an empty purpose and a bare category word — "biometrics",
  "fingerprint", "facial recognition" name what the data *is*, not what it is
  *for*, and a person cannot consent to a noun. **It cannot tell a specific
  purpose from a vague one, and no code can.** That reading belongs to the
  controller.
- **SAIRN does not read this as legal advice to anyone**, and nothing here is
  an opinion about any particular jurisdiction. The sequence and the ceiling are
  the policy this platform applies. A jurisdiction with stricter requirements is
  a stricter policy, not a code change.

## 7. Current state, stated rather than implied

**As of 2026-09-15, no SAIRN app collects a biometric identifier.** This module
exists so that the first one to need it inherits the machinery instead of
building it under deadline — the same reasoning as the WebAuthn rollout.

**`sql/biometric_consent_schema.sql` has not been run.** Until it is, the tables
do not exist and any write answers `NOT_PROVISIONED`. That is the honest state
and is recorded here rather than left for somebody to discover: a policy
document describing tables that do not exist would be the exact defect this
platform keeps finding.

---

*Questions about this policy, or a request to have a biometric identifier
destroyed ahead of schedule, should go to the controller — the business
operating the SAIRN application — who holds the relationship and the consent.*
