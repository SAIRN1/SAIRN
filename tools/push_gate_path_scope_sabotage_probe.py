#!/usr/bin/env python
# OWNER: cc
# written 2026-10-20, batch b27, item 1
"""Sabotage-test pre-push CHECK 5d (gate `path-scope`) in a scratch worktree.

    python tools/push_gate_path_scope_sabotage_probe.py            # run it
    python tools/push_gate_path_scope_sabotage_probe.py --selftest  # criteria

One out-of-scope path per build population, plus one auditor path, each planted,
committed and driven through the REAL pre-push hook in a clone provisioned as
that population. Every refusal must NAME the planted path and NAME the deciding
rule.

── WHY THIS IS A FILE AND NOT A SCRATCH SCRIPT ──────────────────────────────
It was a scratch script. cc's b26 ran it from the session scratchpad, and the
twelve FMEA drafts generated in the same batch were lost by a worktree cleanup
in that same directory. A control nobody can re-run is a control whose result
has to be believed.

── WHAT IT IS NOT ───────────────────────────────────────────────────────────
It does not test that `tools/sairn_path_manifest.py` classifies correctly --
that tool's own `--fixtures` does, 39/39, and classification is not refusal.
This asserts the composition: that the HOOK refuses the PUSH, in-clone, before
anything leaves, with the planted path named.

── THE PLANT IS SETUP, NOT THE TEST, AND THAT DISTINCTION IS THE WHOLE BUG ──
b26's first run reported hank **ALLOWED**. The pre-COMMIT hook had refused the
plant (`tools/*.py` with no inventory entry), the commit never happened, and the
pre-PUSH hook was then driven over a clean tree and its exit 0 read as a result.

Two changes, because either alone is thin:

  1. The plant commits with `--no-verify`. The subject under test is the
     PRE-PUSH hook. Letting a different hook adjudicate the setup means the
     probe's coverage depends on rules it is not testing.
  2. `sabotage.verdict()` requires the planted path to be inside the OUTGOING
     RANGE -- what the pre-push hook will actually be handed -- before any
     verdict is returned. Absent that it is INCONCLUSIVE, and
     `sabotage.tally()` keeps an INCONCLUSIVE row out of both buckets, so
     "4 of 5" cannot be written over four refusals and one untested case.

`--no-verify` is deliberately NOT applied to the push: the push is the thing
being measured.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage import INCONCLUSIVE, tally, verdict          # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (population, planted path, the rule the refusal must name)
CASES = [
    ('hank',   'tools/zz_pathscope_probe.py',              'FOREIGN'),
    ('cc',     'api/zz_pathscope_probe.js',                'FOREIGN'),
    ('cody',   'stonedesk_zz_pathscope_probe.html',        'FOREIGN'),
    ('fourth', 'tests/zz_pathscope_probe.js',              'FOREIGN'),
    ('cc',     '.claude/skills/sairn-hover-auditor/tools/zz_pathscope.py',
     'AUDITOR'),
]


def run(args, cwd, stdin=''):
    # TWO SHAPES HERE ARE SCRUTINY-FLAGGED AS WEAKENING AND BOTH ARE
    # DELIBERATE, so the reason sits next to them rather than in a commit
    # message nobody re-reads.
    #
    # `timeout=600`: the subject is a FULL PRE-PUSH RUN, fifteen-plus checks
    # over a scratch worktree, five times. A shorter bound would turn a slow
    # gate into a probe failure and the two must not look alike. A timeout
    # raises here, which aborts the whole probe loudly -- it is never read as
    # an ALLOWED.
    return subprocess.run(args, cwd=cwd, input=stdin, capture_output=True,
                          text=True, encoding='utf-8', errors='replace',
                          timeout=600,
                          env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                   PYTHONUTF8='1'))


def _drive(wt, pop, path, want):
    """Provision, plant, prove the plant is in the outgoing range, drive the
    hook. Returns (got, detail)."""
    r = run([sys.executable, 'tools/sairn_session_identity.py',
             '--provision', pop, '--force'], wt)
    if r.returncode != 0:
        return INCONCLUSIVE, ('could not provision the clone as %r, so no '
                              'population was under test: %s'
                              % (pop, (r.stdout + r.stderr).strip()[-200:]))

    full = os.path.join(wt, path.replace('/', os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with io.open(full, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('// path-scope sabotage probe -- never pushed\n')
    run(['git', 'add', '-f', path], wt)
    c = run(['git', '-c', 'user.name=probe', '-c', 'user.email=p@local',
             'commit', '-q', '--no-verify', '-m',
             'probe(path-scope): %s plants %s' % (pop, path)], wt)

    shipped = run(['git', 'diff', '--name-only', 'origin/main...HEAD'], wt)
    outgoing = shipped.stdout or ''

    h = run([sys.executable, 'tools/sairn_push_gate_hook.py', '--pre-push'],
            wt, stdin='')
    out = (h.stdout or '') + (h.stderr or '')
    observed = 'REFUSED' if h.returncode != 0 else 'ALLOWED'

    # THE RAN-CHECK. The plant must be in what the hook was handed, or the
    # exit code above is a statement about some other tree.
    got, why = verdict(observed, path, outgoing,
                       label='the outgoing range origin/main...HEAD')
    if got == INCONCLUSIVE:
        return got, why + '\n  commit exit %d: %s' % (
            c.returncode,
            ((c.stdout or '') + (c.stderr or '')).strip()[-160:] or 'no output')

    if got != 'REFUSED':
        return got, 'the hook exited 0 over a range that DID contain the plant'
    missing = [lbl for lbl, s in (('the planted path', path),
                                  ('the rule %s' % want, want))
               if s not in out]
    if missing:
        return 'REFUSED-UNNAMED', ('refused, but the refusal does not name '
                                   + ' or '.join(missing))
    return got, 'refusal names the path and names %s' % want


def main():
    base = tempfile.mkdtemp(prefix='pathscope-sabotage-')
    wt = os.path.join(base, 'wt')
    add = run(['git', 'worktree', 'add', '--detach', wt, 'HEAD'], REPO)
    if add.returncode != 0:
        print('COULD NOT RUN: no scratch worktree, so nothing was tested.')
        print((add.stdout + add.stderr).strip()[-500:])
        return 2
    try:
        rows = []
        for pop, path, want in CASES:
            got, detail = _drive(wt, pop, path, want)
            rows.append(('%s:%s' % (pop, path), got, 'REFUSED'))
            print('  %-7s %-7s %-55s want %-7s -> %s'
                  % ('ok' if got == 'REFUSED' else
                     '??' if got == INCONCLUSIVE else 'FAIL',
                     pop, path, want, got))
            for ln in detail.splitlines():
                print('          ' + ln)
            run(['git', 'reset', '-q', '--hard', 'origin/main'], wt)
            run(['git', 'clean', '-qfd'], wt)
    finally:
        # Never from inside, and never with the main repo as cwd for a clean:
        # b26 lost untracked work to exactly that sequence.
        run(['git', 'worktree', 'remove', '--force', wt], REPO)
        run(['git', 'worktree', 'prune'], REPO)
        # `ignore_errors=True` is the second flagged shape. It is swallowing a
        # failure to DELETE A SYSTEM TEMP DIRECTORY -- outside the repo,
        # containing nothing but this probe's own scratch worktree. The cost of
        # a swallowed failure here is leftover temp bytes; the cost of raising
        # is that a cleanup error replaces the verdict table the probe exists
        # to print. b26's loss ran the OTHER way -- a removal that reached work
        # it should not have -- which is why the two `git worktree` calls above
        # name an explicit path and run with REPO as cwd, never from inside.
        shutil.rmtree(base, ignore_errors=True)

    code, lines = tally(rows)
    print('')
    print('PRE-PUSH CHECK 5d (gate path-scope) -- sabotage, scratch worktree')
    for ln in lines:
        print(ln)
    return code


def _selftest():
    """Lock the criteria against fixtures before trusting the live run."""
    ok = True

    def check(name, cond, detail=''):
        nonlocal ok
        print(('  ok   ' if cond else '  FAIL ') + name
              + ('' if cond else '  ' + str(detail)))
        if not cond:
            ok = False

    print('1. the ran-check decides, not the exit code')
    check('an exit-0 hook over a range CONTAINING the plant is a real ALLOWED '
          '(and therefore a FAIL of the gate)',
          verdict('ALLOWED', 'api/x.js', 'api/x.js\n')[0] == 'ALLOWED')
    check('THE b26 SHAPE: exit 0 over an EMPTY range is INCONCLUSIVE',
          verdict('ALLOWED', 'api/x.js', '')[0] == INCONCLUSIVE)
    check('an exit-0 hook over a range of OTHER files is INCONCLUSIVE too',
          verdict('ALLOWED', 'api/x.js', 'docs/y.md\n')[0] == INCONCLUSIVE)

    print('\n2. the tally cannot be quoted past an untested case')
    check('four refusals and one inconclusive is exit 2, not 0',
          tally([('a', 'REFUSED', 'REFUSED')] * 4
                + [('e', INCONCLUSIVE, 'REFUSED')])[0] == 2)
    check('...and REFUSED-UNNAMED is a FAIL, not a pass -- a refusal that '
          'does not name the path is not reviewable',
          tally([('a', 'REFUSED-UNNAMED', 'REFUSED')])[0] == 1)
    check('all five refused is the only exit 0',
          tally([('x%d' % i, 'REFUSED', 'REFUSED') for i in range(5)])[0] == 0)

    print('\n3. the case table is five and covers all four populations '
          'plus the auditor')
    check('five cases', len(CASES) == 5, len(CASES))
    check('all four build populations appear',
          {c[0] for c in CASES} >= {'hank', 'cc', 'cody', 'fourth'})
    check('exactly one AUDITOR case, and it is driven as a build agent so '
          'the auditor rule is what refuses it rather than the owner rule',
          [c[2] for c in CASES].count('AUDITOR') == 1
          and [c[0] for c in CASES if c[2] == 'AUDITOR'] == ['cc'])
    check('hank is planted a tools/ path -- the b26 case, kept rather than '
          'swapped for a .txt, because --no-verify is the real fix',
          ('hank', 'tools/zz_pathscope_probe.py', 'FOREIGN') in CASES)

    print('')
    print('  all arms pass' if ok else '  ARMS FAILED')
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(_selftest() if '--selftest' in sys.argv[1:] else main())
