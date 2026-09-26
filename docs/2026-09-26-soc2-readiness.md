# SOC 2 readiness — SAIRN platform

**2026-09-26 (Cody). First version. This is the findable artifact the platform
did not have.**

**NOT A CLAIM OF COMPLIANCE, AND NOT A REPORT.** SAIRN has no SOC 2 report, no
audit engagement, and no observation period. Saying so in the first paragraph is
deliberate: §6 records that misrepresenting a certification is itself the
enforcement risk, and a readiness document that reads like a report is the
commonest way that happens.

---

## 0. PROVENANCE, AND ONE THING A READER MUST KNOW FIRST

**This document was written independently and is NOT a transcription of the
prior internal research.** That research — a CC1–CC9 mapping, CUEC/CSOC
allocation, NHI credential governance, an IBM/Microsoft/NASA comparison — and
the PR #18 deep-research findings were requested for inclusion across three
dispatches. **Neither was available to the session that wrote this:** they are
not in the repository, not in this session's context, not in the agent memory
directory, and not in any sibling clone. All four were searched.

So rather than leave the gap open a fourth time, this document is built from
**two sources that can be checked**:

| part | source | grade |
|---|---|---|
| **§2–§4** the control evidence | read out of THIS repository, every claim citing a file | **strongest — re-derivable by anyone** |
| **§5–§8** the audit mechanics | retrieved from public sources by this session, 2026-09-26, dated and attributed | **secondary — trade sources, not the AICPA standard itself** |

**WHERE THE PRIOR RESEARCH WOULD HAVE BEEN BETTER, AND IT IS NAMED RATHER THAN
QUIETLY REPLACED:** a CC1–CC9 mapping done against the Trust Services Criteria
text is stronger than §2's mapping, which is done against public summaries of
the criteria. **Nothing here is a substitute for reading TSP section 100.** If
the original research surfaces, §2 is the section to replace, and §0 is the
reason a reader can tell which parts to trust more.

**Nothing in §5–§8 is invented.** Where a search found no answer — §6's central
case being the clearest example — that is said.

---

## 1. Why this exists

`.claude/skills/sairn-decision-gate/SKILL.md` has been asking whether this
platform can substantiate its security claims to a buyer. The answer has been
scattered across a hundred engineering documents and nothing collected it, so a
reader arriving cold could not tell which controls are real. The material is
unusually good in one half and unusually thin in the other, and **the split is
the finding**:

- **Engineering-discipline controls are strong and evidenced** — measurably,
  with artefacts an auditor could sample.
- **Organisational controls barely exist**, because the organisation is one
  person and several agents. No HR function, no vendor-management programme, no
  board, no segregation of duties in the sense CC1 means it.

A readiness document that averaged those two into one posture would be useless.

---

## 2. Control evidence that EXISTS, by criterion

Measured at `d9694306`. Re-derive rather than quote: every figure here moves.

### CC1 — Control environment · **WEAKEST AREA**

| what CC1 wants | what exists | honest gap |
|---|---|---|
| board / governance oversight | nothing | **no substitute exists.** One owner. |
| organisational structure, reporting lines | `CLAUDE.md`'s five-clone registry, role boundaries between build agents and the hover auditor, enforced by `tools/hover_auditor_scope_gate.py` | a real separation-of-duties analogue, but between AGENTS, not people |
| competence / background screening | nothing | no HR function |
| accountability | `docs/tier-a-reviews.json` — 164 obligations, **153 discharged**, each naming an author and a different reviewer, with self-review refused mechanically | the strongest CC1-adjacent artefact on the platform |

**The self-review refusal is worth an auditor's attention** because it is
enforced rather than asserted: `tools/tier_a_review_gate.py` refuses any record
whose reviewer is its own author, at the write, not in a policy.

### CC2 — Communication and information

`docs/SAIRN-OPEN-WORK-INDEX.md` (the work register), `docs/SAIRN-PROCESS-RULES.md`
(682 lines of standing rules), `docs/CRITICALITY-TIERS.md` (389 resources
classified on two axes). **Internal communication is documented to an unusual
standard. External communication of commitments to customers is not** — there is
no trust page, no published commitment, no status page.

### CC3 — Risk assessment

- `docs/CRITICALITY-TIERS.md` — every registered resource carries an integrity
  and a confidentiality tier with written evidence; **261 Tier A**.
- `docs/defect-density-register.json` — **301 records**, each with severity,
  detection method, contributing factors and an open-recurrence statement.
- FMEA and PRA structures exist as documents.

**This is a real risk-assessment programme with real data**, and it is the
section most likely to impress an auditor.

### CC4 — Monitoring

`tools/sairn_push_gate_hook.py` carries **20 numbered checks** running on every
push; 108 gate/check tools in `tools/`; **747** test files. `docs/traceability-matrix.md`
maps requirements to guard tests.

**GAP: no runtime monitoring.** Everything above is pre-deployment. There is no
alerting on production behaviour, no log aggregation, no on-call.

### CC5 — Control activities

The push gate is the control activity, and it is **policy-as-code in the literal
sense**: `SAIRN-PROCESS-RULES.md` rules have executable counterparts that refuse
a push. A gate that fails CLOSED when a dependency is absent is a stated,
enforced rule (PR §1.11), not an aspiration.

### CC6 — Logical and physical access · **the criterion that matters most here**

CC6.1 is the longest criterion in the series and the one a multi-tenant SaaS is
judged on. What exists:

- **17 per-app authentication endpoints** (`api/*-auth.js`) with **17
  corresponding `*_employee_auth` schemas**, PIN credentials, signed session
  tokens, failed-attempt lockout.
- **Per-resource session gating** — `SD_SESSION_GATED` + `SD_GATE_APP` in
  `api/sd-data.js`, with `tests/app_session_isolation.js` measuring the posture
  of every app by DRIVING the handler and comparing against a recorded table.
- **Role-based minimum-necessary tiers** — e.g. SAIRNdental's
  `DNT_FINANCIAL_ROLES` and `DNT_PATIENT_SCOPED_RESOURCES`, where a provider
  reads only patients they have an appointment with and an unlinked provider
  gets refused rather than shown everything.
- **A deactivation lifecycle** re-checked on the data path, not only at login:
  a deactivated credential is refused on a token that still verifies.
- **9 cross-tenant isolation suites** under `api/`.
- **Privilege narrowing at the database** — `sql/*grant*`/`*revoke*` files with
  an audit query.

**Physical access: not applicable and it must be SAID, not skipped** — hosting
is Vercel and Supabase, so CC6.4/6.5 are inherited and become a CUEC/subservice
question (§4).

### CC7 — System operations

`docs/2026-09-15-incident-response-plan.md`, **487 lines, structured on NIST SP
800-61r3 (April 2025)**, and its own opening records that before it existed
*"zero files in 1668 tracked ones described an incident-response process"*. It
is written against two failure modes — a plan nobody can execute, and a plan
whose facts are aspirational — and it states plainly that the platform has ONE
responder.

**GAPS: no vulnerability-management programme, no penetration test, no runtime
detection.** §5 notes that a pen test is commonly expected evidence.

### CC8 — Change management

The strongest area. Every push runs the gate; Tier A changes require a recorded
independent-review obligation; the defect register requires a record or an
explicit `no-defect-record:` reason with a checked minimum length; generated
documents must match their sources or the push is refused.

### CC9 — Risk mitigation / vendors

**Essentially absent.** No vendor risk assessments, no subservice-organisation
monitoring, no BAAs. `docs/SAIRN-OPEN-WORK-INDEX.md` carries an OPEN row: no
BAA exists for the HIPAA-adjacent apps, and it blocks signing rather than
shipping.

---

## 3. NON-HUMAN IDENTITY (NHI) CREDENTIAL GOVERNANCE

Called out separately because it is where an agent-operated platform differs
from an ordinary SaaS, and where an auditor has no standard question to ask.

**What exists:** the service-role key is server-side only; licence keys are
bearer credentials and the platform has an audit recording that they were once
over-trusted (`docs/superpowers/specs/2026-09-02-licence-key-exposure-audit.md`);
the `SD_AUTH_SECRET` signs session tokens; grant/revoke SQL narrows what
`service_role` may do, with a live audit query.

**What does not exist:** no key rotation schedule, no inventory of non-human
identities as a governed population, no expiry on the platform's own machine
credentials, and — the sharpest one — **the five agent sessions act with the
owner's full repository authority and their separation is enforced by
convention plus two gate tools, not by credentials.**

**That last sentence is the honest NHI posture and it should go to an auditor in
those words.** A reader who takes "agents are separated" to mean
cryptographically separated would be wrong.

---

## 4. CUECs and subservice organisations — the allocation

**CUECs (Complementary User Entity Controls)** — what a CUSTOMER must do for the
platform's controls to work. On the evidence in §2, at minimum:

1. **Provision and deprovision their own employees.** The platform enforces a
   last-admin refusal and no self-deactivation, but it cannot know somebody left.
2. **Protect the licence key**, which is a bearer credential.
3. **Choose roles deliberately.** Minimum-necessary tiers exist per app; which
   employee gets which role is the customer's decision.
4. **Review their own audit trails.** Append-only records exist; nobody reads
   them on the customer's behalf.

**Subservice organisations** — Vercel (compute/hosting) and Supabase (Postgres,
PostgREST). **The carve-out vs inclusive-method decision has not been made**,
and it materially changes scope: physical security, backup and infrastructure
availability all live there. A readiness position that does not settle this is
incomplete, and this document does not settle it.

---

## 5. TYPE II MECHANICS — what an engagement actually involves

*Public sources retrieved 2026-09-26; trade publications, not the AICPA
standard. Verify before budgeting.*

- **Observation period: minimum three months**, typically 3, 6 or 12. First-time
  Type II commonly runs 3 months, with renewals extending to 6 or 12.
- **A Type I is a point-in-time design opinion; a Type II tests operating
  effectiveness over the period.** For a platform whose controls are enforced
  by gates that run on every push, the evidence trail across a period is the
  easy part — the artefacts already accumulate.
- **Reported audit fees:** roughly **$15,000–$60,000+** for Type II; small-to-mid
  scope often **$12,000–$20,000**; Big-4 engagements **$60,000–$400,000+**.
  **Total first-year spend** including tooling and readiness commonly
  **$25,000–$80,000+**.
- **A penetration test is commonly expected** as CC4.1/CC7.1 evidence. SAIRN has
  none.

**THE MOST IMPORTANT MECHANIC FOR THIS PLATFORM:** an auditor samples evidence
that a control **executed**, not that it is described. The repository is unusually
well suited to that — a push gate refusal is a durable artefact — and unusually
badly suited to CC1, where the evidence would be about people.

---

## 6. MISREPRESENTATION IS THE NEAR-TERM LEGAL RISK, NOT NON-COMPLIANCE

**There is no obligation to hold SOC 2. There IS an obligation not to say you
hold it.**

**I did not find an FTC enforcement action specifically about a false SOC 2
claim, and I am not going to imply one exists.** What the search did return is a
consistent line of FTC action on **misrepresented certification and seal
programmes**:

- **SecurTest, Inc.** — falsely claimed EU-U.S. Privacy Shield participation
  after starting but never completing certification; settled, barred from
  misrepresenting participation in any privacy or security programme sponsored
  by a government, self-regulatory or standard-setting body.
- **ControlScan** — misled consumers about how often it monitored certified
  sites; **$750,000 judgment, suspended** on inability to pay.
- **TRUSTe, Inc.** — deceived consumers about its recertification programme.
- **Thirteen companies** settled charges of falsely claiming Safe Harbor
  compliance.
- Separately, **False Claims Act** exposure where a federal contractor
  misrepresents security compliance.

**The transferable rule:** the actionable conduct is the claim, and "we started
the process" is exactly what SecurTest said. **This platform's specific risk is
an RFP answer or a service agreement that upgrades "readiness" into
"compliant".** `sairn-decision-gate` already exists to refuse that, and this
document is the artefact that makes the true position quotable instead.

---

## 7. ISO 42001 AND NIST AI RMF — applicability

Relevant because SAIRN ships AI features into regulated verticals (a clinical
scribe, billing-code adjudication, legal deadline computation).

- **ISO/IEC 42001** is the first certifiable AI-management-system standard —
  global, sector-agnostic, requiring policies, objectives, roles, risk
  treatment, monitoring and continual improvement.
- **NIST AI RMF** is comparable in intent and **carries no certification**.
- **SOC 2 is not AI-specific** and does not cover AI-management practice.

**The honest applicability call: neither is required of SAIRN today, and ISO
42001 is the one to watch** — trade coverage describes it moving from a standard
toward a vendor requirement. **A SOC 2 report would not answer an AI-governance
question**, and a buyer in a clinical vertical is increasingly likely to ask one.

**Already present and directly relevant:** deterministic guards that sit OUTSIDE
the model and cannot be bypassed by it — the SAIRNvet contraindication gate, the
SAIRNcode billing-rule validators, clinician acceptance required before an AI
draft is filed. Those are AI-governance controls in substance, and they are not
currently described as such anywhere a buyer would look.

---

## 8. THE HONEST READINESS POSITION, IN ONE PARAGRAPH

**SAIRN could substantiate CC3, CC4, CC5, CC6 and CC8 today with artefacts an
auditor could sample, and could not substantiate CC1, CC9, the runtime half of
CC7, or physical access at all.** The gating items are not engineering: a
subservice decision, a vendor programme, a pen test, and an organisation with
more than one person in it. **The cheapest genuinely useful next step is not an
audit — it is a Type I on a narrowed scope**, which tests design rather than a
period of operation and would surface the CUEC and subservice questions in §4
before any money is spent on an observation window.

---

## 9. What this document does NOT do

- **It does not claim compliance, readiness-for-audit, or a timeline.**
- **It does not replace the missing prior research** — §0 says which sections
  that research would have improved.
- **§2's mapping is against public summaries of the Trust Services Criteria,
  not TSP section 100.** Anybody relying on it for an engagement must read the
  criteria text.
- **It does not settle the carve-out vs inclusive-method question** (§4), which
  changes scope more than anything else here.
- **No figure in §5 was taken from an auditor quote.** They are trade-source
  ranges and will be wrong for any specific engagement.

---

## 10. Decay

Every repository figure is measured at `d9694306` on 2026-09-26 — 261 Tier A,
301 defect records, 164/153 obligations, 20 gate checks, 747 test files, 17 auth
endpoints. All of them move weekly across five clones. **Re-derive before
quoting any of them to anyone outside the team**, and re-read §6 before quoting
any of it at all.
