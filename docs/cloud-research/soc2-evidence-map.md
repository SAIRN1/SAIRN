# SOC 2 Trust Services Criteria — SAIRN evidence map

**Written 2026-09-24 by a standalone cloud research session, against `main` at
`da1cc791` (2026-09-24 11:11 -0400).** New file only; nothing else in the
repository was edited. It is not in the open-work index and is not a claim of
work by any local agent.

**What this is.** One block per AICPA Trust Services Criterion (2017 TSC with
2022 points of focus): the Common Criteria CC1–CC9, plus the Availability
(A1) and Confidentiality (C1) categories. Each block says what SAIRN already
has that would count as evidence, what is partial, what is missing, and what
could not be verified from this clone. It ends with a ranked gap list.

**Method, and its limits — read before trusting any row.**

- Every `HAVE` line names a real path that was **opened and read** in this
  session (by this session or by one of seven research sub-sessions it ran,
  whose reports were cross-checked against each other and spot-verified
  directly). Tool outputs quoted were produced by running the tool read-only
  in this container on 2026-09-24. Nothing is cited from memory or from
  another document's description of a tool.
- Anything inferred but not confirmed by reading is labelled **UNVERIFIED**.
  Absence claims ("no X exists") were established by grep across `docs/`,
  `api/`, `tools/`, `.claude/` and the root, and are stated with the search
  that was run where it matters.
- **This clone is shallow (50 commits) and Linux.** Any git-history figure is
  bounded to that window. The clone holds no database credential, no Vercel
  credential and no GitHub settings access, so live grant state, branch
  protection, Vercel environment values and the operator's console MFA are
  all UNVERIFIED by construction. Per-clone git hooks (`core.hooksPath`) are
  not installed here, which is expected and says nothing about the operator's
  clones.
- `HAVE` means *designed and present in the repository*. It does not mean
  *operating effectively*. Several controls below are report-only, fail open
  on internal error, or have never fired; each such case is said in its row.
  A SOC 2 Type I opines on design at a point in time; a Type II would need
  the operating-period evidence that most of these rows do not yet produce.

---

## 0. The platform, in the terms an assessor needs first

| Fact | Evidence |
|---|---|
| One Vercel project (`sairn.vercel.app`), 22 routed single-file HTML apps, 4 crons | `vercel.json` (routes and crons; no `headers` block) |
| One Supabase Postgres project shared by every app; tenant = licence key, `license_hash` filter in application code | `docs/2026-09-17-shared-backend-tenancy-map.md`; `api/_lib/license.js`; `docs/NHI-REGISTER.md` row `supabase-service-role` |
| Supabase FREE TIER: no vendor backups, one-day log retention (Michael, 2026-09-14) | `docs/2026-09-14-backup-restorability-scoping.md` lines 3-8; `docs/2026-09-15-incident-response-plan.md` §7.1 |
| 388 registered resources across 17 apps; 248 Tier A, 140 B, 0 C | `docs/CRITICALITY-TIERS.md`; `python tools/criticality_tier_check.py` (TIER_A:248, PROBLEMS:0, run 2026-09-24) |
| Regulated data in scope: PHI (SAIRNdental, SAIRNcare, SAIRNsenior), attorney-client and IOLTA trust (SAIRNlaw), DEA-relevant controlled substances (SAIRNvet) | `docs/CRITICALITY-TIERS.md` tier definitions; `docs/2026-09-15-incident-response-plan.md` §5 |
| One human operator (Michael) holds every credential and every admin console; four Claude Code build sessions plus an independent hover-auditor role; six push-capable clones on one Windows workstation | `docs/2026-09-15-incident-response-plan.md` §1; `docs/NHI-REGISTER.md` rows `github-pat`, `clone-push-access`; `CLAUDE.md` clone table |
| Trunk-based: every clone pushes straight to `main`, Vercel deploys on push; no pull requests, no staging | `tools/dora_metrics.py` line 140; `.github/` holds only `workflows/`; `docs/2026-09-16-hover-separation-push-rejection.md` |
| All five roles commit under one git identity; 131 historical commits carried a probe identity unnoticed | `tools/hover_separation_audit.py` header; `tools/committer_identity_check.py` header |
| Tooling: 220 files in `tools/`; 13 BLOCKING, 63 REPORT-ONLY, 69 DECIDED-not-promoted, 29 SUITE-ONLY, 43 UNWIRED | `docs/TOOLING-INVENTORY.md` (generated). Note: `python tools/tooling_inventory.py --check` FAILS on 2026-09-24 — the inventory is already stale against the repo |
| Legal instruments in the repo: five DRAFTs dated 2026-08-26 (ToS/DPA/AUP amendments, two per-app agreements); master ToS, DPA, AUP, NDA and vendor agreement are NOT in the repo | `docs/legal/`; `.claude/skills/sairn-contract-drafter/SKILL.md` lines 11-25, 218-230 |

---

## CC1 — Control environment

### CC1.1 Integrity and ethical values

**HAVE**
- `CLAUDE.md` — "Verify before you report. A status report is a claim, not a fact" (step 5); push protocol "both directions, no exceptions"; a gate override must be said out loud (Push protocol §3).
- `docs/SAIRN-PROCESS-RULES.md` — Part 5 verification discipline (lines 622-640); §2.3 strike through, never delete, a wrong claim (396-398); §3.3 "An override nobody mentions is how a gate gets hollowed out" (513-514); §4.3 never reword a task string to slip past the claim matcher (596-604).
- `.claude/skills/sairn-decision-gate/SKILL.md` — premortem before any "production / complete / live" claim leaves the team (line 37); "100% means 100%" (63-76); decision-log rule (42).
- `docs/sairnlaw-deadline-engine-external-claim.md` — one approved external sentence, "do not paraphrase it looser" (3-6), with a self-declared PRE-LAUNCH BLOCKER (30-34).
- `docs/2026-08-30-sairntech-app-sellability-gate.md` — eight pass/fail checks before an app is listed publicly, including a dated correction of its own false present-tense claim (51-59).
- `docs/BYPASS-LOG.jsonl` + `tools/bypass_log.py` — every push-gate override recorded (call site `tools/sairn_push_gate_hook.py` lines 598-618); `PATTERN_AT = 3` reports a repeatedly bypassed check as a defect (`bypass_log.py:83`); a retraction row is kept rather than deleted.
- The dated in-place correction convention (`.claude/skills/sairn-memory-curator/SKILL.md` §4, §7; PR §2.3) — corrections are visible, not silently absorbed. `docs/2026-09-15-incident-response-plan.md` lines 92-146 is a worked example.

**PARTIAL**
- Accountability for deviations is a log, not a consequence. `docs/BYPASS-LOG.jsonl` holds 40 rows: 1 retracted; the other 39 are `"check": "ALL", "blanket": true`, 38 of them by session `fourth` between 2026-09-21T12:18Z and 14:36Z — twelve times the `PATTERN_AT` threshold. Every `reason` is the hook's boilerplate string, not a human justification. The incident plan says a session "MUST NOT, ever, without Michael saying so in that session, use `SAIRN_SEED_GATE=off`" (§1, lines 180-182); whether those 38 were authorised is UNVERIFIED — nothing in the log records it.
- `tools/bypass_log.py` lines 106-109 still derive session identity from the clone folder name, the spoof-by-rename defect (hover #258) that `tools/sairn_session_identity.py` closed for claims and Tier A reviews. The log is "APPEND-ONLY BY CONVENTION, not by enforcement" and cannot see a `--no-verify` push (`bypass_log.py:46-55`).
- `SECURITY.md` at the root is GitHub's unfilled template ("Use this section to tell people how to report a vulnerability", lines 15-21).

**MISSING**
- Code of conduct, ethics policy, acceptable-behaviour policy for personnel, sanctions process, policy acknowledgement records. Grep across `*.md *.json *.py *.js *.html` for `code of conduct|employee handbook|background check|whistleblow|org chart|training record|succession` hits only customer-facing product source (`stonedesk-hr.html`, `sairncare.html`) and third-party spec copies under `docs/superpowers/`.
- Any review of a deviation by someone other than the session that made it.

### CC1.2 Board and oversight independence

**HAVE**
- `.claude/skills/sairn-hover-auditor/SKILL.md` — fifth role: "Never write, edit, or push platform code. Find something that needs fixing -- report it" (33-36); "Who checks the auditor" (3963-4007) sets an EQA checkpoint every third process pass.
- `tools/hover_auditor_scope_gate.py` (prevent: refuses commits outside `.claude/skills/sairn-hover-auditor/`, `docs/defect-density-register.json`, `.claude/claims/hover.json`, lines 75-94) and `tools/hover_separation_audit.py` (detect; re-derives the auditor's hash chain independently). Armed per clone by `.git/sairn-hover-auditor-clone` via `.githooks/pre-commit` and `.githooks/pre-push`.
- `.github/workflows/hover-separation.yml` — runs `tools/hover_separation_ci.py` on every push to `main`; its header (14-24) says it **REPORTS and does not BLOCK** until branch protection lists it as a required check with "Do not allow bypassing".
- `tools/tier_a_review_gate.py` — refuses a review record signed by its own author at read (`self_signed()`, 1039-1047) and at the single write point (`_discharge`, 1792-1796). `docs/tier-a-reviews.json`: 136 records, 115 reviewed, 21 open, 0 self-signed; every reviewed record has `reviewer_session != author_session`.
- `docs/2026-09-16-item83-independent-review.md` — a fresh-context reviewer, not the author and not the commissioner (3-6), who deliberately did not fix what it found (179-183).
- `tools/hover_eqa_escalation.py` — computes the auditor's overdue EQA checkpoint from OUTSIDE the auditor clone, read-only; `tools/blind_review.py` — reviewer records severity before seeing the tool's.

**PARTIAL**
- Every "independent" party is a Claude session run by the same one person. The item-83 review was "Commissioned by Michael" (line 5); the hover skill's answer to "who checks the auditor" is Michael spot-checking (3969-3971). Nothing is independent of management, because management is one person.
- Session identity behind the self-review refusal is a `.git/` marker file, "NOT A CRYPTOGRAPHIC CONTROL ... anything that can rename the directory can also write the marker" (`tools/sairn_session_identity.py:35-41`).
- `docs/2026-09-15-hover-auditor-separation-enforcement.md` lines 224-232: "No proof the auditor never wrote platform code" (64.4% of history unattributed); the local gate was "not installed anywhere yet" on 2026-09-15. Whether it has since been armed in `SAIRN-hover` / `SAIRN-hover2` is UNVERIFIED (per-clone `.git/` marker, invisible here). `docs/2026-09-22-hover-multi-log-fix-proposal.md` records that with two auditor instances both freshness tools currently refuse for both, fix "not committed and not applied".
- Whether `hover-separation` is a required status check: UNVERIFIED (GitHub settings). `docs/2026-09-16-hover-separation-push-rejection.md` lines 65-107 records it was tried, deadlocked every direct push, and was removed.

**MISSING**
- Any board, advisory board, audit committee or external oversight body. `docs/2026-09-15-incident-response-plan.md` lines 184-187: "no rotation, no secondary, and no out-of-hours cover. If Michael is unreachable, the platform's incident response is paused."
- A charter or terms of reference for the auditor role beyond its skill file; any external party reviewing its findings.

### CC1.3 Structures, reporting lines, authorities

**HAVE**
- `CLAUDE.md` "Where things live" — the clone/session table (hank, cc, cody, fourth = build; hover = audit, not build) and the rule that clones are counted from disk, not from the list.
- `docs/2026-09-15-incident-response-plan.md` §1 (159-189) — roles table (incident owner Michael; responder any session; credential rotation, data access/restore and customer notification Michael only) and an explicit MAY / MUST NOT list for sessions (175-182).
- `docs/NHI-REGISTER.md` (generated by `tools/nhi_register.py`) — 23 non-human identities, each with owner and scope; the generator REFUSES when a credential has no owner (`nhi_register.py:677-686`); `clone-push-access` counted from disk (6 working copies including SAIRN-hover and SAIRN-hover2).
- `docs/SPOF-REGISTER.md` — Owner column on every row; checker refuses a row without one (line 16).
- `.claude/settings.json` — technical authority limits on agents: `deny` force-push and push-to-master; `ask` on `git add/commit/push` and `npx vercel`; PreToolUse `session_lock_check.py guard`, `git_push_master_guard.py`, `sairn_push_gate_hook.py`, `redaction_check.py`.
- `tools/sairn_claim.py` / `.claude/claims/<session>.json` (work ownership by claim; `STALE_HOURS = 4`); `tools/sairn_status.py` live registry outside git, where `blocked` refuses without `--blocked-on` (593-608).
- `docs/tier-a-reviews.json` fields `author_session`, `reviewer_session`, `reviewer_owner`, `owner_assigned_at` (ownership check at `tier_a_review_gate.py:1800-1819`).

**PARTIAL**
- Roles are defined for AI sessions and one human. There is no delegation-of-authority matrix beyond IRP §1, and no separation between developer, deployer and operator: six clones share one push credential (`docs/NHI-REGISTER.md` row `clone-push-access`).
- `PROVISIONING_ROLES` in `api/sd-auth.js`, `api/law-auth.js`, `api/alf-auth.js` and others are customer-tenant RBAC, not SAIRN's internal structure.

**MISSING**
- Org chart, job descriptions, reporting lines, written delegation for anyone other than Michael.

### CC1.4 Competence, training, succession

**HAVE**
- `.claude/skills/` — 34 directories, all `sairn-*` (counted with `ls -d`), encoding procedures for agent sessions; `CLAUDE.md` "Skills — read them" and "Model selection" sections; `docs/2026-09-13-cross-domain-disciplines.md` mandated reading before any checker is built.
- `.claude/skills/sairn-skill-author/SKILL.md` and `sairn-skill-vetter/SKILL.md` — how skills are authored and how third-party ones are admitted (contents opened for the vetter; author skill listing only, UNVERIFIED in detail).

**PARTIAL**
- Every competence artefact is for AI agents. The only human's competence, qualifications and coverage are undocumented.

**MISSING**
- Training records, onboarding checklist, role qualifications, performance reviews, background-check policy (grep above: none). Succession: IRP §9 "no out-of-hours cover and no secondary responder". Executed legal instruments and all credentials are single-holder; `.claude/skills/sairn-contract-drafter/SKILL.md` 218-230 records the master legal documents exist only in `C:\Users\marsh\Downloads\` ("single-point-of-failure for executed legal instruments"); `git ls-files` shows no `.docx`/`.pdf` in the repo.

### CC1.5 Accountability and performance measures

**HAVE**
- `docs/defect-density-register.json` (271 records, `started` 2026-09-09) + `tools/defect_register.py` — deliberate add; severity vocabulary defined against consequence (139-150); detection-method coverage matrix (20-29). Counts: critical 20, high 121, moderate 107, low 23; detection methods code-review 111, independent-review 63, static-checker 41, mutation-testing 14, live-verification 13, fault-injection 12, probe-control 10, hover-audit 4, user-report 3.
- `docs/defect-budget-decisions.json` + `tools/defect_budget_policy.py` — rolling 30-day window, budget 60 weighted defects, band vocabulary NORMAL / INCREASED REVIEW / FEATURE FREEZE / ALL HANDS; decisions attributed to Michael with dates and `budget_recalibrate_after: 2026-10-22`. `python tools/defect_budget_gate.py` on 2026-09-24: **ALL HANDS, 0.0% remaining, REFUSED new-vertical work**.
- `tools/dora_metrics.py` — DF / lead time / CFR / TTR from git and the register; explicitly refuses benchmark bands ("one person and four agent sessions on a trunk", 44-49).
- `docs/blind-review-rounds.json` / `tools/blind_review.py` — severity-calibration rounds (2 rounds; latest 2026-09-16, judged 8, agreed 3).
- `docs/SPOF-REGISTER.md` — frozen baseline (11 on 2026-09-14) so progress is a fraction; "0 RETIRED" stated (56-72).
- Tier A review 24h deadline (`tools/tier_a_review_gate.py` docstring; `--list` exits 1 when overdue). 1 record past 24h on 2026-09-24 (hank, opened 2026-09-23).

**PARTIAL**
- The defect budget is self-described as uncalibrated (`window_reason`: budget 60 against an observed rate "about 317 ... which means the budget is wrong") and "no hook consults this tool" (`defect-budget-decisions.json:4`). `tools/defect_budget_gate.py` is UNWIRED (inventory) — it binds nothing until invoked.
- Metrics measure the platform and its tooling, never an individual.

**MISSING**
- Performance objectives for personnel, an evaluation cycle, incentives, or any consequence for a session that repeatedly bypasses gates (see CC1.1).

---

## CC2 — Communication and information

### CC2.1 Relevant, quality information

**HAVE**
- Generated registers that refuse to render on a bad input and carry `--check`: `docs/NHI-REGISTER.md`, `docs/MASTER-PLAN.md` (four gates BUILT / TIERED / TRACEABLE / FAULT-TESTED; 388 resources), `docs/TOOLING-INVENTORY.md`, `docs/SECRETS-INVENTORY.md` (49 vars: 18 CREDENTIAL, 5 ENDPOINT, 8 ADDRESS, 18 TUNING), `docs/traceability-matrix.md`, `docs/CRON-LIVENESS-STATUS.md`.
- Hand-written registers with mechanical drift checkers: `docs/CRITICALITY-TIERS.md` (`criticality_tier_check.py` refuses Tier A rows without evidence, line 743), `docs/SPOF-REGISTER.md` (`dependency_graph.py --register`), `docs/SOUP-REGISTER.md` (`soup_register_check.py`), `docs/ACCEPTED-RISKS.md` (every entry must name a trigger; `accepted_risk_trigger_check.py`).
- The three-state exit convention (0 clean / 1 finding / 2 COULD NOT TELL, never folded into pass) — `docs/SAIRN-PROCESS-RULES.md` §1.11; applied e.g. in `docs/AUDIT-CHECKPOINT-STATUS.md` ("COULD NOT TELL ... nothing was verified").
- Timestamped claims: PR §1.10; `docs/claim-provenance.json` (`observed_at` vs `recorded_at`, method measured / derived / attested — 3 records, design doc `docs/2026-09-13-claim-provenance-chain-design.md` says "design, not a build"); `docs/SAIRN-OPEN-WORK-INDEX.md` line 27 "Every row is a claim, not a fact".
- `tools/closing_error.py` — every generated document prints one row per derivation source and refuses if any source contributes zero (`docs/TOOLING-INVENTORY.md` "Closing error" block).
- `tools/committer_identity_check.py` — a clone committing under a probe identity (report-only, `report_only_checks.py:890`).

**PARTIAL**
- Three information sources are red today: `python tools/secrets_inventory.py --check` REFUSES (two unclassified vars `SAIRNVET_TRANSCRIBE_URL`, `SAIRN_RESEND_TIMEOUT_MS`), `python tools/schema_snapshot_freshness.py` FAILS (28 verdicts rest on a `db/schema_snapshot.json` capture 260.6 h old), `python tools/tooling_inventory.py --check` FAILS. `docs/AUDIT-CHECKPOINT-STATUS.md` reads COULD NOT TELL as of 2026-09-14 while `docs/CRON-LIVENESS-STATUS.md` shows `/api/audit-checkpoint` ran ok on 2026-09-24T03:30Z — two status documents disagree because one is not regenerated.
- Git attribution is structurally poor (one identity for five roles; 131 probe-identity commits).

**MISSING**
- A documented information-requirements or data-quality policy; log retention beyond Supabase's one day (IRP lines 400-401); a Vercel log-retention figure (open-work index line 371: "a retention window that is not ours").

### CC2.2 Internal communication

**HAVE**
- `CLAUDE.md` (session primer) and `docs/SAIRN-PROCESS-RULES.md` (in-task rules), split by audience 2026-09-12.
- SessionStart hooks push context automatically (`.claude/settings.json`): `session_lock_check.py start`, `sairn_claim_hook.py`, `sairn_status.py --hook`, `hover_self_health_shim.py`; PreCompact hook demands a handoff be written and committed.
- Per-session logs `SAIRN-ACTIVE-WORK-{hank,cc,cody,fourth}.md`; the open-work index; handoffs named `APP-YYYY-MM-DD-subject-handoff.md`, "not written until committed" (`.claude/skills/sairn-session-handoff/SKILL.md:45-58`).
- `tools/sairn_status.py` — `--note` is append-only with re-read confirmation (488-516, 641-665); `--blocked-on` surfaces what waits on Michael.
- `docs/2026-09-13-coordination-health-check.md` — four real relay failures analysed; `docs/2026-09-16-shared-status-registry.md`.
- Escalation: hover HIGH/urgent findings "go to Michael directly, immediately" (`sairn-hover-auditor/SKILL.md:84-86`); IRP §6.1 step 4.

**PARTIAL**
- The only escalation path is "a session tells Michael" — one hop, to the person who is also management. No anonymous or whistleblower channel. The chat relay has "no integrity check, no size guarantee, and no acknowledgement" (`coordination-health-check.md:51-53`).

**MISSING**
- Security-awareness communication, policy acknowledgements, any communication of internal-control responsibilities to a human other than the operator.

### CC2.3 External communication

**HAVE**
- `docs/legal/` — five DRAFTs dated 2026-08-26: ToS Amendment No.1, DPA Amendment No.1, AUP Revision No.1, SAIRNdental and SAIRNroofing service agreements. Contact `michael@sairn.com`, Orrville, Ohio; AUP Revision §5 abuse reporting (51-53); per-app agreements §7 no uptime SLA, §9 liability capped at three months' fees, §10 Ohio law.
- `.claude/skills/sairn-contract-drafter/SKILL.md` — house convention; §5 "write §3 and §5 from the CODE"; §6 the three gaps an app agreement cannot close (DPA §9 HIPAA trigger, two BAAs, DPA §6 deletion the product cannot perform).
- Customer-notification authority: IRP §6.4 — Michael's legal decision, "no session may contact a customer"; the responder assembles app / resource / licences / data categories / counts / confidence (380-393).
- `docs/BIOMETRIC-RETENTION-POLICY.md` — self-described "written, publicly-available policy", effective 2026-09-15 (actual public publication UNVERIFIED).
- External-claim discipline: `sairn-decision-gate`, `docs/sairnlaw-deadline-engine-external-claim.md`, the sellability gate.
- Vendor identities named: `docs/NHI-REGISTER.md` (Anthropic, Stripe, Resend, Supabase, CourtListener, Stability, Firebase, Stedi, ALF pharmacy); `docs/SOUP-REGISTER.md` (third-party components).

**PARTIAL**
- Every legal file is "TEMPLATE ONLY. Attorney review required"; the dental agreement is headed "THIS AGREEMENT CANNOT BE EXECUTED YET"; "No BAA exists between SAIRN and Anthropic" (dental agreement line 17). The master ToS / DPA / AUP / NDA / vendor agreement are not in version control; their executed status is UNVERIFIED.
- No customer-facing commitment on response or notification times, "deliberately"; "no legal review" (IRP §9, 464-467).
- No single SOC 2-style system description. Boundary facts are scattered across `CLAUDE.md`, `docs/2026-09-17-shared-backend-tenancy-map.md`, `docs/MASTER-PLAN.md`, `docs/SPOF-REGISTER.md`. No `README*` at the root.
- Vulnerability disclosure: `SECURITY.md` unfilled; the only security contact is in a DRAFT AUP revision.

**MISSING**
- Executed contracts in the repo, privacy policy text, status page, customer security documentation, subprocessor list, regulator-communication procedure, DPIA/BAA register.

---

## CC3 — Risk assessment

### CC3.1 Objectives specified clearly; risk tolerances

**HAVE**
- `docs/MASTER-PLAN.md` (generated by `tools/master_plan.py`) — a four-gate FINISHED definition per vertical, each gate with a named checker.
- `docs/CRITICALITY-TIERS.md` lines 15-23 (what counts as consequential: money; regulated/protected data; a documented incident) and 581-588 ("What a tier is FOR": verification depth, whether a guard blocks, pre-computed incident cost).
- `tools/defect_budget_policy.py` lines 22-33 + `docs/defect-budget-decisions.json` — the one quantified risk tolerance on the platform (see CC1.5).
- IRP §1.1 (191-210) defines "incident" — "A SILENT WRONG ANSWER IS AN INCIDENT" — and §5 (309-324) SEV-1..4 with first-response targets keyed to tier.
- `docs/2026-09-13-cross-domain-disciplines.md` — eight standing disciplines that function as an engineering risk-methodology charter.

**PARTIAL**
- The only quantified tolerance is defect load, and it is acknowledged uncalibrated. Regulatory obligations appear as evidence cells on individual tier rows (e.g. `dnt_gfe` → 45 CFR 149.610), not as a compliance-objectives statement.

**MISSING**
- Entity-level objectives (service commitments, system requirements), an availability target, a risk-appetite statement. Grep `risk (tolerance|appetite)` over docs, CLAUDE.md and skills: two incidental hits in the hover skill only. RTO/RPO: "UNDEFINED, and that is the finding" (IRP line 416).

### CC3.2 Risk identification and analysis

**HAVE**
- Asset inventory by resource: `docs/CRITICALITY-TIERS.md` — 388 rows, two-axis (Integrity/Availability and Confidentiality, Tier = worse of the two; `docs/2026-09-21-criticality-tiers-two-axis-spec.md`), per-row "worst consequence if wrong or lost" and "if read by the wrong person", evidence cell mandatory on A. Checker `tools/criticality_tier_check.py` reconciles against `api/_resources/*.js`, refuses uncited access-control claims (192-205), guards the headline count (844-874). Run 2026-09-24: PROBLEMS:0.
- `docs/SPOF-REGISTER.md` + `tools/dependency_graph.py` (`SPOF_THRESHOLD = 10`, line 477) — 32 rows (8 OPEN, 24 ACCEPTED, 0 RETIRED) against a frozen baseline of 11; each with owner, blast radius, compensating control. `env:SUPABASE_URL` blast 70 of 144 modules with a live 504 incident cited (line 108).
- `docs/SECRETS-INVENTORY.md` (blast radius and fail-open/closed absence behaviour per variable) and `docs/NHI-REGISTER.md` (23 identities, 6 drafted compromise procedures). `python tools/rotation_blast_radius.py` (2026-09-24): 5 identities BROAD-scope with no attested rotation (supabase-service-role, sairn_backup_reader, anthropic-api, session-signing, sairncash-firebase-admin).
- Likelihood/impact: `tools/risk_event_tree.py` (four barriers in series with probability bands; run 2026-09-24: worst case "0.2% to 23.1% conditional on the initiating event", "RANKING IS NOT STABLE"; backup barrier band 0.30-0.95 because `docs/backup-reader-verification.json` does not exist) and `tools/pra_event_tree.py` (top-down end states; refuses to multiply frequency by consequence; "RECOVERABLE is False for every one of the 44 initiating events").
- FMEA: `tools/fmea_draft.py` (97 drafts in `docs/fmea/`) and `tools/fmea_prediction_check.py` (2026-09-24: 271 defects considered, 18 predicted, 75 missed, honest rate 7%).
- Third-party component risk: `docs/SOUP-REGISTER.md` (per-component hostile-version impact and bound; SRI sha384 on registered CDN scripts, lines 226-230; `qs` advisory triage with reachability, 170-215); `tools/soup_register_check.py` CLEAN 2026-09-24; `tools/npm_audit_check.py` 0 advisories (exit 3 = could-not-tell is distinct from pass); `.github/workflows/codeql.yml` (JS/TS + Python; push, PR, weekly `21 19 * * 5`).
- IRP §4.2 names undetected threat classes (credential compromise, exfiltration, wrong answers, `supabase_admin` object creation).

**PARTIAL**
- Likelihood is explicitly not measured anywhere; no incident-frequency data exists (`docs/2026-09-18-circuit-breaker-enforce-decision.md` §2).
- 140 Tier B rows are rule-classified, not individually read (`CRITICALITY-TIERS.md` line 572); 7 rows still "CONFIDENTIALITY NOT YET INDIVIDUALLY READ" (line 40).
- The SPOF graph sees only `require()` and `process.env` edges; HTTP calls between endpoints and the HTML apps are invisible (`SPOF-REGISTER.md` 82-90).
- Secrets inventory currently refusing; transitive npm tree (189 lockfile entries) "not individually assessed" (`SOUP-REGISTER.md` 156).

**MISSING**
- Vendor-as-organisation risk assessment (Supabase, Vercel, Anthropic, Stripe, Resend, Cloudflare, GitHub) — see CC9.2. A periodic formal risk-assessment cadence or sign-off.

**UNVERIFIED**: whether CodeQL results are reviewed.

### CC3.3 Fraud risk

**HAVE**
- Fabricated-data risk: `.claude/skills/sairn-guardian-v2/SKILL.md` Check 0b (fabricated KPIs: numbers with no function behind them); `tools/benford_check.py` (leading-digit test on money corpora; header: "NOT WIRED INTO ANY GATE ... 'look here' instrument"; DECIDED).
- Three-way match: `docs/2026-09-14-three-way-match-audit.md` (SAIRNbiz was a "zero-way match": one person creates and settles a payable) and `docs/2026-09-14-independent-review-three-way-match.md` (independent reviewer executed the shipped function, found it refused correct bills, fixed `a58af8ca`); `tools/three_way_match_check.py` (DECIDED — no FIXTURES block yet).
- Two-person control on an irreversible regulated write: `api/sv-witness.js` (1-70) — witness token bound to the record hash, checked against the table, fails closed (503), countersign must be a DIFFERENT prescriber, per-licence `require_two_person`; suites `api/sv-witness.test.js` (470 lines) and `tests/failsafe/witness_{mint,countersign,atomicity,recovery}.js` (1,545 lines; a 32-mutation sabotage review recorded in `witness_mint.js`).
- Tamper-evident audit: `sql/audit_checkpoint_schema.sql` / `api/audit-checkpoint.js` daily hash-chained checkpoints (IRP §4.3); live ok 2026-09-24T03:30Z per `docs/CRON-LIVENESS-STATUS.md`.
- Independent audit role (hover) with mechanical separation (CC1.2).

**PARTIAL**
- Fraud is addressed as specific control shapes, not as a fraud risk assessment. Grep `management override|insider threat|segregation of duties` across docs and skills: no policy hit. The SAIRNbiz "second pair of eyes" is an open product decision for Michael (open-work index line 376).

**MISSING**
- A fraud-risk assessment naming incentive, opportunity, rationalisation and management-override risk for a solo operator with full production access; a segregation-of-duties analysis for the six clones that can all push to `origin/main`.

### CC3.4 Changes that could significantly affect controls

**HAVE**
- `docs/2026-09-13-cross-domain-disciplines.md` §8 — instrument drift; `python tools/sabotage_control_check.py` 2026-09-24: UNGUARDED 0 (down from 23/39 on 2026-09-13).
- `tools/schema_snapshot_freshness.py` (repo SQL vs pasted DB snapshot, with a 12-hour expiry — FAILING today, 260.6 h stale), `tools/ownership_evidence_drift.py` (population drift vs the accepted `supabase_admin` ACL risk; RED at 380 tables against 251), `tools/pinned_list_drift_check.py` + `docs/2026-09-15-pinned-list-drift-sweep.md`, `tools/sairn_stale_snapshot_scan.py`.
- `tools/criticality_tier_check.py`, `tools/soup_register_check.py`, `tools/nhi_register.py --check`, `tools/secrets_inventory.py --check` — all fail closed when code adds a resource, component or credential.
- Technology-change decisions recorded: `docs/2026-09-18-circuit-breaker-enforce-decision.md`, `docs/2026-09-18-slsa-build-provenance-scoping.md`; business-model change tracked in `docs/2026-09-17-sairncash-stripe-readiness.md` (Stripe blocked on LLC formation, Michael 2026-09-05).

**PARTIAL**
- Drift detection is thorough for repo-internal artefacts. Drift in the external environment (Supabase plan, Vercel runtime, vendor terms) is captured only ad hoc.

**MISSING**
- A change-impact procedure for leadership, staffing or business-model change; a review cadence for the risk registers themselves.

---

## CC4 — Monitoring activities

### CC4.1 Ongoing and separate evaluations

**HAVE**
- Ongoing evaluation, two entry points: `.claude/settings.json` hooks (PreToolUse `sairn_push_gate_hook.py`, `git_push_master_guard.py`, `session_lock_check.py guard`, `redaction_check.py`; PostToolUse `html_script_check.py`, `deploy_verify_notify.py`, `report_only_checks.py --hook`; four SessionStart hooks; UserPromptSubmit heartbeat; PreCompact) and `.githooks/pre-push` (reads refs once; hover scope gate in the auditor clone; `register_feed_gate.py --pre-push`; `sairn_push_gate_hook.py --pre-push`). The git hook exists because the tool-call hook "was never asked" on 2026-09-01 when a Python subprocess pushed (pre-push header).
- `tools/report_only_checks.py` — `REGISTRY` of 61 checkers (each with `tool, mode, verdict, promoted, catches, why_it_matters, evidence`) run after every push, exit 0 always; `NOT_PROMOTED` list of 69 with a recorded reason each. Promotion policy is prose ("report-only until quiet in practice"), no numeric threshold field.
- Meta-monitoring of the monitors: `tools/flaky_checker_quarantine.py` + `docs/flaky-checker-ledger.json` (46 checkers with observations, quarantine empty); `tools/known_red_check.py` + `docs/known-red-suites.json` (17 known-red of 411 files, measured 2026-09-17; NEW / KNOWN / CHANGED / RECOVERED states); `tools/checker_control_check.py` (every promoted checker needs a plant-defect / plant-clean pair); `tools/sabotage_control_check.py`; `tools/mutation_anchor_check.py`; `tools/metamorphic_check.py`; `tools/checker_confidence.py`; `tools/check_precedence.py`; `tools/independence_check.py`; `tools/install_git_hooks.py --check` including `git_actually_fires()`; `tests/push_gate/gate_freshness_probe.py`; `tools/guard_ablation.py` + `docs/2026-09-15-item98-guard-ablation.md` ("17 of 38 role gates can be removed and nothing goes red"); `docs/2026-09-12-checker-determinism-sweep.md`.
- Separate evaluation: the hover auditor (`.claude/skills/sairn-hover-auditor/SKILL.md`: fast / deep / process passes, rotation never the same agent twice, append-only hash-chained self-log outside the repo, EQA every third process pass); `tools/hover_process_pass_freshness.py` (FAIL at 48 h, WARN 36 h); `tools/hover_eqa_escalation.py`; `tools/blind_review.py` + `docs/blind-review-rounds.json`; `tools/first_article_inspection.py` + `docs/first-article-inspections.json` (12 inspections, required from 2026-09-16); `tools/tier_a_review_gate.py`.
- Static analysis: CodeQL (push, PR, weekly); `tools/run_semgrep.py` + `tools/semgrep/verify-session-token-app-scope.yml` (one rule file, two rules, `--max-target-bytes 0`).
- `tools/run_all_tests.py` — discovers ~506 files under `tests/` plus 75 `api/*.test.js`, names UNRUN files.

**PARTIAL**
- Every ongoing evaluation runs on the operator's workstation, keyed to a Claude Code tool call or a per-clone git hook that a fresh clone does not have until `install_git_hooks.py` is run. Nothing server-side verifies the hooks are armed. The gate fails OPEN on internal error by design (`.githooks/pre-push` header; hook lines 2345-2349).
- `tools/run_all_tests.py --hook` has been PAUSED since 2026-09-10 (`docs/2026-09-10-run-all-tests-hook-PAUSED.md`); both re-enable conditions were recorded MET on 2026-09-11 and it is still absent from `.claude/settings.json`. No CI runs the test suite; `.github/workflows/` holds codeql, cron-liveness, hover-separation, nightly-backup, source-manifest only.
- Whether anyone reads the report-only sweep's output is not recorded anywhere.
- The auditor's self-log is unreadable from the repo or CI; `hover_process_pass_freshness.py` and `hover_eqa_escalation.py` both exit 2 COULD NOT RUN here, and `docs/2026-09-22-hover-multi-log-fix-proposal.md` says they refuse on the operator's machine too now that two auditor instances exist. `hover_eqa_escalation.py` docstring: the EQA checkpoint was "OVERDUE for sixteen process passes against a cadence of three" when written.
- `python tools/tooling_inventory.py --check` FAILS today; the inventory's closing traverse prints 74 NOT-promoted decisions against a headline of 69.
- `.claude/skills/sairn-guardian-v2/SKILL.md` "## The 31 Checks" is a manual checklist the model runs; only some checks are mechanised.

**MISSING**
- A written monitoring plan (scope, frequency, risk basis, evaluator qualification); a management review sign-off of monitoring results; any external assessment.

### CC4.2 Deficiencies evaluated and communicated; remediation tracked

**HAVE**
- `docs/defect-density-register.json` + `tools/defect_register.py` (see CC1.5) — every record cites the fixing commit, `detection_method`, `contributing_factors`, `recurrence_open`; `tools/register_feed_gate.py` DENIES a `fix(` commit touching code that cites no record (requirement date 2026-09-16; escape trailer `no-defect-record:` with minimum length; wired in `.githooks/pre-push`).
- `docs/SAIRN-OPEN-WORK-INDEX.md` — the open-deficiency queue (723 rows; Owner / Blocked by / Next action / STATUS; ⚠️ marks unconfirmed rows) with `tools/stale_row_sweep.py`, `tools/index_duplicate_check.py`, `tools/dispatch_state.py`, `tools/orphan_register_check.py`.
- `docs/tier-a-reviews.json` — 136 records, 21 open, 1 past the 24h deadline, 0 self-signed.
- Generated status documents with a COULD NOT TELL third state: `docs/CRON-LIVENESS-STATUS.md` (State OK, 2026-09-24 12:54Z), `docs/AUDIT-CHECKPOINT-STATUS.md`.
- `tools/assurance_case.py` (GSN goals → evidence commands; DECIDED not promoted because "five of eight developed goals are NOT SUPPORTED" and "it MUST NOT BECOME A GATE"), `docs/MASTER-PLAN.md`, `docs/traceability-matrix.md`.
- `docs/2026-09-13-defect-severity-rubric-UNRATIFIED.md` (accuracy 13/21 on one blind pass; still unratified — no successor file).

**PARTIAL**
- The register is a closed-defect ledger; open deficiencies are prose rows in the index. No single record with an open → assigned → remediated → verified lifecycle and dates.
- Communication to "management" is chat to Michael; no retained record of what was escalated when (the hover self-log would hold some of it and is off-repo).
- `docs/AUDIT-CHECKPOINT-STATUS.md` has read COULD NOT TELL since 2026-09-14 (`CRON_SECRET` not set in that environment).

**MISSING**
- Remediation SLAs by severity and measurement against them (the 24h Tier A review deadline is the only timed obligation); a deficiency-communication log; a periodic root-cause / recurrence roll-up.

---

## CC5 — Control activities

### CC5.1 Control activities that mitigate risk; segregation of duties

**HAVE**
- The blocking push gate `tools/sairn_push_gate_hook.py` — 15 `CHECK n:` blocks (1-14 plus 12b): 1 seed load state (LIVE, deny on drift); 2 credential-writer recoverability guard on changed `sql/*.sql`; 3 SQL preflight against the live schema snapshot, fail-closed; 4 endpoint/engine seam; 5 reachability (blocking since 2026-09-02); 6 redaction on what the push ships; 7 pre-auth oracles; 8 a PROBE fixture commit must not reach origin; 9 the named `GUARD_TESTS` and seam tests over the whole tree; 10 gate staleness vs `origin/main` (report-only inside the blocking hook); 11 raw control bytes; 12 / 12b a generated document this push broke, or a new `tools/` file with no inventory entry; 13 the independent-review rule on Tier A code; 14 conflict markers. Checks 2, 3, 4, 5, 12 deny when their tool is absent (PR §1.11).
- Risk linkage: the tier register drives `tier_a_review_gate.py`, `criticality_tier_check.py`, `service_role_tier_a_gate_check.py`; the accepted-risk, SPOF, SOUP and secrets registers each have a drift checker in the report-only registry.
- Segregation of duties, mechanical: check 13 refuses a self-signed Tier A review and a Tier A hunk with no recorded obligation; hover separation (prevent, detect, CI).
- Coordination controls: `tools/sairn_claim.py` (4h claims), `tools/sairn_status.py`, `tools/session_lock_check.py` (BLOCKING PreToolUse deny on a second live session in one clone).

**PARTIAL / what cannot be separated**
- One git identity for all five roles; one human with admin on GitHub, Vercel and Supabase. Any SoD is between AI sessions run by that person; a `reviewer_session` is another Claude session.
- Push gates are client-side, fail open on internal error, are skipped by `--no-verify` or an un-armed clone, and can be blanket-overridden (39 blanket overrides in `docs/BYPASS-LOG.jsonl`).
- `tools/gh_push.py` writes `stonedesk.html` directly through the GitHub contents API (lines 229-243), a path that bypasses every local hook; whether it is still used is UNVERIFIED.

**MISSING**
- A risk-to-control mapping outside docstrings; server-side enforcement of any gate (required status checks UNVERIFIED and, per the push-rejection doc, deliberately not applied); human-level SoD.

### CC5.2 General controls over technology

**HAVE**
- Change control as above; `tools/deploy_verify_notify.py` (post-push hash of `origin/main:stonedesk.html` against the live URL); `.github/workflows/source-manifest.yml` + `tools/source_manifest.py` (signed manifest of the 24 intended deploy digests per push; explicitly "NOT SLSA BUILD PROVENANCE FOR THE DEPLOYED PRODUCT").
- Infrastructure monitoring: `api/cron-watchdog.js` and the independent `.github/workflows/cron-liveness.yml` (see CC7.2).
- Backup design: `.github/workflows/nightly-backup.yml` (see A1.2 — never produced a dump).
- Security scanning: CodeQL; one Semgrep rule; `tools/npm_audit_check.py` (report-only); `tools/redaction_check.py` (PreToolUse and push check 6); `tools/preauth_oracle_check.py` (check 7); `tools/service_role_tier_a_gate_check.py` (report-only; 2026-09-24 run: 3 UNGATED findings — `api/_lib/dental-public.js` `dnt_settings`, `api/dnt-bi.js`, `api/sen-portal.js` — plus 1 COULD NOT RUN for `api/legal-deadlines.js`).
- Third-party components: `docs/SOUP-REGISTER.md` + `tools/soup_register_check.py`.
- Secrets baseline: `docs/SECRETS-INVENTORY.md` + `tools/secrets_inventory.py --check`.

**PARTIAL**
- Recovery relies on a workflow whose secrets were unset when written and which has failed on all 10 runs (A1.2). Vulnerability management is scan-only with no triage record. Hooks-installed check is report-only and per clone.

**MISSING**
- Access reviews for GitHub / Vercel / Supabase, MFA evidence for those consoles, key-rotation records; environment separation; a formal change-approval step.

### CC5.3 Policies and procedures

**HAVE**
- Policy layer: `CLAUDE.md`; `docs/SAIRN-PROCESS-RULES.md` (Part 1 class rules 1.1-1.12 including 1.9 determinism, 1.10 oldest-input currency, 1.11 fail closed, 1.12 hang-before-loud; Part 2 editing standing documents; Part 3 push protocol; Part 4 coordination; Part 5 verification; Part 6 provenance).
- Procedure layer: 34 `.claude/skills/sairn-*` directories; `sairn-precommit-gate/SKILL.md` routes which skill must run per change type; `sairn-guardian-v2/SKILL.md` "## The 31 Checks"; `docs/2026-08-30-skill-precedence.md` (referenced by CLAUDE.md; not opened — UNVERIFIED).
- Responsibility: CLAUDE.md clone table; claims; per-session active-work files; status registry; Tier A review owner fields.
- Timeliness: 4h claim expiry, 24h Tier A review deadline, 48h hover process-pass bound, every-third-pass EQA, handoff before compaction.
- Reassessment of the procedures themselves: `sairn-skill-author` conventions (dated in-place corrections, retire not delete); every count-bearing document says not to trust its own count.

**PARTIAL**
- The policies are written for AI sessions and one operator, contain workstation-specific environment steps (python vs python3, CRLF), and have no named owner, approval or review date beyond git history.
- The one policy document that is written for the outside world (`docs/BIOMETRIC-RETENTION-POLICY.md`) governs data no app collects, on a schema that has not been run (§7).

**MISSING**
- Information-security, acceptable-use, access-control, change-management, vendor-management, BC/DR and data-classification policies in the SOC 2 sense; policy acknowledgement; a review schedule. (An incident-response plan exists — CC7.4.)

---

## CC6 — Logical and physical access controls

### CC6.1 Logical access architecture, identification and authentication, credentials, encryption, key management

**HAVE**
- `api/_lib/auth.js` — the single shared auth library. Session tokens: HMAC-SHA256 over base64url JSON (`signPayload` 425-432), `timingSafeEqual` verify (437-478), `verifySessionToken(token, license_hash, expectedApp)` (545-570) rejects wrong `typ`, unknown app, role outside `ROLES_BY_APP[app]`, app ≠ expectedApp, expiry, licence mismatch; `SESSION_TTL_MS` = 12 h (88); token in `X-SD-Auth`, licence in `Authorization` (576-579); stateless. `ROLES_BY_APP` is a null-prototype map of 17 app namespaces (96-316; the `MAP['constructor']` finding of 2026-09-24 is recorded at 43-77). PINs: scrypt with a 16-byte random salt and constant-time compare, dummy-salt run on unknown ids (481-507). Key rotation: `kid` in every token, `SD_AUTH_SECRET_PREVIOUS` accepted on verify, optional per-app `SD_AUTH_SECRET_<APP>` (340-419). AES-256-GCM `encryptSecret/decryptSecret` with `v2.` keyed by `SD_ENCRYPTION_KEY` and no fallback for v2 (743-796). RFC 6238 TOTP (614-693). OIDC authorization-code + PKCE with JWKS RS256, alg pinned (798-935).
- `api/_lib/license.js` — tenant identity: `hashLicense` = sha256 (38-40); `validateLicenseKey(key, expectedApp)` (86) returns `valid`, `active`, `app_id`, `license_hash`, `app_scope` (78-84).
- `api/sd-data.js` — licence read only from `Authorization: Bearer` (472-474); inactive licence → 403 `LICENSE_INACTIVE` (589-590); 131 `verifySessionToken(` call sites; per-request active-credential re-check (1162-1174); app boundary on by default, off only with `SAIRN_APP_BOUNDARY=off` which logs loudly (463, 678-682).
- `api/sd-auth.js` (representative of 17 `api/*-auth.js`) — `bootstrap` refuses 409 `ALREADY_PROVISIONED` once any credential exists (196-203); PIN 6-8 digits (188); login filters `active=eq.true` (229); `locked_until` → 429 (238-240); 5 failures → 15-minute lock (254-257); generic 401 (264-267).
- `api/law-auth.js` — TOTP MFA (`mfa_setup/enable/verify/reset`, 417-477), MFA failures count toward lockout (259-268), `mfa_reset` needs an owner session (467); OIDC SSO (75-97). `sql/sairnlaw_employee_auth_schema.sql` 46-66 (`mfa_secret_encrypted`, `sso_subject`).
- `api/sd-webauthn.js` — WebAuthn passkeys via `@simplewebauthn/server`, RP `sairn.vercel.app`, 5-minute signed challenges; registration requires an existing PIN session.
- `api/_lib/token-vault.js` — AES-256-GCM vault for accounting OAuth tokens; refuses (`NO_KEY`) rather than storing cleartext.
- `sql/sd_employee_auth_schema.sql` — `pin_hash`, `pin_salt`, `role` CHECK, `active`, `failed_attempts`, `locked_until`; grant is select/insert/update only, no DELETE.
- `docs/NHI-REGISTER.md` (23 identities), `docs/SECRETS-INVENTORY.md`, `docs/2026-09-24-sd-encryption-key-revoke.md` (measures exactly what `SD_ENCRYPTION_KEY` protects and writes the revoke procedure that "did not exist"), `docs/2026-09-17-sd-auth-secret-options.md` (211 `verifySessionToken` call sites with expectedApp vs 5 without, one deliberate).
- `tools/redaction_check.py` — PreToolUse hook blocking credential-shaped strings before any file write; `.gitignore` excludes `.env*`.
- `tools/semgrep/verify-session-token-app-scope.yml` — severity ERROR on a two-argument `verifySessionToken` / `verifyPreauthToken`.

**PARTIAL**
- Encryption at rest is field-level for three secret classes only (TOTP secrets, one Stedi key, accounting OAuth tokens). Customer and PHI JSON payloads in every `*_data` table are stored plaintext at the application layer (`encryptSecret` is used in `api/_lib/auth.js`, `api/law-auth.js`, `api/sc-credentials.js`, `api/accounting.js`, `api/_lib/token-vault.js`, never in `api/sd-data.js`). Supabase disk-level encryption is claimed only in a comment (`auth.js:699`) — UNVERIFIED.
- MFA: TOTP in SAIRNlaw only, opt-in per employee; WebAuthn in StoneDesk is a single-factor alternative; 15 apps are PIN-only (6-8 digits, no complexity, no expiry).
- RLS is declared but is not the tenant boundary: 373 `enable row level security` statements across 112 `sql/` files and 280 `create policy`, of which 216 are `using (auth.role() = 'service_role')` and 52 deny-all; the API's only database identity is `service_role`, which bypasses RLS. Isolation is `license_hash=eq.` filters in application code.
- One `SD_AUTH_SECRET` signs every app's sessions unless per-app secrets are set; rotation overlap exists since 2026-09-17; no rotation has ever been attested ("A blank `last rotated` means NOBODY KNOWS", `NHI-REGISTER.md:11`). Live values of `SD_ENCRYPTION_KEY`, `SD_AUTH_SECRET_<APP>`, `ACCOUNTING_TOKEN_KEY` in Vercel: UNVERIFIED.
- The raw licence key is sent in one query URL (`api/_lib/license.js:23-26`, recorded as a residual).
- `python tools/secrets_inventory.py --check` REFUSES (2026-09-24): the published inventory is stale against code.

**MISSING**
- Network segmentation ("there is no network to segment", IRP §3); an access-control policy; per-user database identities; MFA on the operator's own Vercel / Supabase / GitHub consoles (nothing in the repo records it).

### CC6.2 User registration, authorization, removal, periodic review

**HAVE**
- Two-stage tenant employee registration: `bootstrap` mints the first owner only when zero rows exist (`api/sd-auth.js:196-216`); `setup` needs a verified session holding a provisioning role (283-294; `PROVISIONING_ROLES` per app, e.g. `['owner','admin']` StoneDesk, `['owner']` SAIRNlaw and SAIRNcare).
- Removal: `set_active` (`sd-auth.js:425-520`) requires a provisioner session and a reason, refuses self-deactivation (450-454), re-reads the caller's own row (463-468), refuses removing the last guard-role holder (479-520, `LAST_ADMIN`); `api/_lib/employee-lifecycle.js` carries the same rules for nine apps; `api/sd-auth-last-admin.test.js`, `api/sd-data-active-credential.test.js`, `tests/active_credential_gate_probe.py` (deactivation enforced on the data path per request since 2026-09-16, `api/_lib/auth.js:1002-1030`, `sd-data.js:1162`).
- `tools/licence_recoverability_check.py` — detects licences with zero active provisioners (the "trapdoor"); `api/provisioner-health.js` reports active-provisioner counts per licence for 16 apps.
- Auth events audited for three apps (`api/_lib/audit.js` `AUDIT_TABLES` = sairnlaw, sairncode, stonedesk; `law-auth.js` writes `login_success`, `lockout`, `mfa_failed`, `mfa_enrolled`).
- Internal human population is one (IRP §1); the NHI register is the closest thing to a user inventory.

**PARTIAL**
- Customer (licence) lifecycle has no in-repo mechanism: `python tools/entitlement_freshness_check.py` (2026-09-24, exit 1) — 34 files read `license_keys`, 0 write it, 17 hand-run SQL files do; `status`, `plan`, `trial_ends_at`, `stripe_subscription_id` are UNREVOKABLE from code. Onboarding and offboarding a tenant is a manual SQL paste by Michael.
- Auth audit exists for 3 of 17 apps; the credential table has no `last_login`, so dormant credentials cannot be detected. `NO_ACTIVE_CHECK` (transport failure) is allowed-and-logged, not refused (`sd-data.js:1162-1174`).

**MISSING**
- A periodic access-review procedure or record (grep `access review|periodic review|quarterly review` across docs and skills: nothing); onboarding/offboarding for internal staff, contractors or the AI build agents; an approval workflow for provisioning beyond the provisioner's own session.

### CC6.3 Role-based authorization, least privilege, segregation of duties

**HAVE**
- Per-app role vocabularies signed into tokens and re-validated on every verify; `expectedApp` mandatory by Semgrep rule.
- Formal role model: `docs/spec/RoleGates.tla` with `tools/role_gate_invariants.js` (2026-09-24: "No invariant is violated ... a statement about 63 checks, not about the 22 that could not be made"); `tools/role_gate_mc_config.py`; `tools/run_tlc.py` (first real run 2026-09-22 found both specs unevaluable by TLC — recorded in `docs/TOOLING-INVENTORY.md`).
- Session-gate posture measured by driving the real handler: `node tests/app_session_isolation.js` — 64 assertions pass; ALL resources session-gated in sairnlegacy, sairndental, sairnsenior, sairncare, sairnroofing, sairnbiz, sairnvet; SOME in stonedesk, sairnlaw (all four Tier A gated as of 2026-09-22), sairnbuild, sairndesign, sairnmechanical; NONE in sairnscape, sairngrounds, sairncode (licence-only by decision 2026-09-14), sairnfreedom.
- Cross-tenant isolation graded by `python tools/cross_tenant_isolation_scope.py` (2026-09-24): GENUINE 229, WEAK 1, NONE 18, UNLOCATED 1 (`rf_entities`); `api/sd-data-cross-tenant-isolation.test.js`, `api/sd-data-cross-tenant-dispatchers.test.js` (listed; contents UNVERIFIED); `docs/2026-09-21-cross-tenant-isolation-build-plan.md`.
- Database least privilege: `docs/2026-09-09-license-keys-and-service-role-grant-state.md` (`license_keys` narrowed to SELECT alone 2026-09-05, `e5a98af6`; DELETE revoked from `service_role` on 134 tables 2026-08-25, `923a31c`); `sql/backup_reader_role.sql` (SELECT-only, NOINHERIT, BYPASSRLS); `.claude/skills/sairn-grant-sweep/SKILL.md`; `anon` probed live 2026-09-05 — 42501 on nine tables, confirmed as `postgres` 2026-09-09 (IRP §3).

**PARTIAL**
- 18 Tier A resources have no genuine cross-tenant test. Two apps holding Tier A financial data (sairnscape `scp_quotes`, sairngrounds `grd_invoices`) authorise on the licence key alone, which is shipped to the browser (`auth.js:283-284`).
- `RoleGates.tla` is "NOT MODEL-CHECKED HERE" (header 28-35).

**MISSING**
- Human segregation of duties (one person holds every credential, approves every change, runs every migration); a documented access-review cadence for tenant roles or DB grants (grant sweeps are ad hoc, dated files).

### CC6.4 Physical access

**HAVE** — nothing.

**MISSING**
- Any physical-security, data-centre, workstation, laptop or device policy: grep `physical access|laptop|device policy` across `docs/` and `.claude/` returns nothing. Development, push credentials and (per the contract-drafter skill) the executed legal instruments live on one Windows workstation (`CLAUDE.md` clone table; `docs/NHI-REGISTER.md` `clone-push-access`). No disk-encryption, screen-lock or loss procedure recorded.

**UNVERIFIED**
- Reliance on Vercel and Supabase physical controls: their SOC 2 reports are not referenced anywhere in the repo.

### CC6.5 Secure disposal and decommissioning

**HAVE**
- `docs/BIOMETRIC-RETENTION-POLICY.md` + `api/_lib/biometric-consent.js` (`RETENTION_MAX_YEARS = 3`, refuses use past deadline) + `sql/biometric_consent_schema.sql` (generated `destroy_by`, hard DELETE grant on `biometric_template` only).
- Soft delete with tombstones (`api/sd-data.js:2811, 2897-2918`; `api/sd-data-customer-soft-delete.test.js`; `tests/customer_delete_does_not_resurrect.js`; `tests/collection_delete_reaches_the_server.js`).
- `tools/cleanup_confirm_check.py` (every cleanup SQL must carry per-statement confirm queries) and `tools/cleanup_residue_check.py` (asks the live API whether targeted rows still exist).
- `docs/2026-09-24-sd-encryption-key-revoke.md` + `sql/sd_encryption_key_revoke_2026-09-24.sql` — crypto-shredding-style invalidation of encrypted secrets.
- `tests/phi_cache_scoped_to_user.js` — device-level PHI cache purge on user change and sign-out.

**PARTIAL**
- Deletion is hiding, not destruction: soft-deleted rows stay in Postgres; no purge job exists (grep `api/` for purge / retention_days / delete_after / expires_at finds only trial, biometric and consent code). `docs/2026-09-14-record-retention-and-retrievability.md`: the only retention setting (`SC_RETENTION_FLOOR_YEARS = 10`, `api/sd-data.js:150`) is "a stored preference that nothing reads"; "There is no purge mechanism."
- `service_role` has no DELETE on 134 tables, so deletion outside `sc_*` is hand SQL as `postgres`; every cleanup file's NOT RUN label "is a claim about the file, not about the database" (`cleanup_residue_check.py` header).
- The biometric policy governs data no app collects, on a schema not yet run (§7).

**MISSING**
- Tenant offboarding / licence-termination deletion; decommissioning procedure for environments, keys or backup artefacts; media-sanitisation statement.

### CC6.6 Threats from outside the boundary

**HAVE**
- Vercel WAF declared intent in git: `tools/waf_rules_expected.json` (`firewallEnabled: true`, two rate-limit rules 100/60s and 600/60s keyed by IP, `action: "log"`, invariant that every rule stays `log` until decided in writing) with `tools/waf_rule_check.py` comparing the live config (LIVE; DECIDED not promoted).
- AI proxy guardrails `api/claude.js`: `KNOWN_APP_IDS` allowlist (31-60), `MAX_TOKENS_CEILING = 4096` (114), `MAX_TOOL_USES_CEILING = 5` (93), licence checked when present (306-313), `SAIRN_CLAUDE_AUTH_MODE=enforce` → 401 (325-329); `api/_lib/ai-rate-limit.js` per-app daily ceiling with per-tenant sub-budget, atomic RPC path with `pg_advisory_xact_lock`, racy fallback self-reported; `api/claude-cost-controls.test.js`, `api/claude-guardrail-probes.test.js` (27 arms), `api/claude-guardrail-metamorphic.test.js`.
- Public endpoints rate-limited with salted IP hashes (`api/_lib/dental-public.js:29`, `api/_lib/stonedesk-public.js:51`).
- Unauthenticated surface declared and classed: `tools/public_endpoint_declarations.json` — 28 handlers (10 public-by-design, 8 bespoke-auth, 4 cron-secret, 2 webhook-signature, 4 pilot-only); `tools/preauth_oracle_check.py` (push check 7) + `tools/preauth_oracle_accepted.json` (25 triaged).
- Stripe webhooks verified by signature (`api/agent/stripe-webhook.js:130-135`); cron endpoints require `CRON_SECRET` before any disclosure.
- Anti-enumeration: constant-time PIN check, generic 401, WebAuthn returns well-formed options for unknown ids.
- XSS: `docs/2026-09-01-stonedesk-innerhtml-audit.md` (470 innerHTML sites; 40 attribute-position raw interpolations closed; 141 element-text interpolations remain unescaped); `docs/2026-08-30-raw-html-exposure-sweep.md`.
- Credentials kept out of URLs: `tests/public_token_leaves_the_address_bar.js`, `tests/intake_link_no_credential.js`. `api/bridge.js:215` enforces `https:` and a host allow-list for proxied hosts.
- `docs/2026-09-13-ai-red-teaming-scoping.md` — live-verified 2026-09-13 that `/api/claude` answered an unauthenticated request with a real completion; SAIRN-owned probes built, garak deferred.

**PARTIAL**
- `api/claude.js` auth mode defaults to `'observe'` (288) and fails OPEN on licence-store error (315-321); production mode UNVERIFIED. `api/_lib/anon-rate-limit.js` was "MEASURED IN PRODUCTION 2026-09-05: THIS DOES NOT WORK" (per-instance; 40 concurrent junk requests → 0 × 429) and now defaults to observe (`docs/2026-09-05-anon-amplification-limiter-scoping.md`).
- No `headers` block in `vercel.json`; no HSTS, CSP or X-Frame-Options anywhere in `api/`.
- Four `pilot-only` unauthenticated writes (`api/bridge.js`, `api/network.js`, `api/org-intel.js`, `api/agent/enqueue.js`) with stated preconditions.
- IRP §3 says "no WAF" — imprecise: the WAF is enabled with log-only rules. Everything else in that sentence (no IDS, no SIEM, no log aggregation, no anomaly detection, no automated key rotation) is accurate.

**MISSING**
- A blocking WAF rule, IDS/IPS, egress or credential-misuse detection (IRP §4.2), bot management, DAST/external scan, penetration-test record.

**UNVERIFIED**: HTTPS-only redirect and TLS termination at Vercel (platform default; only `sd-webauthn.js:72` `ORIGIN = 'https://sairn.vercel.app'` evidences it).

### CC6.7 Transmission, movement and removal of information

**HAVE**
- `tools/export_coverage_check.py` — every Class A record must be producible as a file; `docs/2026-09-14-class-a-retrievability.md` (11/11 producible on screen and as a file as of 2026-09-16).
- `tools/csv_formula_injection_check.py` (UNWIRED) — 53 raw CSV sites in 13 files routed through guard helpers on 2026-09-17; detects an undefined-helper regression.
- `tests/phi_cache_scoped_to_user.js` + `tests/phi_cache_scope_probe.py` — SAIRNcare / SAIRNsenior local PHI caches purged on identity change and sign-out, including the outbound AI prompt.
- Bulk PHI export behind a dedicated feed token (`api/dnt-bi.js`, `DENTAL_BI_KEY`; NHI row `dental-bi-export`).
- Licence only in `Authorization`, session only in `X-SD-Auth`, never body or URL (`sd-data.js:472`).
- `api/_lib/mech-redact.js` — server-side redaction on the SAIRNmechanical `mech_docs` write path (`tests/mech_docs_redaction_wiring_probe.py`; explicitly NOT anonymisation).

**PARTIAL**
- Exports are client-side CSVs of data the session already fetched: no separate export authorisation, watermark or export audit event.
- Browser `localStorage` holds full working copies of Tier A data (IRP §7.1: `sv_controlled` and `law_trusttx` "leave a partial, device-dependent copy in a browser").
- The licence key is a long-lived bearer secret held by every browser of every employee.

**MISSING**
- Mobile-device, removable-media or BYOD policy; MDM; DLP; classification-driven transmission rules.

**UNVERIFIED**: encryption in transit to Supabase / Anthropic / Stripe / Resend (all `fetch` to URLs held in env vars not in the repo).

### CC6.8 Unauthorized or malicious software

**HAVE**
- `.github/workflows/codeql.yml` (push, PR, weekly; JS/TS + Python; default query pack, `security-extended` commented out at line 79). `docs/2026-09-18-circuit-breaker-enforce-decision.md` §2: 242 successful CodeQL runs in the last 500 Actions runs.
- `tools/npm_audit_check.py` (2026-09-24: 0 advisories, CLEAN); `package.json` pins 3 dependencies (`@simplewebauthn/server`, `firebase-admin`, `stripe`) with a `uuid >= 11.1.1` override; `package-lock.json` lockfileVersion 3, 195 entries.
- `tools/run_semgrep.py` + one custom rule file; `docs/SOUP-REGISTER.md` + `tools/soup_register_check.py` (CLEAN 2026-09-24).
- `.github/workflows/source-manifest.yml` — attested manifest of the 24 deployed paths per push.
- `.claude/skills/sairn-skill-vetter/SKILL.md` — third-party skills, plugins and MCP servers treated as supply-chain artefacts.
- `tools/redaction_check.py`; `tools/control_char_check.py` and `tools/invisible_in_pattern_check.py` (push check 11 and report-only: raw control bytes and invisible characters inside patterns).

**PARTIAL**
- Subresource integrity: 4 external `<script src="https://…">` tags in the app HTML and 0 carry `integrity=` (grep; the SOUP register's SRI claim covers the components it registers, not these four).
- No `.github/dependabot.yml`; patching is manual after an alert; no Python dependency scan (open-work index line 269).
- Deploy integrity is one file at one moment (`deploy_verify_notify.py`); no runtime integrity monitoring.

**MISSING**
- Endpoint protection / EDR / application allow-listing on the developer workstation; malware scanning of uploaded files (`api/_lib/dental-photo-validation.js` exists but was not opened — UNVERIFIED); a patch-management policy or SLA.

---

## CC7 — System operations

### CC7.1 Detection of configuration change and new vulnerabilities

**HAVE**
- CodeQL, npm audit, Semgrep as above.
- Configuration baselines: `db/schema_snapshot.json` + `tools/schema_snapshot_freshness.py` (FAILING: 260.6 h stale); `docs/SECRETS-INVENTORY.md` + `tools/secrets_inventory.py --check` (REFUSING); `tools/vercel_config_check.py` (report-only: buildCommand length, route destinations); `tools/waf_rules_expected.json` + `tools/waf_rule_check.py`.
- Post-deploy change detection: `tools/deploy_verify_notify.py` (stonedesk.html only, Bash-text pushes only); `tools/landing_verification.py` (all routes, manual; "The other 21 routes in vercel.json have never been compared to anything", header 123-147); `tools/gh_verify.py` (single file; hardcodes a Windows `.env.local` path at line 71).
- Repo-vs-database drift as a named class: `docs/2026-09-12-never-run-migration-batches.md`, `docs/2026-09-13-never-run-tables-severity-triage.md` (85 declared tables absent from live, 26 queried by live code, as of 2026-09-13).
- `docs/2026-09-10-self-referential-guard-sweep.md`; `tools/sairn_stale_snapshot_scan.py`.

**PARTIAL**
- Both configuration baselines are red today. Post-deploy verification is automated for one file.

**MISSING**
- Any monitoring or diff of Vercel or Supabase settings (env vars, project protection, RLS policies, grants); DAST; a vulnerability-management SLA. `tools/ownership_evidence_drift.py` header: the accepted-risk trigger (an object in `public` created by `supabase_admin`) "cannot ever report that the trigger fired, because no clone can query ownership".

### CC7.2 Monitoring for anomalies

**HAVE**
- `api/cron-watchdog.js` — hourly Vercel cron (`vercel.json` `15 * * * *`), Bearer `CRON_SECRET`; grades 4 `EXPECTED_JOBS` from `sairn_cron_heartbeat` as ok / LATE / DEAD / FAILING / PARTIAL / NEVER_BEAT / UNDECLARED (149-202); alerts by Resend to `SAIRN_OPS_EMAIL` (208-212, 300-327); weekly end-to-end channel proof (232-271); `api/cron-watchdog.test.js` (965 lines) asserts `EXPECTED_JOBS` equals `vercel.json` crons both ways.
- `.github/workflows/cron-liveness.yml` + `tools/cron_liveness_check.py` — out-of-band read from GitHub Actions; soft re-poke then hard fail so GitHub emails the repo owner; refuses without `CRON_SECRET`; commits `docs/CRON-LIVENESS-STATUS.md` (State OK, 2026-09-24 12:54:37Z, 4 jobs ok, channel proof delivered to the operator 2026-09-17). Its own header: "roughly THREE RUNS IN FOUR NEVER HAPPEN" — real cadence every 2-6 hours. `docs/2026-09-15-item54-second-watchdog.md` records the three live watchdog defects it was built after (HTTP 508 self-retry, self-latching failure, no ops email set).
- Tamper-evident audit: `api/audit-checkpoint.js` + `sql/audit_checkpoint_schema.sql` — daily SHA-256 checkpoints over closed UTC-day windows of three audit tables, chained from GENESIS, re-verifying the last 14 windows; `api/audit-checkpoint.test.js` plants a backdated row and requires detection. Live ok 2026-09-24T03:30Z (written 3, failures 0).
- Audit-trail writers: `api/_lib/audit.js` (`writeAuditLog`, best-effort, allowlists `sairnlaw_audit_log`, `sairncode_audit_log`, `stonedesk_audit_log`) required by 7 files → 3 apps with server-side checkpointed audit logs; SAIRNvet `sv_audit_log` and SAIRNcare `alf_op_audits` are browser-originated trails not covered by checkpoints (`docs/2026-09-14-hash-chained-audit-logs-scoping.md`); `tools/append_only_read_order_scan.py`; `api/alf-append-only-fail-closed.test.js`.
- Silent-failure detection as an anomaly class: `tools/fail_open_check.py` + `tools/fail_open_accepted.json` (11 accepted), `tools/optimistic_success_scan.py`, `tools/discarded_verdict_check.py`, `api/fail-open-triage-2026-09-04.test.js`, `.claude/skills/sairn-silent-failure-sweep/SKILL.md`; fault injection `tests/faults/` (`faultkit.js`, `transport_timeout_sweep.js` — 12 of 15 apps had no write timeout before 2026-09-11, `run_fault_suite_probe.py`).
- `docs/2026-09-14-supabase-504-root-cause.md` §8 — production runtime logs queried with controls to establish 0 failures over 24 h.

**PARTIAL**
- Logging is unstructured `console.*` (455 `console.error(`, 816 `console.log(` in non-test `api/`); no log aggregation (grep sentry / datadog / logtail / axiom / betterstack: only an unrelated naming guide). Supabase log retention one day; Vercel retention undocumented.
- Alerting covers exactly one anomaly class — a scheduled job stopping or failing. IRP §4.1: "That is the complete list." `SAIRN_ESCALATION_EMAIL` is not set (`CRON-LIVENESS-STATUS.md` `escalation_has_own_address: false`).
- Audit writes are best-effort and swallowed (`api/_lib/audit.js`). Two status documents disagree (CC2.1).

**MISSING**
- IDS/SIEM/anomaly detection on auth, licence-key or service-role use; egress monitoring; error-rate or latency alerting (the September cron 504 rate was found by a session reading logs, not by an alert); an uptime monitor for customer-facing routes (`docs/ACCEPTED-RISKS.md` AR-4, open with Michael 2026-09-14); a security-event analysis workflow.

**UNVERIFIED**: `sql/cron_heartbeat_schema.sql` applied in production (live rows imply yes; the record says NOT RUN).

### CC7.3 Evaluation of security events

**HAVE**
- IRP §1.1 (what counts as an incident, four historical examples) and §5 (SEV-1..4 keyed to tier, "Escalate on uncertainty, not on evidence").
- Impact inputs: the tier, SPOF, secrets and NHI registers (IRP §2); `docs/NHI-REGISTER.md` carries a service-role revoke procedure.
- `docs/defect-density-register.json` (271 records) with `detection_method`; `tools/defect_register.py` refuses a record with contributing factors but no `recurrence_open`.

**PARTIAL**
- Evaluation is defined on paper; the plan has never been exercised (§9). Severity determination depends on the secrets inventory, which is refusing to regenerate. The register's 3 `user-report` records are all internal tooling; no `detection_method` value for incident / production / customer exists.

**MISSING**
- An incident log distinct from the defect register; any record of an event formally evaluated as security incident vs not; breach-notification assessment criteria beyond §6.4's input list.

### CC7.4 Incident response program

**HAVE**
- `docs/2026-09-15-incident-response-plan.md` (487 lines, structured on NIST SP 800-61r3 and corrected against the publication itself on 2026-09-17): §1 roles and a session's MAY / MUST NOT; §6.1 first fifteen minutes (record time, do not remediate, contain toward fail-closed, notify, claim); §6.2 credential-compromise runbook (rotate in Vercel Production and Preview, redeploy, verify against the deployed URL, licence key = SEV-1); §6.3 data-integrity (blast radius from the audit chain, a correction is a new row, 1 FK across 459 tables so the external checker is the oracle); §6.4 notification inputs; §4.3 the checkpoint verifier as first forensic step.
- Containment-in-code exercised on operational incidents: `43a06d9d` and `b162c871` after the 504 RCA; the watchdog self-retry fix (item 54).
- Six drafted compromise procedures in `docs/NHI-REGISTER.md` ("DRAFTED, NOT REHEARSED, AND NOT VERIFIED").

**PARTIAL**
- Single responder, no secondary, no out-of-hours cover; "If Michael is unreachable, the platform's incident response is paused" (§1). No tabletop, no legal review, no customer-facing commitments (§9). Coverage against the 800-61r3 Community Profile subcategories is explicitly unmeasured (§9: "no completeness against SP 800-61r3 should be asserted anywhere — in a SOC 2 readiness discussion").

**MISSING**
- Incident register / ticketing; evidence-preservation steps beyond "do not remediate yet" (Supabase logs expire in one day); forensic capability outside the three checkpointed tables; periodic testing; training; contact roster; regulator / customer notification templates.

### CC7.5 Recovery

**HAVE**
- IRP §7 — honest recovery state: code recoverable (git, clones), schema reconstructable from `sql/*.sql` (structure only), configuration recoverable only if the secrets inventory is current, "Data is not recoverable"; audit checkpoints as the restore oracle for the three audit tables.
- `.github/workflows/nightly-backup.yml` and `tools/restore_coherence_check.js` (see A1.2 / A1.3).
- Post-incident: IRP §8 (a register entry with detection method; "a control, not a resolution"; make the control fail on purpose; update the plan). Root-cause analyses with real structure: `docs/2026-09-14-supabase-504-root-cause.md` (timing table, code-level cause, experiment, fix, live verification, what is NOT claimed, re-measurement), `docs/2026-09-15-item54-second-watchdog.md`, `docs/2026-09-16-hover-separation-push-rejection.md`.
- Resilience: `api/_lib/resilience.js` (timeout, bulkhead, breaker), `.claude/skills/sairn-resilience-patterns/SKILL.md`, `tools/retry_policy_audit.py`, `tools/retry_backoff_check.py` (finding: `api/sd-agent.js` agent loop with no delay or breaker), `tools/idempotency_check.py` + `tools/idempotency_triage.json` (31 files), `tools/rate_limit_race_model.js` + `docs/spec/RateLimitConsume.tla` (spec header: `sql/sairn_ai_rate_limit_consume_fn.sql` HAS NEVER BEEN RUN, so the racy path is live).

**PARTIAL**
- The backup mechanism has never produced a dump (10 of 10 runs failed — A1.2). The only production circuit breaker runs on a per-instance store with `canEnforce: false` (`docs/2026-09-18-circuit-breaker-enforce-decision.md`). Lessons flow into the defect register and dated docs, not an incident log; corrective controls are frequently report-only checkers.

**MISSING**
- A tested restore; RTO/RPO; a DR plan for loss of Vercel or Supabase beyond "code is in git"; a post-incident review template applied to a security incident; communication of recovery to affected parties.

---

## CC8 — Change management

### CC8.1 Change lifecycle

**HAVE — authorisation**
- Claims before work (`tools/sairn_claim.py`, 4h expiry, committed and pushed through the pre-push hook; `.claude/claims/README.md` says plainly it is not a lock); `tools/sairn_claim_hook.py` at SessionStart; `tools/session_lock_check.py` refusing a second live session in one clone; `.claude/settings.json` deny/ask permissions; `tools/git_push_master_guard.py`.

**HAVE — standards**
- `CLAUDE.md` Syntax rule and Push protocol; `docs/SAIRN-PROCESS-RULES.md` Part 3 (447-546) and §1.11; `.claude/skills/sairn-guardian-v2` (31 checks), `sairn-differential-review` (diff shape, seam, blast radius, seed inertness), `sairn-precommit-gate`, `sairn-adversarial-reviewer`, `sairn-api-tester`.

**HAVE — documentation and tracking**
- Commit convention: 50 of 50 sampled subjects carry a conventional prefix; 34 carry `Co-Authored-By`; 8 a `FILES:` trailer; long-form bodies with VERIFIED / NOT verified sections (e.g. `603ca439`).
- `tools/register_feed_gate.py` (pre-push deny; requirement date 2026-09-16); the open-work index; generated `docs/MASTER-PLAN.md`, `docs/traceability-matrix.md`, `docs/TOOLING-INVENTORY.md` with push check 12 / 12b denying a push that breaks them; per-session worklogs; `tools/verification_plan_staleness_check.py`.

**HAVE — testing before deploy**
- `tools/checkblocks.py` (HTML-parser extraction, `node --check` per block; note `tools/html_script_check.py`, the PostToolUse hook, does NOT check syntax by its own header, lines 91-97). Push checks 4, 5, 7, 9 (`GUARD_TESTS` over the whole tree, deny on failure; 10 entries in `docs/traceability-matrix.md` §1), 11, 14. `tests/push_gate/` (13 probes of the gate itself), `tests/faults/`, `tests/failsafe/`, `tests/claims/`. `docs/known-red-suites.json` (17 of 411).

**HAVE — independent approval**
- Push check 13 + `tools/tier_a_review_gate.py` (self-signed refusal; obligation must be recorded in the same push; 136 records, 115 reviewed by a different session, 0 self-signed, 17 verdicts contain "WEAK"). `docs/2026-09-16-item83-independent-review.md`.

**HAVE — deployment and post-deploy**
- `vercel.json` (build copies `*.html` to `dist/`, 22 routes, 4 crons); `.githooks/pre-push` order (hover scope gate → register feed gate → push gate); `.githooks/prepare-commit-msg` → `tools/staged_conflict_marker_check.py` (fires under `--no-verify` and `rebase --continue`); `.githooks/post-rewrite` → `defect_register.py --post-rewrite`. `tools/deploy_verify_notify.py`; `tools/landing_verification.py`; push check 1 (seed load state vs live licence for 4 apps; `docs/2026-09-09-load-state-gate-invocation.md`); `.github/workflows/source-manifest.yml`.

**HAVE — configuration baseline**
- `db/schema_snapshot.json` (`_generated_at` 2026-09-13 18:39 UTC, ~380 tables, 340 constraints) + `tools/load_schema_snapshot.py` (refuses a shrinking capture without `--allow-shrink`); push check 3 (`tools/sairn_sql_preflight.py --gate --require-live`, fail-closed); push check 2 (`tools/employee_auth_guard_check.py`); `tools/advisory_lock_isolation_check.py`; `tools/cleanup_confirm_check.py`.

**HAVE — emergency change / override**
- `SAIRN_SEED_GATE=off` at the front of the push command (blanket: exits before any check, hook 766-773, 2340-2343); `SAIRN_PROBE_PUSH=1` suppresses check 8 only; `docs/BYPASS-LOG.jsonl` (40 rows) via `tools/bypass_log.py`; `docs/2026-09-14-tier-a-bypass-audit.md`; `docs/2026-09-14-graduated-mechanical-commitment.md`; `docs/2026-09-15-item99-graduated-consent-for-irreversible-changes.md`.

**HAVE — environments and supply chain**
- `api/_lib/stripe-config.js` 72-82 distinguishes `VERCEL_ENV === 'production'`; IRP §6.2 treats Vercel Production and Preview as separate secret scopes. `package.json` / `package-lock.json`; `tools/npm_audit_check.py`; CodeQL; `docs/SOUP-REGISTER.md`; `docs/2026-09-18-slsa-build-provenance-scoping.md`.

**HAVE — change metrics**
- `tools/dora_metrics.py` (report-only, writes no file; lead time "NOT MEANINGFUL ON THIS TOPOLOGY"; time-to-restore from the register median 2 days, mean 6.65, max 58 over n=125).

**PARTIAL**
- Approval is by a different Claude session, never by a different human; no PR-based review; direct push to `main` auto-deploys to production; a required status check was tried on 2026-09-16, deadlocked every direct push, and was removed (`docs/2026-09-16-hover-separation-push-rejection.md` 65-107).
- No CI runs the test suite; `run_all_tests.py --hook` paused since 2026-09-10. Pre-deploy testing is author-run suites plus the gate's selected checks.
- Every gate is client-side, per-clone opt-in (`core.hooksPath`), fails open on internal error, and `tools/gh_push.py` is an API push path that bypasses all of it (status UNVERIFIED).
- 38 blanket overrides by one session in one afternoon (2026-09-21), each with a tool-generated reason; overrides are logged, not approved, and are not time-bound.
- No migration ledger: `sql/` has 338 files and no applied-state record; `tools/cleanup_confirm_check.py` 468-469: "This checker cannot tell you whether a file was run. Nothing in the repo can." Applied state is inferred from a hand-pasted snapshot that is 11 days stale; migrations are pasted into the Supabase editor by Michael.
- Post-deploy verification is automated for one file; the seed gate covers 4 apps.
- No `.github/dependabot.yml`; patching is manual.

**MISSING**
- A staging environment (only `main` on origin; Vercel preview usage UNVERIFIED); a documented rollback procedure (grep `rollback|revert` across CLAUDE.md, process rules, IRP and accepted risks: only a principle and a listed Michael-only action; no Vercel instant-rollback mention); human change approval; a change-management policy.

---

## CC9 — Risk mitigation

### CC9.1 Business disruption: BC/DR, backup, recovery, insurance

**HAVE**
- Backup design complete in code: `.github/workflows/nightly-backup.yml` (`40 3 * * *`; pg_dump piped straight into `age`, no plaintext on disk; 50 KB floor; provenance attestation; upload to Cloudflare R2; restore into a throwaway `postgres:15` + PostgREST; `tools/restore_coherence_check.js` with exit 2 treated as failure; 30-day retention sweep only after a proven restore; key shredded `if: always()`); `sql/backup_reader_role.sql` (SELECT + BYPASSRLS role, raises on the placeholder password); `docs/2026-09-14-nightly-backup-design.md`; `docs/2026-09-14-backup-restorability-scoping.md`; `docs/2026-09-15-backup-reader-default-acl-verification.md` (verify queries written, NEVER RUN).
- Restore oracle: hash-chained audit checkpoints (IRP §7.2).
- Availability monitoring: `api/cron-watchdog.js`, `.github/workflows/cron-liveness.yml`, `docs/CRON-LIVENESS-STATUS.md`.
- Resilience patterns (CC7.5). `docs/ACCEPTED-RISKS.md` — 4 formal entries (AR-1 Stripe portal, AR-2 "current" semantics, AR-3 EVV readiness, AR-4 watchdog shared scheduler), each with Where / Accepted by / Risk / Bounds / Trigger / Open with; `tools/accepted_risk_trigger_check.py` (clean 2026-09-24); `tools/accepted_risk_expiry_audit.py` (over the open-work index: 18 accept/defer decisions, 14 UNCONDITIONAL — no expiry condition at all).

**PARTIAL — the key fact**
- **The nightly backup has never produced a dump.** GitHub Actions for `nightly-backup.yml`: 10 scheduled runs, run 1 on 2026-09-15 through run 10 on 2026-09-24T08:43Z, all `failure`; run 10 failed at "Dump and encrypt in one pipe" in 0 seconds with every downstream step skipped — consistent with all ten required secrets absent, which the workflow's own header (44-57) and `docs/SAIRN-OPEN-WORK-INDEX.md` line 352 ("NEVER RUN — Michael to create the role and the secrets") both say. The newest written record in the repo is 2026-09-18 ("2 runs 2 failures"). **Net: no restorable copy of any Tier A data exists; RTO and RPO are undefined.** (Actions state was read through the GitHub API by a research sub-session; the failing step's stderr was not retrieved — UNVERIFIED as to exact cause.)
- Whether `sairn_backup_reader` in the live database holds the placeholder or a rotated password is UNKNOWN (`docs/NHI-REGISTER.md` open warning).
- Circuit breaker is observe-only; 6 of 23 compromise procedures are drafted and unrehearsed.

**MISSING**
- A business continuity plan, a business impact analysis, RTO/RPO, a DR test, a tabletop; a secondary responder; insurance (grep `business impact analysis|cyber insurance|insurance polic|E&O` over docs, skills and CLAUDE.md: the only hit is a customer RFP requirement in `sairn-software-architect/SKILL.md:39`).

### CC9.2 Vendors and business partners

**HAVE**
- Vendor identities and credentials enumerated with owner and scope: `docs/NHI-REGISTER.md` (anthropic-api, stripe-account, resend, oidc-client, quickbooks-oauth, courtlistener, stability-ai, sairncash-firebase-admin, alf-pharmacy, supabase_admin) and `docs/SECRETS-INVENTORY.md` (blast radius and absence behaviour per credential).
- Software-supplier risk: `docs/SOUP-REGISTER.md`, `tools/soup_register_check.py`, `tools/npm_audit_check.py`, CodeQL.
- Live vendor-status verification for Stripe: `docs/2026-09-17-sairncash-stripe-readiness.md` (expired `sk_test_` key; blocked on LLC).
- Contract layer (drafts): `docs/legal/` — DPA Amendment §3 requires a BAA with Anthropic before PHI processing; SAIRNdental agreement line 17: "No BAA exists between SAIRN and Anthropic."
- Vendor dependency awareness: `docs/SPOF-REGISTER.md` (`env:SUPABASE_URL` blast 70 with a live 504 incident); subprocessor disclosure named as a requirement in `sairn-software-architect/SKILL.md:39`.

**PARTIAL**
- The master DPA and ToS that the amendments modify are not in the repo; a subprocessor list is therefore not verifiable here. Supabase, Vercel, Cloudflare R2 and GitHub appear only as infrastructure facts, never as assessed vendors; the NHI register cannot see console-minted identities (Vercel token, Supabase PAT).

**MISSING**
- A vendor inventory with due-diligence evidence (their SOC 2 reports, executed DPAs/BAAs, SLAs, security reviews, contract dates, exit plans) for any of Supabase, Vercel, Anthropic, Stripe, Resend, CourtListener, Cloudflare, GitHub, Stability, Firebase/Google, Stedi — grep `sub-?processor|vendor inventory|vendor register` across docs, skills and tools: no such document. Vendor monitoring (status-page subscriptions, SLA tracking). A BAA with Anthropic while four PHI-adjacent apps forward prompts to the model (C1.1).

**UNVERIFIED**: whether any master DPA / ToS / BAA has been executed off-repo; whether Dependabot is enabled on the GitHub side.

---

## A1 — Availability

### A1.1 Capacity

**HAVE**
- AI capacity controls: `api/claude.js` app allowlist, server-side `max_tokens` clamp (217), per-app daily limiter with per-tenant sub-budget charged to the *verified* licence app (393-441); limiter failure is logged "AI rate limit NOT ENFORCED" and the response carries `rate_limit_degraded` (463-481) — fails open by design; `api/claude-cost-controls.test.js`; `api/sd-agent-budget.test.js` (agentic endpoint charged per model call). Knobs `SAIRN_AI_DAILY_LIMIT`, `SAIRN_AI_RATE_LIMIT_MODE`, `SAIRN_AI_TENANT_SHARE`, `SAIRN_AI_CONTENTION_FLOOR` (`docs/SECRETS-INVENTORY.md` 43-46).
- `api/_lib/resilience.js` (timeout, bulkhead, breaker); `docs/2026-09-18-circuit-breaker-enforce-decision.md`.
- A real capacity incident, root-caused and re-measured: `docs/2026-09-14-supabase-504-root-cause.md` (two hourly crons 504ing 40-50% of firings; unindexed cross-tenant scans and an unbounded `alf_mar` read; fix `43a06d9d`; crons spread to :07 / :37; 0 failures over 24 h on 2026-09-15).
- `docs/2026-09-05-anon-amplification-limiter-scoping.md`; `tools/rate_limit_race_model.js`.
- `tools/production_activity_snapshot.json` (72 h per-route invocation counts from Vercel logs, `captured_at` 2026-09-13; notes 7d/30d windows time out); `tools/activity_cadence.json` (two rows, "almost empty ON PURPOSE"); `tools/purpose_expired_measure.py` (13 of 64 routed endpoints observed — below its own 60% bar, so it classifies nothing).
- `docs/2026-09-17-shared-backend-tenancy-map.md` 23-28, 84 — the shared resources a tenant can exhaust ("exhaust connections, lock a shared row, fill disk"; "Storage and egress quotas. No per-tenant accounting exists to read.").
- The single-file ceiling as a named capacity surface: `CLAUDE.md` ("around 2.0MB and growing"); `.claude/skills/sairn-software-architect/SKILL.md` 68-72; `.claude/skills/sairn-perf-profiler/SKILL.md` 86-96.

**PARTIAL**
- The AI limiter's production mode (observe vs enforce) and whether the atomic RPC is live are not recorded in the repo (`tools/rate_limit_race_model.js` 27-39). Capacity observation is one 72 h snapshot, not a recurring measurement. Whether the 504-fix indexes (`sql/dnt_appointments_due_index.sql`, `sql/alf_mar_sweep_index.sql`) were applied: "NOT RUN … I did not verify" (RCA §8).

**MISSING**
- A capacity plan; utilisation thresholds or dashboards for Supabase (free-tier DB size, connections, egress), Vercel (invocations, duration), R2, Anthropic spend; forecasting; a review cadence.

### A1.2 Backups, redundancy, recovery infrastructure

**HAVE** — see CC9.1: the workflow, the backup-reader role, the design and scoping docs, the restore oracle, the SPOF register, the two watchdogs, `api/provisioner-health.js` (a recoverability monitor for tenant admin lockout, not uptime).

**PARTIAL**
- 10 of 10 nightly-backup runs failed at the dump step; no offsite copy of any data exists (CC9.1).
- Redundancy: none — one Supabase project and key, one session-signing secret, one encryption key; 0 SPOF rows retired since 2026-09-14.
- Monitoring reaches a human only for scheduled-job silence.

**MISSING**
- A successful backup; point-in-time recovery, replica or failover; a DR runbook beyond IRP §7 ("Data is not recoverable"); an uptime monitor or status page (grep uptime / statuspage / pingdom / betterstack / healthcheck across `api/`, `docs/`, `vercel.json`: only AR-4 and the watchdog's own comment); vendor SOC reports or environmental-control evidence (all infrastructure is Vercel + Supabase + GitHub).

Note: `tests/faults/sv_backup_write_faults.js` and `tests/dnt_vendor_backup_probe.py` test client-to-server sync of localStorage collections, not database backups. Do not cite them here.

### A1.3 Recovery testing

**HAVE**
- `tools/restore_coherence_check.js` — three-state checker: recomputes every audit-checkpoint digest against the restored audit tables with paged reads checked against the server count; derived referential coherence from `db/schema_snapshot.json` with ambiguity refused; optional row-count baseline. Header states it covers only the three audit tables and that its context is "THE HAND RESTORE". `tests/run_restore_coherence_probe.js` drives it against a local mock server (26 arms) — the tool works on fixtures.
- Wired as steps 9-12 of `nightly-backup.yml`; would run every night if a dump ever succeeded.
- `docs/2026-09-14-backup-restorability-scoping.md` 137-144 sizes the negative control ("restore a deliberately truncated copy and demand the check find it") — not built.

**PARTIAL**
- Restore tooling exists and has never seen a real dump; the design doc says the restore step "is the one most likely to need fixing" (`docs/2026-09-14-nightly-backup-design.md` 145-148).

**MISSING**
- Any tested restore (IRP §9: "no tested restore — because there is nothing to restore"); a tabletop; a DR test schedule; an RTO/RPO to test against.

---

## C1 — Confidentiality

### C1.1 Identification and classification; retention

**HAVE**
- `docs/CRITICALITY-TIERS.md` — per-resource register with a **Confidentiality axis added 2026-09-22** (27-40): Confidentiality-A = "PHI, a clinical record, legally privileged or client-confidential material, vital records and government identifiers, an individual's compensation, an authorisation map, or the firm's own confidential commercial position"; Tier = worse of the two axes; evidence mandatory on A; rollups per app (e.g. sairnvet 29/42 A, sairnlaw 18/20 A, sairndental 18/25 A). `docs/2026-09-21-criticality-tiers-two-axis-spec.md` grounds it in the FIPS 199 high-water mark.
- `tools/confidentiality_candidate_flagger.py` (SUITE-ONLY, advisory) — flags B/C rows for human confidentiality review by name, payload fields read from the app's own record literal, and client/server asymmetry; "IT FLAGS. IT DOES NOT SCORE"; `tests/confidentiality_flagger_asymmetry_review_probe.py`.
- Secrets classified CREDENTIAL / ENDPOINT / ADDRESS / TUNING (`docs/SECRETS-INVENTORY.md` 18-24; tool refuses on an unclassified variable).
- `docs/2026-09-15-sairnlaw-privacy-scoping.md` — scopes `law_pimedical`, trust and operating transactions, bank statements, client identifiers, portal messages "from the schema, not from the sales description"; states no SOC 2 readiness material existed on 2026-09-15 (§3).
- Minimum-necessary and leakage controls: `api/sd-data.js` HIPAA gate on `sen_clients` (~4966) and dental financial tiering (~11574); `api/sd-data-dental-provider-scope.test.js` (provider sees only own patients); `tests/phi_cache_scoped_to_user.js`; `tests/public_token_leaves_the_address_bar.js`; `tests/intake_link_no_credential.js`; `api/_lib/mech-redact.js`; `api/sairnvet-transcribe.js` (no audio to disk, log or response; refuses without a consent reference); `docs/2026-09-23-sairnvet-ambient-scribe-consent-scoping.md`.
- Field-level encryption for three secret classes (CC6.1); `docs/2026-09-24-sd-encryption-key-revoke.md`.
- `tools/redaction_check.py` as PreToolUse hook and push check 6 (`sairn_push_gate_hook.py` 1217-1368) — a secrets scanner, not a PHI/PII scanner; fails OPEN with a printed "UNCHECKED for credentials" note if the scan cannot run (1363-1368).
- Retention: `SC_RETENTION_FLOOR_YEARS = 10` (`api/sd-data.js:150`; `RETENTION_BELOW_FLOOR` refusal on the settings write) — the one retention number on the platform; `docs/BIOMETRIC-RETENTION-POLICY.md` (notice → purpose/duration → signed release; destroy at the earlier of purpose satisfied or 3 years after last interaction; enforced by a generated `destroy_by` column); `docs/2026-09-14-class-a-retrievability.md` + `tools/export_coverage_check.py` (retrievability, not retention).
- Legal drafts: DPA Amendment §3 requires a BAA before PHI; dental agreement §5 classes its data as PHI under the DPA; both per-app drafts note "DPA §6 promises deletion on request; the dnt_* grants do not include a general DELETE".

**PARTIAL**
- Classification exists as an engineering register keyed by resource; there is **no written data-classification policy** (levels, handling rules, labelling, owners, review cadence). 7 rows are still "NOT YET INDIVIDUALLY READ" on confidentiality.
- Retention: one app has a configurable floor that nothing reads; no retention schedule per data class; no purge; the one real policy governs data nobody collects (`docs/2026-09-14-record-retention-and-retrievability.md`: 11 of 11 Class A tables carry no retention statement).
- **PHI reaches Anthropic unredacted, by code.** `api/claude.js` 200-221 forwards `system` and `messages` verbatim (only `max_tokens` clamped and `tools` sanitised); grep for redact / PHI / scrub in `api/claude.js`: none; direct callers `api/sd-agent.js:132`, `api/legal-citator.js:89`; sairndental, sairnsenior, sairncare, sairnvet and sairnlaw are all allowlisted; `tests/phi_cache_scoped_to_user.js` 19-24 confirms resident/client PHI is built into the outbound prompt. No BAA with Anthropic (dental agreement 17-20; open-work index line 690). Anthropic data-retention / zero-data-retention status of the key: UNVERIFIED (no document addresses it).
- Confidentiality commitments to customers exist only as unexecuted drafts amending masters not held in the repo; subprocessor list and breach-notification window in the master DPA: UNVERIFIED.

**MISSING**
- A data-classification and handling policy; a data inventory mapping classes to storage (the tier register is the closest thing); a retention schedule; labelling; operator NDA/confidentiality evidence; a subprocessor list; PHI/PII redaction before AI calls.

### C1.2 Disposal

**HAVE**
- Soft delete (`api/sd-data.js` `soft_delete` sets `_deleted_at`; reads filter it out) with resurrection tests (`tests/customer_delete_does_not_resurrect.js`, `tests/collection_delete_reaches_the_server.js`, `tests/dnt_vendor_backup_probe.py`).
- `sql/unused_delete_grant_revoke_2026-08-24.sql` (run 2026-08-25): `service_role` lost DELETE on 134 tables — the API physically cannot hard-delete outside `sc_*` and the biometric template table.
- `tools/removal_path_check.py` + `tools/removal_path_baseline.json` — measured 2026-09-10: 389 registered resources, 50 declare a removal verb, 339 declare none (grandfathered; only a NEW stuck resource fails). `tools/cleanup_confirm_check.py`; `tools/cleanup_residue_check.py` (read-only; 28 statements blocked by `NO_SESSION` on its last run).
- The biometric destruction design (not provisioned); the encryption-key revoke procedure (crypto-shredding of encrypted secrets); device-level PHI cache purge.

**PARTIAL**
- Deletion hides rows; nothing ever hard-deletes `_deleted_at` rows; backups, once they exist, would be an encrypted 30-day rolling set into which no data-subject deletion propagates.

**MISSING**
- A tenant / licence offboarding deletion procedure (grep docs for offboard / right to erasure / GDPR / "delete all": hits are competitive research, legal drafts and the tier register — none is a procedure); a data-subject request process; disposal for logs, R2 objects, Vercel logs or Anthropic-side data; certificate-of-destruction workflow; end-of-retention disposal (no retention schedule exists). The drafts' own note: DPA §6 deletion "needs owner-level database work".

**UNVERIFIED**: whether any customer offboarding has ever occurred and how data was handled.

---

## Cross-cutting facts an assessor will ask about first

1. **Single operator, no oversight body.** One human holds every credential and every admin console; every "independent" reviewer is a Claude session that person runs; incident response pauses if that person is unreachable (IRP §1, §9; `tools/nhi_register.py` 359-362).
2. **No restorable copy of any data.** Supabase free tier; 10 of 10 nightly-backup runs failed at the dump step; RTO/RPO undefined; "Data is not recoverable" (IRP §7).
3. **Gates are client-side and overridable.** Two entry points, both on the operator's workstation, both fail open on internal error, per-clone opt-in; 39 blanket overrides logged, 38 by one session in one afternoon; no CI test run; no required status check; a GitHub-API push path (`tools/gh_push.py`) bypasses all of it.
4. **One git identity, six push-capable clones, direct push to `main` deploys to production.** Attribution is derived from claim files and trailers, not native.
5. **PHI is forwarded to Anthropic verbatim with no BAA**, from five allowlisted apps, while the customer-facing legal documents are unexecuted drafts and the masters are not in version control.
6. **Detection reaches a human for exactly one anomaly class** (a scheduled job going quiet); no log aggregation, one-day Supabase log retention, no incident log, an incident-response plan that has never been exercised.
7. **Three information baselines are red today**: `secrets_inventory.py --check` refusing, `schema_snapshot_freshness.py` FAIL (260 h stale), `tooling_inventory.py --check` FAIL; `docs/AUDIT-CHECKPOINT-STATUS.md` ten days stale and contradicted by the live watchdog.
8. **No policy set in the SOC 2 sense.** What exists is a working-repository rule set for AI sessions (CLAUDE.md, process rules, 34 skills) plus one real external policy for data nobody collects. `SECURITY.md` is an unfilled template.
9. **The platform's own honesty is unusually strong evidence.** Registers refuse to render on bad input, checkers report COULD NOT TELL as a third state, corrections are dated in place, and most gaps above are already written down somewhere in `docs/` by the platform itself. An assessor will find the gaps quickly because the repository names them; that is a design strength and a readiness weakness at once.

---

## Ranked gap list

Ordered as a SOC 2 Type I readiness assessment would flag them: a Type I tests whether controls are *designed and implemented* at a point in time, so the first things flagged are criteria where there is nothing to point at, then criteria where what exists cannot be evidenced as a control (no policy, no owner, no operating record), then design weaknesses in controls that do exist. Regulated-data exposure raises priority.

### Tier 1 — nothing behind the criterion, or the criterion is effectively failed

| Rank | Criterion | What is missing | Why it is flagged first |
|---|---|---|---|
| 1 | A1.2, A1.3, CC9.1, CC7.5 | No backup has ever succeeded; no restore has ever been tested; no BCP, BIA, RTO/RPO, DR plan or insurance | Availability cannot be opined on at all. Tier A data (controlled substances, trust money, patient charges) has no recovery path. The mechanism exists in code, so the fix is operational (secrets and a role) rather than a build — which is also why an assessor will not accept "in progress" |
| 2 | CC5.3, CC1.1, CC2.2 | No information-security, access-control, change-management, vendor-management, data-classification, acceptable-use or BC/DR policy; no code of conduct; no policy acknowledgement | A Type I is tested against management's own policies. With none written, every other criterion lacks the "what is expected" half; the working-repo rules for AI sessions do not substitute because they name no owner, approver or review date |
| 3 | CC1.2, CC1.3, CC5.1, CC6.3 (SoD) | No board or oversight body; no segregation of duties possible with one human; one git identity for five roles | Structural. Cannot be closed by tooling; needs at least a second human with a defined role, or a documented compensating-control rationale the assessor can evaluate |
| 4 | CC9.2, C1.1 (BAA), CC2.3 | No vendor inventory or due diligence; no BAA with Anthropic while PHI is forwarded unredacted; all customer contracts unexecuted drafts; masters not in the repo | Legal exposure, not just a control gap: HIPAA-relevant data flows to a subprocessor under no agreement. An assessor treats an absent BAA on a PHI flow as a stop-the-engagement finding |
| 5 | CC6.4 | No physical-security evidence; reliance on vendor SOC reports that have not been obtained | The cheapest Tier 1 item to close (obtain Vercel/Supabase/GitHub SOC 2 reports; write a one-page workstation policy), which is why it ranks last in this tier |
| 6 | C1.2, CC6.5 | No tenant offboarding deletion, no retention schedule, no purge; deletion "needs owner-level database work" while the draft DPA promises deletion on request | A promise in the contract that the product cannot keep is a finding on its own |
| 7 | CC1.4, CC1.5 | No training, onboarding, competence, background-check or performance records | Structural with one person; an assessor will accept a short documented rationale plus vendor-side controls, but nothing exists to accept today |
| 8 | A1.1 | No capacity plan, thresholds or monitoring for the free-tier database, Vercel quotas or AI spend | One 72 h snapshot and a fail-open AI limiter of unrecorded mode are not a capacity control |
| 9 | CC3.3 | No fraud-risk assessment (management override, insider, solo operator with full production access) | Specific fraud-shaped controls exist (witnessing, three-way match); the assessment that would justify them does not |

### Tier 2 — something exists but cannot be evidenced as a control

| Rank | Criterion | Gap | Note |
|---|---|---|---|
| 10 | CC8.1 | Direct push to production; no CI test run; client-side fail-open gates; 38 blanket overrides; no staging; no rollback procedure; no migration ledger; `run_all_tests --hook` paused since 2026-09-10 with re-enable conditions met | The gate design is unusually thorough; what is missing is server-side enforcement, a human approval step and an operating record |
| 11 | CC7.2, CC7.3, CC7.4 | One alerting class; no log aggregation; one-day log retention; no incident log; plan never exercised; single responder | The incident-response plan is real and honest; it needs a tabletop, an incident register and a second responder to become a control |
| 12 | CC6.2, CC6.1 | No access reviews; no onboarding/offboarding for humans or agents; no operator-console MFA evidenced; no credential rotation ever attested; licence entitlements unrevokable from code; secrets inventory refusing to regenerate | Tenant-side credential lifecycle is well built (bootstrap, setup, set_active, last-admin, lockout, per-request active check); the gap is on SAIRN's own side |
| 13 | CC3.1, CC3.2, CC3.4 | No entity-level objectives, availability target or risk appetite; no periodic risk-assessment sign-off | The registers (tiers, SPOF, secrets, NHI, accepted risks) are strong evidence of *identification*; the missing piece is the governance wrapper |
| 14 | CC4.1, CC4.2 | Monitoring runs only on the operator's workstation; no monitoring plan; no management review record; three generated baselines currently red; severity rubric unratified; no remediation SLAs | The meta-monitoring (controls that test controls) is the platform's strongest area and will impress an assessor; it still needs a written plan and a review log |
| 15 | CC6.6, CC6.7 | WAF log-only; no HSTS/CSP; AI proxy observe-mode default and fail-open; four pilot-only unauthenticated writes; licence key as a long-lived browser bearer; Tier A data in localStorage; no export authorisation | Design weaknesses in controls that do exist |
| 16 | CC6.8, CC7.1 | Four CDN scripts without SRI; no Dependabot config; CodeQL default pack only; no Python dependency scan; no DAST; both configuration baselines stale | Scan-only, no triage record |
| 17 | CC2.1, CC2.3 | Status documents disagreeing; no system description; unfilled `SECURITY.md`; no subprocessor list; no status page | Largely documentation |

### What would move the most criteria for the least work (not a plan — a reading of the table)

- Setting the ten backup secrets and running `sql/backup_reader_role.sql` turns rank 1 from "nothing" to "a nightly restore-tested backup", touching A1.2, A1.3, CC7.5, CC9.1 at once; the code is already written and its own restore test would prove it.
- Obtaining a BAA (or an executed zero-data-retention arrangement) with Anthropic, or redacting PHI before the call, addresses the single largest regulated-data exposure (rank 4).
- A short policy set with a named owner and review date — even one page each — converts most of Tier 2 from "cannot be evidenced" to "designed", because the mechanical controls behind them already exist.
- A required status check on `main` that runs the test suite and the push gate server-side would close the largest CC8.1 design gap; the platform has already recorded why the first attempt deadlocked (`docs/2026-09-16-hover-separation-push-rejection.md`) so the second attempt can be designed around it.

---

*Re-verify before quoting any count here. Every figure was true of `da1cc791` on 2026-09-24 and several of the sources it was read from (the tooling inventory, the schema snapshot, the secrets inventory, the open-work index) are already known to move faster than the documents that describe them.*
