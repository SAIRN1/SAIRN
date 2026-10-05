# SAIRN-PLATFORM — Handoff, 2026-09-26 (cloud-research lane)

Written at a natural stopping point, at Michael's request, so a fresh session can
take over. Every claim below was re-checked against git, GitHub and the files at
the time of writing. Treat each one as a claim to re-verify, not a fact (§5).

**Why this file is in `docs/cloud-research/` and not the repo root.** This
session's standing rule for every dispatch was: new files only,
`docs/cloud-research/` only, no platform code, claims or tier registers. Dated
handoffs normally sit at the repo root (for example
`SAIRN-PLATFORM-2026-09-11-pushgate-empty-range-handoff.md`), so a root-level
`ls *-handoff.md` will **not** find this one.

---

## 0. What this session was

- **Identity.** A Claude Code **cloud** session: clone `/home/user/SAIRN`,
  designated branch `claude/wizardly-ride-wtun13`. It is not one of the five
  platform identities (Hank, CC, Cody, Fourth, hover auditor).
- **Work.** A series of isolated external research dispatches ("same lane").
  Each produced one sourced markdown document in `docs/cloud-research/`, and all
  of them landed as successive commits on **one** PR, SAIRN1/SAIRN#18. There is
  only one PR because GitHub allows one open PR per head→base pair and the
  harness allows pushes only to the designated branch.
- **Method, the same in every doc:**
  - internal grounding against the app file comes first;
  - research subagents run in parallel;
  - every claim carries a URL and an access date;
  - snippet-only findings are flagged, and conflicting figures are kept rather
    than resolved;
  - each doc opens with a §0.1 caveat on blocked network access.

## 1. Verified current state (2026-09-26)

| Fact | Value | How checked |
|---|---|---|
| `origin/main` HEAD | `52bb093a` | `git rev-parse origin/main` after a fetch |
| Branch HEAD (= `origin/claude/wizardly-ride-wtun13`) | `c2f2eb68` before this handoff's own commit | `git rev-parse` |
| Branch vs main | 8 doc commits ahead (9 with this handoff); 150 behind; merge-base `ca9adaa0` | `git log origin/main..HEAD`, `git rev-list --count HEAD..origin/main` |
| PR SAIRN1/SAIRN#18 | Open, not merged, not draft | GitHub API |
| Checks on `c2f2eb68` | **Passed:** CodeQL, Analyze (python), Analyze (javascript-typescript), GitGuardian, hover-separation, Vercel. **Failed:** `github-advanced-security` | GitHub check runs |
| Cause of that failure | GitHub-side. The Copilot code-scanning agent errors with `CAPIError: 400 The requested model is not supported` before analysing anything. The workflow has failed on all of its last 8 runs (runs 26–33), across SAIRN1/SAIRN#27, SAIRN1/SAIRN#28 and SAIRN1/SAIRN#18. A standing-down comment is posted at https://github.com/SAIRN1/SAIRN/pull/18#issuecomment-5848599425 | Job logs and the workflow run list |
| Are this session's 8 docs on `origin/main`? | **No.** Only `SAIRNlaw-external-competitive-gap-audit-2026-09-25.md` and `SAIRNvet-external-competitive-gap-audit-2026-09-25.md` are in `docs/cloud-research/` on main | `git ls-tree origin/main docs/cloud-research/` |
| `sairnbiz.html`, `stonedesk.html` | Unchanged between `f7d1eba0` (where the SAIRNbiz doc's line numbers were taken) and `52bb093a` | `git diff --stat` |
| Shared status registry row `SAIRN` | `idle` | `python tools/sairn_status.py` |

**Environment facts a new cloud session will hit:**
- `python tools/sairn_claim.py check …` fails here with
  `sairn_session_identity.NoIdentity: THIS CLONE IS NOT PROVISIONED`. This
  session deliberately did not provision itself under a borrowed platform name.
  It read the SessionStart hook's advisory claims list instead.
- `WebFetch` returned `EGRESS_BLOCKED` for nearly every external domain. The
  only one that worked was `sourceforge.net`.
- The session-wide `WebSearch` cap (200 calls, shared by all subagents) ran out
  during the SAIRNbiz pass. A new session should get a new budget; that is not
  verified.
- SessionStart hooks repeatedly raised a "SESSION LOCK WARNING" for this clone,
  with no liveness data. `git` never showed any divergence.

## 2. Commits this session, in order

From `git log --reverse origin/main..HEAD`:

1. `c99ffc1e` docs(cloud-research): SOC 2 readiness deep research, five new angles
2. `eddec416` docs(cloud-research): SAIRNvet external competitive-gap audit, pricing/CDS/exotics/telemedicine delta
3. `b24ce833` docs(cloud-research): StoneDesk external competitive-gap audit, measurement/scheduling/OSHA/AI-review delta
4. `b7830a69` docs(cloud-research): Novaclad capability teardown vs StoneDesk WebXR AR measure
5. `89c0fc14` docs(cloud-research): SAIRNlaw external competitive-gap audit, jurisdiction/citator/portal/privacy delta
6. `130f8408` docs(cloud-research): SAIRNcode external competitive-gap audit, encoders/autonomous-coding/specialty/denial delta
7. `1adefca0` docs(cloud-research): SAIRNcode autonomous-coding wide-lens supplement
8. `c2f2eb68` docs(cloud-research): SAIRNbiz external competitive-gap audit, wide lens
9. This handoff.

## 3. What was CORRECTED, not just added

**Brief premises that did not hold.** Each is stated in the relevant doc's §0
rather than silently worked around.
- **"No fresh external audit exists."** False for SAIRNvet and SAIRNlaw:
  same-topic `…-2026-09-25.md` docs already existed in `docs/cloud-research/`,
  and both are now on main.
- **StoneDesk's audit "likely drifted."** It had not. The 2026-09-02 audit had
  been kept current through in-place corrections. Seven of its 8 gaps are closed
  or decided; only slab-scanner integration is still open.
- **SAIRNcode "confirmed closed / no open items."** Contradicted by
  `docs/competitive-gap-audit-sairncode.md` (2026-09-23), which names autonomous
  coding as its largest open gap.
- **SAIRNbiz as an "HR+payroll+accounting" bundle with "embedded payroll."**
  Its payroll only calculates, by design. It does no withholding, payment,
  filing or remittance, and has no I-9 or E-Verify.
- **Novaclad as a shipped competitor** (as flagged in the StoneDesk doc). The
  teardown found no App Store listing and waitlist language on its site, so it
  is most likely not shipped yet.
- **The SAIRNbiz A2 blocker in the 09-03 internal audit** (a hardcoded timesheet
  array) no longer holds. Timesheets are store-backed now; the gap has moved to
  payroll gross ignoring recorded hours.

**Positioning assumptions that did not survive.** SAIRNlaw's citator and
deadline engine are matched or exceeded by Clio (the CalendarRules acquisition
in 2021, and vLex for $1B in 2025). In the other direction, SAIRNcode's refusal
to publish an uncalibrated denial-probability score turned out to be
defensible, not a weakness.

**My own slip.** A mid-session status line said four SAIRNcode research agents
were still running. There were three.

**Still unresolved, and deliberately kept rather than picked:**
- the date of the Gusto Simple price rise (most sources say March 2026; one says
  March 2025);
- the Clio Accounting launch date (July 2024 vs "early 2026");
- the Guideline acquisition price ($600M vs $1B+).

## 4. Open items, prioritized

**1. RESOLVED 2026-09-26: the SAIRNvet path collision with SAIRN1/SAIRN#28.**
- SAIRN1/SAIRN#28 (Fourth, branch
  `fourth/sairnvet-external-gap-audit-2026-09-26`) adds
  `docs/cloud-research/sairnvet-external-competitive-gap-audit-2026-09-26.md`,
  the path commit `eddec416` originally added on SAIRN1/SAIRN#18.
- Michael chose to rename this session's copy. It now lives at
  `docs/cloud-research/sairnvet-external-competitive-gap-audit-pricing-cds-2026-09-26.md`
  and carries a cross-link to Fourth's doc, which has the higher evidence grade
  (8 vendor pages opened directly). SAIRN1/SAIRN#28 was not touched.

**2. Review and merge SAIRN1/SAIRN#18.**
- It is docs-only, and its red check is GitHub-side (§1).
- This session did not subscribe to PR events and has scheduled no check-ins. A
  session that is going to drive the PR should subscribe.
- If main conflicts arise, merge main into the branch; never rebase or
  force-push.

**3. SAIRNbiz internal findings F1–F5 need the owning build session.** The full
text is §0.3 of `docs/cloud-research/sairnbiz-external-competitive-gap-audit-2026-09-26.md`.
No session held a SAIRNbiz claim at the last SessionStart advisory.
- **F1:** "1099 Required" uses a $600 threshold (`sairnbiz.html:3804`, `:968`,
  `:3774`, `:3830`). OBBBA raised it to $2,000 for payments made after
  2025-12-31, CPI-indexed from 2027. The tile therefore over-counts 2026
  vendors paid $600–$1,999.99.
- **F4:** the Benefits panel's plan cards (`sairnbiz.html:684-710`) are static
  HTML shown to every licence. They carry invented figures, including "Plan
  Assets (est.) $284,000", "Avg 5.2%" and "Workers Comp — Active · BWC Ohio".
  This is the fabricated-KPI class.
- **F2:** overtime is computed only above 40 hours a week (`:3113`), which is
  wrong in CA, AK, NV and CO. Payroll gross uses scheduled hours, so recorded
  overtime reaches no payroll figure at all.
- **F3:** Employee FICA leaves out the 0.9% Additional Medicare Tax on wages over
  $200,000, and the app does not disclose that.
- **F5:** the only "included free" wording anywhere is in StoneDesk's AI prompt
  (`stonedesk.html:12427`). There is no SAIRNbiz agreement, and the FTC's
  16 CFR 251 conditions on "free" offers apply.

**4. For whoever administers the repository.** The `github-advanced-security`
workflow fails on every PR ("model not supported"). Fixing it is a
code-scanning/Copilot settings change, not a code change.

**5. Coordination with active claims** (last SessionStart advisory,
2026-09-26):
- Fourth's `fourth-q9` includes a "SAIRNlaw positioning rewrite". The SAIRNlaw
  doc on SAIRN1/SAIRN#18 (its Clio-parity findings) is direct input to that.
- Cody's `cody-q10` includes "stonedesk 8th competitive gap". The StoneDesk and
  Novaclad docs on SAIRN1/SAIRN#18 are input to that.

**6. Research never done because the search cap ran out.** Each doc lists its
own gaps. The fullest list is the SAIRNbiz doc's "What this document does not
establish". A follow-up pass needs a session with a fresh search budget.

**7. Other open cloud-research PRs, with no path collision with this branch:**
- SAIRN1/SAIRN#3 (`docs/cloud-research/soc2-evidence-map.md`), which is on a
  topic next to this session's SOC 2 doc;
- SAIRN1/SAIRN#4 (trades/mechanical);
- SAIRN1/SAIRN#15 (SAIRNcare);
- SAIRN1/SAIRN#16 (SAIRNroofing);
- SAIRN1/SAIRN#17 (SAIRNdental).

## 5. Standard verification reminder

Before trusting any claim here, including this one:
- verify the `origin/main` HEAD and the branch;
- check PR SAIRN1/SAIRN#18's state and its checks;
- re-run anything relevant yourself.

This document reflects 2026-09-26 only.
