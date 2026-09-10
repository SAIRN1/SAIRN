"""Live-verify push-gate check 4 the same way checks 1-3 were verified:
a planted violation must BLOCK, a clean push must be ALLOWED.

Driven from Python so nothing depends on Bash command text, and every arm
asserts on the refusal REASON, not just the exit code -- three of tonight's
probe arms returned the right code for the wrong reason.
"""
import subprocess, os, sys, re

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
EP = 'api/legal-deadlines.js'


# ── THIS PROBE DECLARES ITSELF TO PUSH-GATE CHECK 8 (2026-09-10) ──────────
# Check 8 refuses a push carrying a commit whose subject starts with PROBE,
# because one of this file's own fixtures reached origin/main and shipped to
# production on 2026-09-09. This probe's pushes are `--dry-run` and publish
# nothing, so they are exempt -- but git hands a pre-push hook NO signal that a
# push is a dry run, so the exemption has to be declared rather than detected.
#
# It suppresses CHECK 8 ONLY. It is set here, in the probe that plants the
# fixture, and nowhere else. A real push that sets it is defeating a gate it had
# to go out of its way to defeat.
PROBE_ENV = dict(os.environ, SAIRN_PROBE_PUSH='1')


def run(*a, **k):
    return subprocess.run(list(a), cwd=REPO, capture_output=True, text=True,
                          env=PROBE_ENV, **k)


def clean_tree():
    return run('git', 'status', '--porcelain').stdout.strip()


# ── A PRECONDITION IS NOT A FAILURE (2026-09-08) ──────────────────────────
# This was `assert clean_tree() == ''`, which exits 1 -- indistinguishable
# from "check 4 is broken". It is neither. This probe COMMITS planted
# fixtures and then `git reset --mixed` back, so running it against a dirty
# tree would sweep somebody's uncommitted work into a probe commit and then
# unstage it. The guard protects real work and must stay.
#
# What was wrong is the SIGNAL. On 2026-09-08 an unrelated probe left one
# tracked file byte-modified and this exited 1, which read as a failing
# push-gate check and sent a reader looking at check 4. Exit 3 now means
# SKIPPED -- tools/run_all_tests.py lists it under SKIPPED with this reason
# and never counts it as a pass, because "could not run" is not "ran clean".
#
# ── AND AN UNTRACKED FILE IS NOT DIRT (2026-09-09) ────────────────────────
# This compared the WHOLE porcelain output, so a single untracked file skipped
# it -- and one has been sitting in a clone since 2026-08-28, which means this
# probe had been reporting SKIPPED on every run in that clone and verifying
# nothing about a BLOCKING gate. Its sibling check7_probe.py already filters
# `??` for exactly this reason; the two guards were written to the same
# intention and only one of them implemented it.
#
# It is safe: the danger this guard exists for is `git add` sweeping somebody's
# uncommitted work into a probe commit, and this probe adds NAMED PATHS. An
# untracked file elsewhere cannot be swept by that, and `git reset --mixed`
# does not touch it either.
dirty = [l for l in clean_tree().split('\n') if l.strip() and not l.startswith('??')]
if dirty:
    print('SKIPPED: this probe commits fixtures and resets, so it needs a clean')
    print('tree -- running it now would sweep uncommitted work into a probe')
    print('commit. Nothing about check 4 was verified. Modified:')
    print('\n'.join(dirty))
    sys.exit(3)
start = run('git', 'rev-parse', 'HEAD').stdout.strip()
# The untracked files that were here BEFORE this probe ran. The restore check at
# the bottom compares against this rather than against an empty tree.
START_UNTRACKED = {l for l in clean_tree().split('\n') if l.startswith('??')}
R = {}


def dry_push():
    r = run('git', 'push', '--dry-run', 'origin', 'HEAD:main')
    err = r.stderr or ''
    return {
        'exit': r.returncode,
        'blocked_by_seam': 'does not forward every input its engine reads' in err,
        'blocked_by_sql': 'no live schema snapshot' in err,
        'rejected_by_remote': 'fetch first' in err or 'rejected' in err,
        'names_field': 'service_methods' in err,
    }


# ---- ARM 1: CLEAN api change must be allowed by check 4 ----
p = os.path.join(REPO, 'api', '_lib', 'zz_probe_clean.js')
open(p, 'w').write('// probe: a new lib nothing calls\nmodule.exports = {};\n')
run('git', 'add', 'api/_lib/zz_probe_clean.js')
run('git', 'commit', '-q', '-m', 'PROBE clean api change')
R['clean_api_change'] = dry_push()
run('git', 'reset', '--mixed', start)
os.remove(p)

# ---- ARM 2: PLANTED seam violation must block ----
path = os.path.join(REPO, EP)
src = open(path, encoding='utf-8').read()
# ── EXACTLY ONCE, NOT MERELY PRESENT (2026-09-10) ─────────────────────────
# `assert patched != src` catches an anchor that has DISAPPEARED and says
# nothing about one that now matches SEVERAL places -- re.sub(count=1) would
# quietly mutate whichever came first, and the arm would then be asserting
# something about a line nobody chose. That is not hypothetical: arm 15 of
# tests/sairndental_outbound_queue_probe.py went ambiguous the day a second
# SAIRNdental write branch landed with an identical header, and it only
# survived as a real guard because it counted.
#
# An anchor is a string match against code somebody else keeps editing, so
# going ambiguous is how it AGES rather than an accident.
#
# COUNTED WITHOUT THE SURROUNDING NEWLINES, and the first version of this line
# was vacuous for the one case that matters most. `\n...\n` cannot match two
# ADJACENT copies: the trailing newline of the first is the leading newline of
# the second, and re.findall does not return overlapping matches, so two
# identical lines in a row counted as ONE. A control that duplicated the line
# caught it -- the assertion was already the shape it exists to forbid.
_hits = len(re.findall(r'^\s*service_methods\s*:[^\n]*$', src, re.M))
assert _hits == 1, ('fixture invalid: the anchor matches %d places in %s, not 1 -- '
                    'widen it until it is unique rather than letting re.sub pick'
                    % (_hits, EP))
patched = re.sub(r'\n\s*service_methods\s*:[^\n]*\n', '\n', src, count=1)
assert patched != src, 'fixture invalid'
open(path, 'w', encoding='utf-8').write(patched)
run('git', 'add', EP)
run('git', 'commit', '-q', '-m', 'PROBE seam violation')
R['planted_violation'] = dry_push()
run('git', 'reset', '--mixed', start)
run('git', 'checkout', '--', EP)

# ── RESTORED MEANS "THIS PROBE LEFT NOTHING", NOT "THE TREE IS EMPTY" ──────
# Same defect as the guard at the top and found in the same run: this was
# `clean_tree() == ''`, so a pre-existing untracked file made the probe report
# NOT RESTORED and exit 1 -- a false failure about the probe's own cleanup,
# which is the loudest possible way to be wrong about residue in a repo that
# has spent a session learning to read residue correctly.
#
# What actually matters is that nothing THIS PROBE created or modified is still
# there. So: no modified tracked files, and the untracked set is exactly what it
# was before the probe started. That still catches a stranded fixture -- the
# thing the check exists for -- and stops blaming this probe for a file it never
# touched.
_after_untracked = {l for l in clean_tree().split('\n') if l.startswith('??')}
_after_tracked = [l for l in clean_tree().split('\n')
                  if l.strip() and not l.startswith('??')]
R['restored'] = (not _after_tracked and _after_untracked == START_UNTRACKED)
R['head_restored'] = (run('git', 'rev-parse', 'HEAD').stdout.strip() == start)

for k, v in R.items():
    print('%-20s %s' % (k, v))
print()
ok = (R['planted_violation']['blocked_by_seam'] and R['planted_violation']['names_field']
      and not R['clean_api_change']['blocked_by_seam']
      and R['restored'] and R['head_restored'])
print('CHECK 4 VERIFIED (planted blocks by seam + names the field, clean not blocked by seam):', ok)
sys.exit(0 if ok else 1)
