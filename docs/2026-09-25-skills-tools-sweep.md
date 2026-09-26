# Skills and tools sweep — staleness, overlap, gaps

**2026-09-25 (CC).** Item 5 of the queue: sweep the shared skill store and
`tools/` for staleness, overlap and gaps. **Findings only — nothing fixed
blind**, which was the instruction and is also the right call: three of the
four candidate findings below dissolve on a second look, and two of those were
my own search method rather than the platform.

---

## 1. Staleness — the number is real, the alarm is mostly not

**`tools/`: 224 tools. 190 touched this month, 28 in August, 5 in July.**
47 have not been touched since 2026-09-10.

**MOST OF THAT 47 IS NOT STALENESS AND SAYING SO IS THE FINDING.** Reading the
list rather than the count: 20 of the 47 are `gen_*_calendar.py` /
`gen_*_seed.py` — per-state legal-deadline generators (MA, NJ, VA, MN, MO).
A generator for a jurisdiction's rules SHOULD be quiet; it changes when the
statute changes, not when the platform does. Calling those stale is the
wolf-crying this repo already records switching tools off.

**THE ONES WORTH A LOOK, and why each:**

| Tool | Last touched | Why it is worth a look |
|---|---|---|
| `gh_push.py`, `gh_verify.py` | 2026-07-26 | **Both are BROKEN today.** They read `GITHUB_TOKEN` from `C:\Users\marsh\Documents\SAIRN\.env.local`, which is **0 bytes** and has been since 2026-08-08. Every invocation raises `RuntimeError: GITHUB_TOKEN not found`. The working token is in the git credential manager. Two tools whose whole job is pushing, dead for seven weeks, and nothing said so. |
| `va_rule_currency.py` | 2026-08-25 | A **currency** checker is the one kind of tool whose own staleness is the defect — it exists to say whether a rule set is current. |
| `redaction_check.py` | 2026-07-27 | Oldest security-adjacent tool in the tree. Not evidence of rot; it is the one I would re-qualify first if a redaction requirement changed. |
| `missing_dom_target_check.py`, `div_balance_check.py` | 2026-08-07 | Both are HTML-shape checkers written before the platform learned (four times over) that a regex over a construct produces confident wrong answers. Worth re-reading against that lesson, not worth rewriting on spec. |

**Skill store: 62 entries, 58 with a `SKILL.md` older than 20 days, the oldest
58 days.** That number is almost entirely the **third-party** skills —
`ui-ux-pro-max`, `ponytail`, `frontend-design`, `claude-api`, `skill-creator`
and so on — which are vendored and do not change when SAIRN does. **Their
staleness is a supply-chain question for `skill-vetter`, not a maintenance
backlog**, and the distinction matters because mixing the two produces a
57-item to-do list nobody will ever start.

**mtime is also the wrong instrument here and the sweep says so rather than
quoting it**: the skill store is symlinked into the canonical store (all 34
SAIRN skills were migrated to symlinks on 2026-09-23), so an mtime reflects
when the link or the file was last written, not when the content was last
reasoned about. A content-hash comparison against the repo mirror is the honest
measure; `scripts/verify-skill-store.sh` already does it and reports CLEAN.

## 2. Overlap — three candidates, one real, and it is deliberate

Measured by shared vocabulary between the `PURPOSES` "catches" text of all 165
registered tools (>42% of the smaller vocabulary, ≥8 shared terms):

| Pair | Overlap | Verdict |
|---|---|---|
| `leg_session_gate_live_probe.py` / `scp_session_gate_live_probe.py` | 0.78 | **REAL, and deliberate.** Two live probes with the same shape against two different apps. The duplication is the point — a live probe must name its own app, licence and resource — but it is the pair to watch: a fix to one will not reach the other, which is the `strip_comments`-times-seven failure this platform has already paid for. **Recommendation: NOT a merge. A shared helper for the request/verdict half, keeping the per-app constants separate.** |
| `resource_reachability_check.py` / `tier_a_bypass_check.py` | 0.48 | **NOT overlap.** Shared words are generic (`before`, `cannot`, `check`, `names`, `number`). One asks whether a resource is ever asked for; the other whether a Tier A path can be reached without its gate. Different questions, similar prose. |
| `tier_a_review_gate.py` / `sairn_self_state.py` | 0.42 | **NOT overlap.** Both talk about obligations because one creates them and the other reports them. |

**So: 1 real overlap out of 224 tools.** That is a better result than I expected
and is worth recording as a measurement rather than a relief — the platform's
tool sprawl is broad but not redundant.

## 3. Gaps — none, and my first answer was wrong

I clustered the 292 defect-register records by class and asked whether any tool
declares each one. First pass reported two gaps, **both of which are my search
method failing, not the platform**:

* **fail-open** — reported "NO TOOL DECLARED". `tools/fail_open_check.py`
  exists, is registered, and I had run it earlier the same day. Its `PURPOSES`
  text simply does not contain the phrase "fail open".
* **prototype pollution** — reported "NO TOOL DECLARED".
  `tools/role_gate_invariants.js` is the platform-wide guard for exactly that
  (all 48 role maps given a null prototype on 2026-09-24).

**Corrected: every one of the 13 recurring classes has a declared tool** —
silent failure, comment-counted-as-code, regex-over-construct, window
heuristic, numeric coercion, fabricated KPI, race/TOCTOU, fail-open, prompt
injection, stale anchor, prototype pollution, rounding, third state.

**AND THE METHOD'S FAILURE IS THE MORE USEFUL FINDING.** A keyword search over
declared purposes cannot answer "is this class covered" — it answers "does
somebody's prose happen to use my word". That is the same class as the
`comment`-counted-as-code defect, one level up: I searched text about code
instead of the code. Anyone repeating this sweep should match on the tool's
own subject (its probe's mutations, its fixtures) rather than on its
description.

## 4. The one thing I would fix, and it is small

**`gh_push.py` and `gh_verify.py` should read the token from the git credential
manager, or say plainly that they are superseded.** Two push tools that raise
on every invocation are worse than absent: the next session to reach for one
loses the time it takes to discover why. Not fixed here — the push flow in use
does not depend on them, and changing a push tool deserves its own commit with
its own verification rather than a rider on a sweep.
