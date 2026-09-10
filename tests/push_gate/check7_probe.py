"""Live-verify push-gate check 7 the way checks 1-4 were: a planted violation
must BLOCK, a clean push must be ALLOWED, and each arm asserts on the refusal
REASON rather than the exit code alone.

CHECK 7 blocks a push that ships an api/ endpoint answering a refusal ABOVE the
first auth call. It went in blocking on 2026-09-08, immediately after the
fifteen *-auth.js handlers were reordered and tools/preauth_oracle_check.py
started exiting 0 for the first time.

THIS PROBE IS THE POINT OF THAT SENTENCE. A gate whose findings are clean has,
by construction, never denied anything -- so nobody knows whether it CAN. The
same standard tools/discarded_verdict_check.py was held to.

Driven from Python so nothing depends on Bash command text. Restores the repo
in a `finally`, and asserts the tree is clean before it starts.
"""
import os
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
EP = 'api/sb-auth.js'


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


dirty = [l for l in clean_tree().split('\n') if l.strip() and not l.startswith('??')]
# ── A PRECONDITION IS NOT A FAILURE (2026-09-08) ──────────────────────────
# Same change and same reason as check4_probe.py. The guard stays: this probe
# commits planted fixtures and `git reset --mixed` back, so a dirty TRACKED
# tree would put somebody's work into a probe commit. But exiting 1 said
# "check 7 is broken" when nothing about check 7 had been examined. Exit 3 is
# SKIPPED, which tools/run_all_tests.py reports separately and never counts
# as a pass.
if dirty:
    print('SKIPPED: this probe commits fixtures and resets, so it needs a clean')
    print('tracked tree -- running it now would sweep uncommitted work into a')
    print('probe commit. Nothing about check 7 was verified. Modified:')
    print('\n'.join(dirty))
    sys.exit(3)
start = run('git', 'rev-parse', 'HEAD').stdout.strip()
R = {}


def dry_push():
    r = run('git', 'push', '--dry-run', 'origin', 'HEAD:main')
    err = (r.stderr or '') + (r.stdout or '')
    return {
        'exit': r.returncode,
        # MATCHED ON A FRAGMENT THAT SURVIVES THE LINE WRAP. The first version
        # looked for 'BEFORE the caller is authenticated' and the deny message
        # breaks between 'the' and 'caller', so the arm reported NOT BLOCKED
        # against a push the gate had correctly refused -- exit 1, file named,
        # and the one assertion that mattered red for the wrong reason.
        'blocked_by_preauth': 'answer a refusal BEFORE the' in err,
        'names_the_file': EP in err,
        'unchecked': 'UNCHECKED for pre-auth disclosures' in err,
        'blocked_undeclared': 'NO authentication' in err and 'no declaration' in err,
        'rejected_by_remote': 'fetch first' in err or 'rejected' in err,
    }


path = os.path.join(REPO, EP)
original = open(path, encoding='utf-8').read()

try:
    # ── ARM 1: a CLEAN change to the same endpoint must be allowed ──────────
    # Not a change to an unrelated file: the arm has to prove the check let a
    # touched endpoint through, or it proves only that the scope filter works.
    open(path, 'w', encoding='utf-8', newline='').write(
        original.replace('module.exports = async (req, res) => {',
                         '// probe: a comment, and nothing else\nmodule.exports = async (req, res) => {', 1))
    run('git', 'add', EP)
    run('git', 'commit', '-q', '-m', 'PROBE clean endpoint change')
    R['clean_change'] = dry_push()
    run('git', 'reset', '--mixed', start)
    run('git', 'checkout', '--', EP)

    # ── ARM 2: the REORDER PUT BACK must block ─────────────────────────────
    # The exact defect, not an invented one: move the envelope gate back above
    # validateLicenseKey, which is what all fifteen looked like before
    # 2026-09-08.
    body_at = original.index('  let body = req.body;')
    body_end = original.index('\n  }\n', original.index('.indexOf(action)', body_at)) + len('\n  }\n')
    block = original[body_at:body_end]
    reverted = original[:body_at] + original[body_end:]
    lic_at = reverted.index('  let lic;\n  try {')
    reverted = reverted[:lic_at] + block + '\n' + reverted[lic_at:]
    assert 'let body = req.body;' in reverted and reverted != original, 'fixture invalid'
    open(path, 'w', encoding='utf-8', newline='').write(reverted)
    run('git', 'add', EP)
    run('git', 'commit', '-q', '-m', 'PROBE pre-auth disclosure')
    R['planted_disclosure'] = dry_push()
    run('git', 'reset', '--mixed', start)
    run('git', 'checkout', '--', EP)
    # ── ARM 3: a NEW endpoint with no auth boundary must block ─────────────
    # The api/claude.js shape: an endpoint that authenticates nothing, added
    # with nothing to notice it. It is not wrong on its own -- 25 are public on
    # purpose -- but it must be DECLARED, and this arm is the only thing that
    # proves an undeclared one cannot slip in.
    newep = os.path.join(REPO, 'api', 'zz_probe_public.js')
    _src = [
        '// probe: an endpoint that authenticates nothing and declares nothing.',
        'module.exports = async (req, res) => {',
        "  if (req.method !== 'POST') { res.status(405).json({ error: { message: 'POST only' } }); return; }",
        '  res.status(200).json({ ok: true });',
        '};',
    ]
    open(newep, 'w', encoding='utf-8', newline='').write(chr(10).join(_src) + chr(10))
    run('git', 'add', 'api/zz_probe_public.js')
    run('git', 'commit', '-q', '-m', 'PROBE undeclared public endpoint')
    R['undeclared_endpoint'] = dry_push()
    run('git', 'reset', '--mixed', start)
    if os.path.exists(newep):
        os.remove(newep)

finally:
    _stray = os.path.join(REPO, 'api', 'zz_probe_public.js')
    if os.path.exists(_stray):
        os.remove(_stray)
    open(path, 'w', encoding='utf-8', newline='').write(original)
    run('git', 'reset', '--mixed', start)
    run('git', 'checkout', '--', EP)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


print('push-gate check 7 -- a pre-auth disclosure must not reach origin\n')

a = R['clean_change']
check('a clean change to a touched endpoint is NOT blocked by check 7',
      not a['blocked_by_preauth'], str(a))
check('...and check 7 did not silently fail open on it',
      not a['unchecked'], str(a))

b = R['planted_disclosure']
check('the reorder put back IS blocked', b['blocked_by_preauth'], str(b))
check('...and the refusal names the file', b['names_the_file'], str(b))
check('...and the push exits non-zero', b['exit'] != 0, str(b))

c = R['undeclared_endpoint']
check('a NEW endpoint with no auth boundary and no declaration IS blocked',
      c['blocked_undeclared'], str(c))
check('...and that push exits non-zero', c['exit'] != 0, str(c))

check('the repo was restored', open(path, encoding='utf-8').read() == original)
check('...and the probe endpoint was removed',
      not os.path.exists(os.path.join(REPO, 'api', 'zz_probe_public.js')))
check('...and HEAD is back where it started',
      run('git', 'rev-parse', 'HEAD').stdout.strip() == start)

print('\n%s  check7_probe: %d checks, %d failed'
      % ('FAILED' if fails else 'ok', 10, len(fails)))
sys.exit(1 if fails else 0)
