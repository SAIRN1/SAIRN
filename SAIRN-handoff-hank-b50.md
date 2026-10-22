# SAIRN handoff — hank b50 — 2026-10-22

**Subject:** npm ci, the five Tier A reviews assigned to hank, the hover deny check. No product code changed.
Written before the report, nothing half-finished.

**Methodology concept:** *a reviewer's verdict is measured, not read. Every claim in an obligation is either
reproduced against the code at HEAD or marked as not reproduced.*

## 1. PUSHED STATE
- The claim commit `14474af83` is on origin.
- This push: `docs/tier-a-reviews.json` (5 discharges), plus this handoff, the report and the digest.
  **NOT FORCED.** Re-derive the tip after the push.

## 2. CLAIMS HELD
`tier-a` (b50) is released at the end of the batch.

## 3. THE ITEMS
**1. npm ci — DONE.** It is denied for the agent at both the project and user level (kept, per Michael), so I didn't run it. Michael
agreed to run it via `!`, and `node_modules` was present afterwards. `python tools/dependency_integrity_check.py` → CLEAN on all four manifests.

**2. Tier A reviews.** cc's b46 handoff flags no Tier A commits for hank, which does not match the dispatch.
Michael chose to review the 5 obligations whose `reviewer_owner` is hank. My own 3 (`2fe89f267`, `38b2b5069`,
`040ac5a95`) stay with cc, because I can't review my own commits.
- Each review was done by a read-only subagent; probes ran only in the scratchpad.
- I re-checked both DEFECT code paths myself before discharging.
- All 5 are DISCHARGED, with the full verdict text in the ledger.

| author / opened | reviewed sha | verdict |
|---|---|---|
| cody 10-13 07:38 (law/sen read paths) | 3a1ab998c | SOUND-WITH-GAPS: readiness consumption arm is owner-only; the inventory regex is shape-fragile |
| cody 10-13 11:41 (sf/bld role arms) | 24e88957 | SOUND-WITH-GAPS: no `touched>0` ALLOW control; ALLOW asserts only not-403 |
| cody 10-14 10:33 (alf MAR grant suite) | a47cdf2d | **DEFECT in product code:** billing reads a MAR via the assignment tier with no grant and no audit |
| cc 10-19 22:00 (criticality_tier_check) | 38bbd4551 (= ca1597f) | **DEFECT, low:** omitted `app:` is invisible (:320); SHAPE_ERROR crashes (:986); the arm count is a literal (:923) |
| cody 10-20 08:43 (b28 countersign + caps) | 7e43c9dab (= 9a97201) | SOUND-WITH-GAPS: fails closed; the caps widen non-photo bytes |

**3. fix-deny.ps1 — ALREADY APPLIED.** `.claude/settings.local.json` has all 8 entries: Edit and Write × SAIRN-hover
and SAIRN-hover2 × `//C:/Users/marsh/Documents/...` and `~/Documents/...`. It also has the 5 Bash hover denies
from b38. Nothing changed.

## 4. OPEN, AND THE EXACT NEXT STEP
| # | open | owner | next step |
|---|---|---|---|
| D1 | billing + assigned + no grant → MAR 200 (`api/sd-data.js`, family MAR assignment tier, ~14548) | hank | Needs dispatch authorisation. Then: in the assignment tier, refuse when `ALF_MAR_GRANT_GRANTEE_ROLES[session.role]` and there is no grant. Add an arm for billing+assigned+no-grant expecting 403. Open a Tier A obligation. |
| D1b | the MAR audit fails open (the `alfAudit` result is ignored); 400 grant refusals are unaudited | hank | decide with D1 |
| D2 | criticality_tier_check: missing `app:` is skipped silently; SHAPE_ERROR crashes and exits 1 | cc | report it (no `continue` on None for a resources file); print SHAPE_ERROR; derive REGISTRY_PROPERTY_ARMS |
| G1 | test gaps in the cody suites (sen readiness non-HR arm, sf/bld touched>0, MAR A2/A3) | cody | add the arms listed in the ledger verdicts |
| T1 | Tier A reviews of `040ac5a95`, `38b2b5069`, `2fe89f267` | cc | unchanged |
| B | schema snapshot re-export | Michael | unchanged |

## 5. TRANSCRIPT
C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-hank\a9d72ca8-d218-42be-9363-f759795e9517.jsonl
