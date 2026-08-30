# Claim-by-claim verification — CC's six skills

The gap named in `2026-08-30-skill-pack-vet-report.md` as *"the gap that matters
most before anything ships"*. Closed here: all six read line by line, every
factual claim extracted and machine-checked against the codebase.

**88 claims checked. 86 verified correct. 2 real errors, both fixed in place.**

---

## Per skill

| Skill | Claims | Verified | Real errors |
|---|---|---|---|
| `sairn-api-tester` | 13 | 12 | **1** — a commit SHA that does not exist |
| `sairn-differential-review` | 16 | 15 | **1** — line-ending example does not hold |
| `sairn-memory-curator` | 17 | 17 | none |
| `sairn-minimalism` | 16 | 16 | none |
| `sairn-perf-profiler` | 13 | 13 | none |
| `sairn-skill-vetter` | 13 | 13 | none |

## The two real errors

### 1. `sairn-api-tester` — a citation that cannot be checked

Rule 5 cited the mutation-check result as going red against **`a877978^`**.
**That SHA does not exist in this repository** — not as a commit, not in
`git log --all`.

The incident is entirely real. The commit is **`06ba0b8`**, *"fix(sairndental):
dnt_cred_rules write was owner-only in intent and any-role in fact"*
(2026-08-29), and its own message confirms every detail the rule states: provider
and front desk could write, `verified_by` was the literal string `'license'`.

**Why it matters more than a typo:** the pack's entire claim is that its rules
are checkable. A reader who tried to check this one would find nothing and have
no way to tell a wrong identifier from an invented incident.

Corrected in place, dated, with the wrong SHA still visible — per
`sairn-skill-author` rule 3.

### 2. `sairn-differential-review` — an example that does not hold in this clone

Rule 10 read: *"mixed line endings, file-by-file — `api/sd-data.js` is CRLF,
`sairncare.html` is LF."*

Measured: **both files are CRLF in the working tree and LF in the stored blob.**
The contrast does not exist here. `core.autocrlf=true`, and `.gitattributes` is
scoped to `docs/skill-backups/` and `scripts/*.sh` only.

**The advice is still right; the mechanism was wrong.** The hazard is the
autocrlf round trip — an editor that rewrites endings produces a whole-file diff
git then normalises away — not per-file divergence. Rewritten to say what was
measured.

## Ten check-bugs, one real error, and what that ratio means

Ten of my own verification checks failed against claims that turned out correct:

- `grep -oc` counts lines, not matches
- a quote wrapped across two `-- ` comment lines (×3, different files)
- flattening left `--` mid-sentence
- asserted a tool's output was on stdout line 1; it was line 3
- targeted the generator `sairn_build_load_gates.py` when the deleted artifact
  was its five generated `.sql` files
- searched for a constraint on `citation` when the column is `authority`
- `$HOME` expanded to a Git Bash path Python cannot open
- asserted a file was absent that had been **renamed**
  (`seed_load_gate_hook.py` → `sairn_push_gate_hook.py`, commit `4cada6a`)

**Roughly ten check-bugs per real finding.** Recorded because it is the strongest
evidence for `sairn-context-budget`'s own thesis, arriving from an unexpected
direction: **a verifier that produces false failures trains you to dismiss real
ones.** Every one of these had to be individually disproved, and the two real
errors were only distinguishable *because* each failure was chased rather than
waved through.

The flattening verifier (`scratchpad/verify_specs.py`) handles the comment and
wrap cases. Ad-hoc shell greps do not, and most of these were ad-hoc shell greps.

## Two things found that are not skill defects

**`C:/SAIRN/tools/seed_load_gate_hook.py` is orphaned — mine, and I should say
so.** Commit `4cada6a` renamed the repo's copy to `sairn_push_gate_hook.py`
(11,129 bytes) and expanded it. Earlier tonight I installed the *old* name
(9,218 bytes) to unblock a broken hook path. It is referenced by **no settings
file**. Dead weight I created. Flagged rather than deleted — deletion authority
in that shared directory is not mine.

**`sairn-differential-review` still lacks the `allowed-tools` its third-party
original declared** (`Read Write Grep Glob Bash`). Unchanged from the first vet
report; listed again because it is a safety regression, not a content one.

---

## Revised verdict

    ADMIT                 internal use — unchanged
    ADMIT WITH CHANGES    shipping — the content gate is now CLOSED

**What this closes:** every rule in all nine is now traceable to a real,
identifiable incident. That was the pack's central promise and it now holds,
with two corrections on the record.

**What still stands between here and sale-ready** — all mechanical, none
requiring research:

1. `allowed-tools` on CC's six, including the one `sairn-differential-review`
   dropped.
2. Honest-scope sections on `sairn-differential-review`, `sairn-memory-curator`,
   `sairn-minimalism`.
3. Precedence declared on `sairn-api-tester` and `sairn-skill-vetter`.
4. Licence-key and personal-name redaction in the distribution build — packaging,
   not content (see the first vet report, finding 4).

**Not checked, and stated because the first report's own rule requires it:** I
verified factual claims and structural gates. I did not attempt to judge whether
each skill's *advice* is good — only whether what it asserts is true.
