# SAIRN handoff -- cc batch b9 -- 2026-10-14

**Written by:** cc, in `Documents\SAIRN-cc`, on `main`.
**Written BEFORE the report**, at a point where nothing is half-finished: all
six items are settled (5 done, 1 blocked with a stated reason), every change
is committed and on `origin/main`, every tool touched has been re-run after
the final rebase, and no file is mid-edit.
**Companions:** `SAIRN-report-cc-b9.txt`, `SAIRN-digest-cc-b9.txt`,
`docs/batch-manifest-cc-b9.json` (6 items: 5 `done`, 1 `blocked`, each with
re-runnable evidence).
**Transcript:** this session's real transcript is
`C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\bb71ca91-ccbc-4a82-aa5e-0bff468b6ed5.jsonl`;
the scratchpad with raw logs is
`C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cc\bb71ca91-ccbc-4a82-aa5e-0bff468b6ed5\scratchpad\`
(`red_suite_real2.log` is the real ordinary run's output).

---

## Committed / pushed state

**HEAD `f0afdadc`, `git rev-list --left-right --count origin/main...HEAD` = `0 0`.**
No `--force` in any spelling. **`SAIRN_SEED_GATE` was never used.** Two
rebases during landing, the second hitting a real conflict in
`docs/defect-density-register.json` (concurrent appends from other sessions),
resolved by `tools/sairn_rebase_resolve.py`; the defect register was
re-seated onto the rewritten commit shas both times by the repo's own
post-rewrite hook.

| SHA | what |
|---|---|
| `ca131d98` | fix(status line) -- real per-model window (Sonnet 5 967K, Opus 1M), never a hardcoded 200K guess |
| `540e0b16` | fix(tools) -- batch_manifest.py cp1252 console crash + `--set`'s silent `cc`/`b6` default (caught LIVE, corrupted and reverted b6's manifest before this fix); sairn_claim.py commit subjects capped at 72 chars |
| `f9e56cfd` | fix(cody-routed) -- AST-confirms a self-test flag is real code, not a string/comment; ooda_phases.py's stale `<10` threshold now structural |
| `070efcd3` | fix(tools) -- encoding= on the 13 subprocess_decode_check findings in tools/ (56 more in tests/ routed to cody) |
| `29c8fc61` | fix(sql preflight) -- license_keys catalogue gap + function-called-as-table false positive |
| `2dc072c3` | fix(red suite register) -- an ordinary run can exit 0, not always 2 |
| `447307e9` | chore(b9) -- hooks record for the original clone, 3 FMEA drafts, batch manifest |
| `a4c1c2e7`, `3997a045`, `24dcc99d` | defect register entries (6 + 1), and the second fix the first one's own record exposed |
| `f0afdadc` | defect register re-seated after the second rebase |

**NO HOOK WAS ADDED OR RESTORED. `hooks` stays `{}` in every tracked
settings file in this repo.** `.claude/settings.json` was never committed
this batch (the original clone's hook-clearing edit is local and
uncommitted there, by design -- see item 2 below).

---

## The six items

| # | item | state | evidence |
|---|---|---|---|
| 1 | status line denominator from the real window | **DONE** | `tools/sairn_status_line.py` 26/26 fixtures; live render against this session's own transcript: `cc \| Sonnet 5 \| ctx 39% of 967k` |
| 2 | clear 3 hooks in the original SAIRN clone + pull --rebase into hank/cody/fourth where clean & no live claim | **BLOCKED, in two different ways** -- see below | `docs/SAIRN-hooks-record-original-clone.md` |
| 3 | batch_manifest.py --close encoding-safe; sairn_claim.py shorten claim commit subjects | **DONE, plus one more thing found along the way** | 32/32 fixtures; see item 3's own section below |
| 4 | cody tools sweep (4 items) | **DONE** | tests/, tools/, docs/ -- see below |
| 5 | red_suite_register_check.py exit code meaningful + 3 FMEA drafts | **DONE** | `--selftest` 10/10; real run exits 1 on 5 genuine findings, not always 2 |
| 6 | push without force, confirm landed | **DONE** | `0 0` against `origin/main`, HEAD `f0afdadc` |

---

## Item 2 -- blocked, and the two blocks are NOT the same shape

**(a) hank / cody / fourth: skipped by the rule itself, not by judgment call.**
The instruction was "only where the tree is clean and no live claim." All
three held an active claim for the entire batch -- checked at the start
(hank b9/b10, cody b10, fourth b16/b18) and **re-checked again immediately
before writing this handoff**: still active (hank b10, cody b10, fourth
b18). Per-rule, nothing was pulled into any of the three. No tree-cleanliness
check was even needed since the live-claim condition alone disqualifies all
three.

**(b) the original clone (`C:\Users\marsh\Documents\SAIRN`): the record and
the safe half are done; the pull itself was not attempted, and here is
exactly why.** Measured before touching anything:

- **HEAD `26db189`, `origin/main...HEAD` = `7810  1`** -- 7,810 commits
  behind, not a small recent divergence like hank/cody/fourth's.
- The clone's 1 local-only commit is **already content-equivalent** to an
  upstream commit (`6c1cb4d0`, same subject, already on `origin/main`) --
  checked by title match, not byte-diffed.
- **Two tracked files carry local uncommitted modifications**:
  `.claude/settings.json` (permissions only -- its `hooks` block was
  byte-identical to HEAD before I touched it) and `SAIRN-ACTIVE-WORK.md`.
- **An untracked, PEM/base64-shaped file sits in `.claude/`**:
  `MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQK.txt`, 218 bytes. Not opened, not read,
  not touched -- named so it is not lost.

**What I did:** copied the hooks block verbatim to
`docs/SAIRN-hooks-record-original-clone.md` FIRST, then cleared `hooks` to
`{}` in that clone's working copy of `.claude/settings.json` -- uncommitted,
matching the house rule and the state already live in the other four
folders. **What I did not do:** run `pull --rebase` there. A 7,810-commit
rebase with one unpushed commit, two dirty tracked files and an unexplained
secret-shaped file sitting beside the repo is a materially different
operation than "pull the hook removal," and I am not comfortable guessing
which way Michael wants that resolved -- see the digest's DECISION-NEEDED
line.

---

## Item 3 -- the thing found ALONG THE WAY, not asked for, fixed anyway

While setting manifest item 1's evidence, `batch_manifest.py --set 1 done
--evidence "..."` **silently wrote into `docs/batch-manifest-cc-b6.json`**
-- a CLOSED batch from an earlier session -- overwriting three of its
evidence fields with b9's text, no error, a confident `item 1 -> done`
printed over a manifest the command never named. Caught immediately via
`git status`/`git diff`, reverted with `git checkout -- docs/batch-manifest-cc-b6.json`
before anything was committed. Root cause: `--set` defaulted to
`--agent cc --batch b6` when neither flag was passed -- a hardcoded leftover
from the batch the file was written in. `--close` two lines below it already
refuses rather than guesses; `--set` now does the same. Re-ran the (correct,
qualified) `--set` calls afterward; b6 was confirmed untouched.

---

## Item 4 -- the cody tools sweep, each sub-item

1. **`SELFTEST_RX` matching `'--selftest'` as text (3 of 44).**
   `tests/run_selftest_sweep_probe.py`'s regex already required the full
   `'--selftest' in sys.argv` phrase (the 2026-09-24 fix), but a regex over
   source TEXT cannot tell real code from a string or comment that merely
   contains the same phrase. All three false positives were exactly that --
   a fixture string `first_article_inspection.py` writes to disk, a
   docstring example in `subprocess_decode_check.py`, a comment in
   `checker_selftest_check.py`. `discover()` now confirms each candidate
   against the AST (needs a real `ast.Compare`/`ast.In` node), which a
   string or comment can never produce. `--list` now finds 40 real
   self-tests with the three false ones gone.
2. **`TOLERATE_MISSING` wording.** Matched `'not recognized'`; argparse
   actually prints `'unrecognized arguments'`. Added, so a could-not-run
   from the class above lands in `could_not` instead of `fails`.
3. **`ooda_phases.py`'s stale `<10` threshold.** Asserted
   `injection_dated < 10`, true at the docstring's own 2026-09-15
   measurement (4 of 77). The register grew to 249 since. Assertion is now
   structural (a bounded record count: `0 <= injection_dated <= records`)
   instead of a magic number that goes stale as the register grows.
   `--selftest` now exits 0.
4. **`subprocess_decode_check.py`: 69 unencoded calls.** 13 in `tools/`
   (cc's), 56 in `tests/` (cody's). Fixed the 13 via the tool's own
   `--fix` path, scoped to only `tools/` paths. **Found a second, real
   defect while fixing the first**: `fix_file()` always spliced
   `, encoding='utf-8', errors='replace'` regardless of what a call already
   had. `tools/credential_purge_check.py` had `errors='replace'` with no
   `encoding=`; the fixer produced a **duplicate keyword argument** -- a
   real `SyntaxError` at `compile()` time that `ast.parse()` does not catch
   (verified: `ast.parse("f(x=1, x=1)")` raises nothing). The push gate's
   own stricter check caught the broken file before it reached
   `origin/main` -- fixed by hand, then fixed structurally (checks for a
   pre-existing `errors=` kwarg; the write guarantee now uses `compile()`).
   The 56 `tests/` sites are routed to cody in
   `docs/2026-10-14-cc-b9-subprocess-decode-tests-routed-to-cody.md`, by
   file:line.
5. **`license_keys` missing from the SQL preflight column catalogue.**
   `tools/sairn_sql_preflight.py` DECLARED mode blocked 4 already-shipped,
   correct seed files with false `MISSING_COLUMN` on every real
   `license_keys` column (the table predates this repo's tracked schema
   files, invisible to a catalogue built only from `CREATE TABLE` in
   `sql/*.sql`). Supplemented from `db/schema_snapshot.json`
   (`_generated_at` 2026-10-05), applied to DECLARED mode only. **Also
   fixed the other half of the same reported finding (#34)**:
   `sairn_circuit_breaker_step` -- a user-defined FUNCTION called in FROM
   position -- was reported `UNDECLARED_TABLE`; fixed structurally (an
   identifier immediately followed by `(` in relation position is a
   function call, never a table). `sql/*.sql` findings: 141 -> 20 (the
   remaining 20 are unrelated, pre-existing undeclared tables from other
   apps, out of scope here). `tests/sql_preflight/run_probe.py` still PASS,
   21/21.

---

## Item 5 -- the exit code, made meaningful, and verified on a real run

`red_suite_register_check.py`'s own docstring sells it as cheap enough to
run every batch WITHOUT `--from-run` -- but every such run unconditionally
added "no --from-run log" to `could_not_run`, and `could_not_run` always
wins over a clean result. So the one invocation it is actually FOR could
never report anything but exit 2, regardless of whether every registered
suite was confirmed still red. "No --from-run" is now a NOTICE: printed
every time, unmissably, but it no longer moves the exit code. A
`--from-run` log that WAS supplied and turned out truncated/unparsable is
unchanged and still forces exit 2. 10/10 selftest fixtures (two new cases
lock: no-log + all-red -> 0 WITH a notice; no-log + a RECOVERED suite ->
still 1). **Live-verified, not just fixture-verified**: a real ordinary run
(`scratchpad/red_suite_real2.log`) exits **1**, on **5 genuine RECOVERED
findings** (`api/sf-auth.test.js`, `tests/push_gate/check8_probe.py`,
`api/sd-data-cross-tenant-dispatchers.test.js`,
`tests/run_committer_identity_probe.py`,
`tests/run_selftest_independence_probe.py` -- the same 6 stale entries b8
routed to cody minus the one b8's own nhi fix already recovered). **An
orphaned worktree from a killed first attempt** (my own `timeout 300`
wrapper was shorter than the tool's own 420s per-suite ceiling) was found
and removed with `git worktree remove --force` before the clean re-run.

FMEA drafts saved (`fmea_draft.py --save`) for all three named tools:
`docs/fmea/tools_red_suite_register_check.py.json`,
`docs/fmea/tools_nhi_register.py.json`,
`docs/fmea/tools_sairn_status_line.py.json`.

---

## Claims held

**`cc`, claimed and pushed as the first action of this batch**, and **not
yet released** -- release it with `python tools/sairn_claim.py release cc`
once these three deliverables are uploaded. Status registry row set to
`working` at the start; set it to `idle` after release.

**Conflicts declared and NOT overridden (PR §4.3):** `tools/*` and
`tests/run_selftest_sweep_probe.py` were all inside cc's own declared FILES
or directly routed by cody; nothing of another session's live claim was
touched. `docs/defect-density-register.json` **was written**, the same
collision b8 already named and resolved the same way: the push gate
requires a record before accepting a defect-closing push, so it was
appended here rather than left to block the push, said out loud rather
than left to a diff.

**Files written that were NOT in cc's declared b9 FILES**, said out loud:
`docs/2026-10-14-cc-b9-subprocess-decode-tests-routed-to-cody.md` (new,
routing doc), `docs/defect-density-register.json` (7 new records, per the
collision above), this batch's three root deliverables, and
`tools/credential_purge_check.py` (one line, the hand-fix for the
duplicate-keyword bug `subprocess_decode_check.py`'s own fixer caused in
it -- not a file this batch set out to touch, but the fixer broke it and
the fixer is mine).

---

## Open, and whose -- with the exact next step

| item | owner | exact next step |
|---|---|---|
| **the original clone's `pull --rebase`** | **Michael** | the record and the safe half (hooks cleared, uncommitted) are done; see item 2 above and the digest's DECISION-NEEDED line for the exact question |
| **56 subprocess-decode sites in tests/** | **cody** | `python tools/subprocess_decode_check.py --fix` scoped to tests/ paths only, or by hand per `docs/2026-10-14-cc-b9-subprocess-decode-tests-routed-to-cody.md`; re-run `python tools/subprocess_decode_check.py` after, it refuses to write a file whose edit breaks the parse |
| **5 stale `known-red-suites.json` entries** | **cody**, already that file's holder | unchanged from b8: RECOVERED per the real run this batch did -- `api/sf-auth.test.js`, `tests/push_gate/check8_probe.py`, `api/sd-data-cross-tenant-dispatchers.test.js`, `tests/run_committer_identity_probe.py`, `tests/run_selftest_independence_probe.py` |
| **fmea_draft.py --save for batch_manifest.py and sairn_claim.py** | any session | the register's own FMEA-LOOP output suggested these two after this batch's records landed; not written here -- my own fixes being FMEA'd by me in the same batch is the detector-blesses-its-own-fix shape named in b8 |
| **the Tier A record `2026-10-12T01:51:33Z`** | whoever next holds `docs/tier-a-reviews.json` | unchanged since b8; this batch did not touch that file |

---

## Three things that will cost the next session time if nobody says them

1. **`ast.parse()` is not a parser-level safety net for everything a
   `compile()` catches.** `subprocess_decode_check.py`'s `fix_file()` said
   "NEVER WRITE A FILE THAT STOPPED PARSING" and checked `ast.parse()`
   only. A duplicate keyword argument passes `ast.parse()` clean and fails
   only at `compile()`. Any in-place source-rewriting tool in this repo
   that uses `ast.parse()` as its own write guarantee should be re-checked
   against `compile()` instead -- this was not swept beyond the one file
   that actually broke.
2. **A CLI flag that defaults a *destination* instead of requiring it is a
   silent-wrong-file bug waiting for the first unqualified call.**
   `batch_manifest.py --set`'s hardcoded `cc`/`b6` fallback corrupted a
   CLOSED batch's manifest live this batch, with a confident success line
   printed over it. `--close` already had the right shape two lines below;
   nothing checked that `--set` matched it until it didn't.
3. **A background shell `timeout` shorter than a tool's own documented
   per-item ceiling kills it mid-cleanup, not mid-nothing.**
   `red_suite_register_check.py` drives suites with a 420s-per-suite
   timeout and removes its worktree in a `finally`; my own `timeout 300`
   wrapper fired first, the `finally` never ran, and a worktree was left as
   litter. Match any external timeout to the tool's documented ceiling,
   not to a guess.
