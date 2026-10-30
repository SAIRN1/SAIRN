# H1 b114: the test_965 Tier A verdict, ready to record (Michael's b114 item 2)

**What this is.** Michael's b114 instruction: keep the Tier A obligation for `test_965` with hover (not hover2), and record the verdict through the Tier A review-obligation path: SOUND on the real change, FINDING on the false-pass paths, premise stale since commit `f02a61f02` (2026-10-28 08:21:30 -0400 = 12:21:30Z; cc b61, not hover's commit). The verdict is written and its claims were driven by hand at b114; it is in the sibling file `2026-10-30-h1-b114-test965-verdict.txt`.

**Why it is not recorded yet.** Two controls stand between hover and the ledger, both correct under their own rules, and neither was loosened:
1. `tools/tier_a_review_gate.py` is a builder tool; the hover builder-path deny hook refuses to run it ("executes builder code", block row 2026-10-30 in `SAIRN-SESSION-LOCKS/deny-blocks.log`). Only `digest_lint.py` has an exemption.
2. `docs/tier-a-reviews.json` is the build agents' shared ledger, outside this role's scope gate (the b92 attempt was refused at commit for the same reason).

**The exact command, for whoever holds the permission (Michael, or a builder at his word):**

    python tools/tier_a_review_gate.py --discharge hover 2026-10-28T21:14:26Z --takeover --body-file .claude/skills/sairn-hover-auditor/routing/2026-10-30-h1-b114-test965-verdict.txt

`--takeover` is there because the record's `reviewer_owner` is cc (assigned by hover's least-loaded rule at b92; cc's b73 handoff C-1 says a builder cannot read the file). The record is the one with `opened_at` 2026-10-28T21:14:26Z, author_session hover, resource `sen_caregivers`, file `.claude/skills/sairn-hover-auditor/empirical-tests/test_965_sen_caregivers_phone_unredacted.py`. I have not run the command, so I do not know whether the gate accepts an author discharging its own record, even with `--takeover`; if it refuses, that refusal is the answer to whether Michael's "keep it with hover" can be recorded as a discharge or needs an amended record.

**Evidence behind the verdict (all driven at b114, all repeatable from the repo):**

| Run | Result |
|---|---|
| `test_965` on the tree at `f02a61f02^` (parent) | exit 0, CLAIM HOLDS: the leak existed |
| `test_965` on HEAD (`5ae8958d3`) | exit 1, KILLED: `session.role` is used for the roster scope |
| `test_965` on a scratch copy of HEAD with one token respelled, `SEN_CAREGIVER_ROSTER_ROLES[session['role']]`, no change in behaviour | exit 0, CLAIM HOLDS: a false pass about a fixed handler |
| gate promotion of H1-965 (log 1726) | 12:08:11Z against `13a006653`, 13 minutes BEFORE `f02a61f02`: valid when made |
| obligation opened | 21:14:26Z against `fe0127562`, which already contains `f02a61f02`: premise stale at opening |

**Limit, stated first in the verdict:** author and reviewer are the same role, so the verdict is a repeatable-runs account, not an independent second reading.
