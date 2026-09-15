# SAIRN incident-response plan

**Status: REAL AND IN FORCE as of 2026-09-15. First version.**
**Structure: NIST SP 800-61r3 (April 2025).**

`.claude/skills/sairn-decision-gate/SKILL.md:53` has been asking this platform
one question for weeks — *"is there a real monitoring and incident-response
plan, or does 'we'll handle it if it happens' count as the plan"* — and until
this file existed the honest answer was the second one. Measured 2026-09-15:
zero files in 1668 tracked ones described an incident-response process.

---

## 0. What this document is, and the two ways it could be worthless

**It is not a template with the app names filled in.** Every number, every
named weakness and every "we cannot currently do this" below was read out of
this repository on 2026-09-15 and is cited so it can be re-checked. A plan whose
facts are aspirational fails on the only day it is used.

**Two failure modes it is written against:**

1. **A plan nobody can execute.** This platform has ONE responder. A document
   assigning roles to an incident commander, a communications lead and a
   forensics analyst describes a company that does not exist, and on the night
   it matters the reader would be one person reading about four people. Section
   1 says who actually does this, and it is a short list.
2. **A plan that claims capabilities the platform does not have.** The hardest
   section below is RECOVER, because the honest content of it is *"for the three
   most sensitive resources on this platform there is currently no recovery
   path at all."* Writing a confident recovery procedure over that would be the
   most dangerous paragraph in the document.

### On the structure

NIST **SP 800-61 Revision 3** (*Incident Response Recommendations and
Considerations for Cybersecurity Risk Management*, April 2025) replaced Rev 2's
four-phase lifecycle with a model organised on the **CSF 2.0 Functions**, on the
argument that incident response is not a separate activity bolted onto security
but a part of managing cybersecurity risk continuously. This document follows
Rev 3.

Most people know the Rev 2 phases, so the mapping is stated once rather than
left implicit:

| Rev 2 phase | Where it lives here |
|---|---|
| Preparation | GOVERN, IDENTIFY, PROTECT (§1–§3) |
| Detection & Analysis | DETECT (§4) and Triage (§5) |
| Containment, Eradication & Recovery | RESPOND (§6) and RECOVER (§7) |
| Post-Incident Activity | §8, and the defect register |

**This document is written from knowledge of SP 800-61r3's structure, not from a
fetched copy of it** — no clone here has network access to NIST. Before this
plan is shown to an auditor or a customer, somebody must open the real
publication and check the Function/Category names against §1–§7. That is a real
caveat and it is at the top rather than in a footnote.

---

## 1. GOVERN — who does this, and what they are allowed to decide

**There is one responder: Michael.** Every session (`hank`, `cc`, `cody`,
`fourth`) can detect, analyse, contain in code, and write up. **No session can
touch production data, rotate a credential, or take a service down** — no clone
holds database access or Vercel credentials, which is a real constraint that has
shaped this whole platform and shapes this plan.

| Role | Who | Can decide |
|---|---|---|
| Incident owner | Michael | Everything below, and anything not listed |
| Responder | any session | Analysis, code containment, write-up, this document |
| Credential rotation | Michael only | No session holds a secret to rotate |
| Data access / restore | Michael only | No session has database access |
| Customer notification | Michael only | And see §6.4 — this is a legal decision, not a technical one |

**A session's standing authority during an incident is deliberately narrow:**

- **MAY**, without asking: read code, run any read-only tool, reproduce, write a
  failing test, open a claim, write the incident record, and **push a
  code-level containment** that makes a thing refuse rather than proceed.
- **MUST NOT**, ever, without Michael saying so in that session: run SQL against
  production, use `SAIRN_SEED_GATE=off`, force-push, delete a branch, revert
  somebody else's commit, or contact a customer.

**The escalation path is one hop, and its weakness is named:** a session tells
Michael. There is no rotation, no secondary, and no out-of-hours cover. **If
Michael is unreachable, the platform's incident response is paused.** That is
the true state today and this document will not dress it up. The mitigation
available now is that code-level containment (making a thing fail closed) does
not need him, and that is exactly why the authority above is drawn where it is.

### 1.1 What counts as an incident here

Broader than "a breach", deliberately. On this platform the most expensive
events on record were **not** intrusions:

- a scheduled job that returned 500 **every hour for months** and sent zero
  reminders, because the code read `RESEND_FROM_ADDRESS` and the project
  defines `RESEND_FROM_EMAIL`;
- a deadline engine that ran **Florida five days late, for five days**, because
  a stranded automated commit deleted one line;
- a public signup endpoint that returned **502 for hours** after a migration
  was reported as run and clean;
- **131 commits on `origin/main` authored by a test identity** after a probe
  wrote to a persistent git config.

None was an attack. Each is an incident under this plan, because each was a
real-world wrong outcome that nobody noticed. **A SILENT WRONG ANSWER IS AN
INCIDENT.** That is the single most important sentence in this section, because
every one of those four was invisible at the time and three of them were being
reported as working.

---

## 2. IDENTIFY — what we are protecting, and where it hurts

The asset register already exists and is generated, not hand-written; this
section points at it rather than making a second copy that can drift.

| What | Where | Why it matters in an incident |
|---|---|---|
| Criticality tiers | `docs/CRITICALITY-TIERS.md` | Tier A is the severity input in §5 |
| Secrets | `docs/SECRETS-INVENTORY.md` | 18 CREDENTIAL, 5 ENDPOINT, 8 ADDRESS, with blast radius and whether absence fails **closed** (an outage) or **open** (an incident) |
| Single points of failure | `docs/SPOF-REGISTER.md` | Shares its blast-radius source with the secrets inventory so the two cannot disagree |
| Tamper-evident history | `sql/audit_checkpoint_schema.sql` | Daily hash-chained checkpoints over the three audit logs — see §4.3 and §7.2 |

**⚠ THE SECRETS INVENTORY IS CURRENTLY REFUSING TO REGENERATE.**
`python tools/secrets_inventory.py --check` fails: `SAIRN_AI_CONTENTION_FLOOR`
and `SAIRN_AI_TENANT_SHARE` are read by code and have no classification. **So on
the day of an incident, the document naming what each credential unlocks is not
currently true.** Closing that is a prerequisite for this plan's §6.2
(credential rotation) to be executable at speed, and it is one decision by
whoever added them.

---

## 3. PROTECT — the controls that already exist, stated at their real strength

This section exists so a responder knows what they can *rely on* at 3am, and
knows what they cannot. Every line is a measured fact, not a claim of coverage.

- **Public role holds nothing.** `anon` and `authenticated` were probed live on
  2026-09-05 with the real shipped publishable key against nine tables: every
  one returned `42501 permission denied`. Confirmed independently from inside as
  `postgres` on 2026-09-09. **Two independent methods agreed**, which is what
  retires the concern rather than leaving it probably-fine.
- **Sessions are app-scoped.** `verifySessionToken(token, license_hash,
  expectedApp)` — the third argument exists because a valid session for one app
  once passed another app's check, and a Semgrep rule now blocks a two-argument
  call.
- **Irreversible writes are gated.** `api/sv-witness.js` will not let a
  controlled-substance row be written until the record is confirmed, and a
  failed check **refuses** rather than writing unwitnessed.
- **Audit logs are append-only and hash-chained** across SAIRNlaw, SAIRNcode
  and StoneDesk.
- **The push gate blocks** on generated-document drift, Tier A changes with no
  recorded review, and several other checks — with a named, spoken override.

**What PROTECT does NOT include, said plainly because a responder will look for
it:** no WAF, no IDS, no SIEM, no log aggregation, no anomaly detection, no
automated key rotation, no network segmentation (there is no network to
segment — it is serverless functions and a managed database), and **no
automated database backups at all** (§7).

---

## 4. DETECT — how we would find out, and the honest coverage

**This is the weakest function after RECOVER, and the gap is structural.**

### 4.1 What actually alerts a human today

| Mechanism | What it watches | Reaches a human? |
|---|---|---|
| `api/cron-watchdog.js` | a scheduled job that has stopped running | **Yes** — Resend email, if `RESEND_API_KEY` and `RESEND_FROM_EMAIL` are set |
| `tools/deploy_verify_notify.py` | the live site not matching the pushed commit | In-session notice only |
| Push gate | a defective change before it lands | Blocks the push; no alert |
| `tools/run_all_tests.py` | a suite gone red | Only when somebody runs it |

**That is the complete list.** Everything else this platform calls a "check" is
a tool somebody has to run.

### 4.2 What has no detection at all

Named rather than left to be discovered mid-incident:

- **credential compromise** — nothing watches for anomalous use of a licence
  key, a session token, or the Supabase service role;
- **data exfiltration** — no egress monitoring; a valid credential reading
  everything it is entitled to read looks exactly like normal use;
- **a wrong answer** — the most likely incident class here, per §1.1, and the
  one with the least instrumentation;
- **an object in `public` created by `supabase_admin`**, which is the named
  trigger on a standing accepted risk. `tools/ownership_evidence_drift.py`
  measures a **proxy** for it (population growth, currently RED at 380 tables
  against the 251 the acceptance was measured on) and **cannot ever report that
  the trigger fired**, because no clone can query ownership.

### 4.3 The one real forensic asset

The **daily hash-chained audit checkpoints** are the only mechanism on this
platform that can answer *"was this record altered, and when"* without trusting
the database it lives in. They are also a restore oracle (§7.2). **In any
incident touching SAIRNlaw, SAIRNcode or StoneDesk data, run the checkpoint
verifier before anything else** — it is cheap, read-only, and its answer is
destroyed by remediation that rewrites rows.

---

## 5. Triage — severity, and what each level obliges

Severity is driven by the **criticality tier of what was touched**, not by how
alarming it feels. Tier A is defined in `docs/CRITICALITY-TIERS.md`.

| Sev | Definition | Target first response | Obligations |
|---|---|---|---|
| **SEV-1** | A Tier A resource is wrong, disclosed, or unrecoverable — controlled substances, attorney trust money, patient charges, medical billing | **Immediate**, whatever the hour | Michael notified at once. Containment before diagnosis. §6.4 assessed within 24h |
| **SEV-2** | Money or PHI/PII affected but not Tier A; or a customer-visible outage | Same working day | Michael notified. Incident record opened |
| **SEV-3** | A wrong answer with no money or personal data; a silent failure; a gate that has stopped gating | Next working day | Incident record; defect register entry |
| **SEV-4** | Near miss caught by a control | No response needed | Defect register entry — **these are the cheapest lessons this platform gets** |

**Escalate on uncertainty, not on evidence.** If it is not yet known whether a
Tier A resource was touched, it is SEV-1 until somebody has *looked*. The cost
of a wrongly-escalated SEV-1 here is one person's evening; the cost of a
wrongly-triaged SEV-2 on a DEA-relevant register is not recoverable.

---

## 6. RESPOND

### 6.1 The first fifteen minutes

1. **Write down the time and what was observed.** Start the incident record
   before diagnosing. Memory of the first ten minutes is the part that is
   always wrong afterwards.
2. **Do not remediate yet.** The strongest instinct is to fix it; the strongest
   forensic evidence is the state it is in right now. On this platform the
   audit chain (§4.3) is the thing most easily destroyed by a well-meant repair.
3. **Contain in the direction of refusing.** Preferred containment is always to
   make the affected path **fail closed** — a gate that denies, a feature
   switched off, a write that refuses. That is a code change, it needs no
   credentials, and any session can do it.
4. **Notify Michael** at the level §5 requires.
5. **Claim it** (`python tools/sairn_claim.py claim <app> <task>`) so a second
   session does not work the same incident blind. Four clones share one branch,
   and two responders editing one file during an incident is its own incident.

### 6.2 Credential compromise

Only Michael can execute any of this; a session's job is to prepare it.

1. Read `docs/SECRETS-INVENTORY.md` for the blast radius **and the absence
   behaviour** — a credential that fails **closed** means rotation causes an
   outage, and one that fails **open** means rotation is urgent *and* the
   window before it was a security incident, not an outage. ⚠ See §2: that
   document is currently not regenerating.
2. Rotate in Vercel (Production **and** Preview — they are separate, and a
   half-rotation leaves the old value live on one of them).
3. Redeploy, then **verify against the deployed URL**, not against the command:
   `tools/sairn_http.py`, or `mcp__claude_ai_Vercel__web_fetch_vercel_url`. A
   403 means **UNVERIFIED**, never verified-good.
4. **The licence key is the platform's front door** and appears in browsers.
   Rotating it is a customer-visible event; treat it as SEV-1 with a
   communications decision attached.

### 6.3 Data integrity incidents

**This is the class this platform is most likely to have**, and the one where
the standard playbook is least applicable, because **there is nothing to restore
from** (§7).

1. Establish the blast radius from the audit chain, not from the rows.
2. **A correction is a new row, never an edit.** The controlled-substance
   register, the trust ledger and the audit logs are append-only by design; an
   UPDATE that "fixes" history destroys the only evidence of what happened.
3. **1 foreign-key clause exists across 459 declared tables.** Postgres will not
   complain about dangling references, so a partial repair produces a database
   that starts, answers queries, and is wrong. An external checker is the
   oracle — the database cannot be.

### 6.4 Notification

**This is Michael's decision and a legal one; nothing in this document
constitutes legal advice, and no session may contact a customer.**

What a responder owes him is the *input*, assembled quickly and honestly:
which app, which resource, which licence holders, what data categories (PHI via
SAIRNdental/SAIRNcare/SAIRNsenior, attorney-client material via SAIRNlaw,
DEA-relevant records via SAIRNvet), how many records, over what window, and
**how confident each of those numbers is**. A breach-notification clock in most
regimes starts from *awareness*, not from certainty, so "we are still
establishing scope" is a thing to say to him on day one rather than a reason to
wait.

---

## 7. RECOVER — and the honest state of it

### 7.1 There are no backups

**Confirmed by Michael directly, 2026-09-14: Supabase free tier, which takes no
automated database backups, with one-day log retention.**

So for `sv_controlled` (DEA-relevant), `law_trusttx` (attorney trust money) and
`dnt_charges` (patient charge history), **there is currently no recovery path at
all.** One-day log retention is not one: a log says what a request claimed, not
what a row contained, and it cannot reconstruct a table.

**The accidental safety net is thinner than it looks, and it is thinnest exactly
where it matters most.** `sv_controlled` and `law_trusttx` leave a partial,
device-dependent copy in a browser. `dnt_charges` leaves **nothing** — its cache
is deliberately cleared on sign-out and on user change, because on a shared
operatory tablet the next user would otherwise read the previous one's copy.
**The app holding dental money has no local fallback, and that is a correct
security decision that happens to remove the net.**

**RTO and RPO are therefore UNDEFINED, and that is the finding, not an
omission.** They cannot be set until backups exist. Creating them is a spend
decision that belongs to Michael.

### 7.2 What recovery is possible today

- **Code** is fully recoverable: git, four clones, `origin/main`.
- **Schema** is reconstructable from `sql/*.sql`, with the caveat that
  `db/schema_snapshot.json` is structure only — no data, no row counts.
- **Configuration** is recoverable if `docs/SECRETS-INVENTORY.md` is current
  (§2).
- **Data is not recoverable.**
- **If a restore ever happens**, the audit checkpoints are the oracle: each
  daily digest is an independently computed fingerprint of history, so no
  baseline capture is needed at restore time. Every window that still matches
  was restored faithfully, and the first that disagrees names *when* the restore
  diverged. This proves the three audit tables restored faithfully and **says
  nothing about any other table** — stated so nobody over-reads it.

---

## 8. Post-incident

1. **A defect-register entry, with the detection method**, in
   `docs/defect-density-register.json`. The `detection_method` field is what
   makes the register answer "which checkpoint should have caught this", which
   is a more useful question than "what broke".
2. **A control, not a resolution.** This platform's standing rule is that a fix
   without something that would notice a recurrence is half a fix. Prefer a
   failing test, a gate, or a probe over a note.
3. **Then make the control fail on purpose.** A check that has only ever passed
   has not been shown to detect anything — 23 of 39 negative controls here were
   measured never verifying their own sabotage applied.
4. **Update this document** when an incident shows it wrong. A plan that
   survives contact unchanged usually was not read.

---

## 9. What this plan does not yet have

Listed so its absence is a decision rather than a discovery:

- **no tested restore** — because there is nothing to restore (§7.1);
- **no out-of-hours cover and no secondary responder** (§1);
- **no detection for credential misuse or exfiltration** (§4.2);
- **no tabletop exercise** — untested, like the restore. A plan nobody has
  walked through is a hypothesis, which is the same standing this platform
  gives an unrestored backup;
- **no customer-facing commitment** about response or notification times, in
  any contract or ToS — deliberately, since committing to a target this
  platform cannot currently meet would be worse than having none;
- **no legal review.**

**The single highest-value thing that would improve this plan is not in this
document.** It is a backup. Everything in §7 is a workaround for its absence.
