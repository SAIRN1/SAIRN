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


def run(*a, **k):
    return subprocess.run(list(a), cwd=REPO, capture_output=True, text=True, **k)


def clean_tree():
    return run('git', 'status', '--porcelain').stdout.strip()


dirty = [l for l in clean_tree().split('\n') if l.strip() and not l.startswith('??')]
assert not dirty, 'probe needs a clean tracked tree, got:\n' + '\n'.join(dirty)
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
finally:
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

check('the repo was restored', open(path, encoding='utf-8').read() == original)
check('...and HEAD is back where it started',
      run('git', 'rev-parse', 'HEAD').stdout.strip() == start)

print('\n%s  check7_probe: %d checks, %d failed'
      % ('FAILED' if fails else 'ok', 7, len(fails)))
sys.exit(1 if fails else 0)
