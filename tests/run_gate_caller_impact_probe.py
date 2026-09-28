"""Control pair for tools/gate_caller_impact.py.

Run:  python tests/run_gate_caller_impact_probe.py

CONTROLS_FOR = ['tools/gate_caller_impact.py']

BOTH DIRECTIONS, on REAL files:

  plant a caller that sends a gated action with a licence key and no session
      -> the tool must NAME it and exit 1
  name that same caller as deliberately unauthenticated
      -> the tool must go quiet and exit 0
  remove the caller
      -> back to the baseline verdict, exactly

── WHY THE SECOND AND THIRD DIRECTIONS MATTER AS MUCH AS THE FIRST ─────────
A checker that reports every caller passes direction one and is useless. A
checker whose `--expect-unauthenticated` silently swallows anything passes
direction two and is worse than useless -- it is a place to hide a caller that
really will break. So the accounting is tested as a NAMED exemption: the planted
file is exempted BY PATH, and a DIFFERENT path must not silence it.

── THE FIXTURE IS SYNTHETIC AND SAYS SO ───────────────────────────────────
The real near-miss -- tools/load_deadline_seed.py sending a bearer key alone
against add_rule -- was fixed in the same change that motivated this tool, so it
cannot be restored from the tree. It IS recoverable from git history, and a later
version of this probe should use it; today the planted caller is a temporary file
written into tools/ and removed. That is weaker evidence than a real defect and
is labelled rather than implied.
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'gate_caller_impact.py')
PLANTED = os.path.join(REPO, 'tools', '_zz_planted_gate_caller_probe.py')
PLANTED_REL = 'tools/_zz_planted_gate_caller_probe.py'
OTHER_REL = 'tools/_zz_some_other_file_entirely.py'

# ── LIVE-PROBE CLASS, DECLARED (2026-09-28) ─────────────────────────────────
# FIXTURE. This file contains a bearer-key `add_rule` caller as a STRING, because
# planting one is how it proves tools/gate_caller_impact.py reports it. It makes
# NO live request of its own -- the only network-shaped code here is inside the
# FIXTURE literal, which is written to disk and deleted again. Declared so
# tools/live_probe_residue_audit.py stops asking; the same self-reference that
# made gate_caller_impact.py flag its own control.
LIVE_PROBE_CLASS = 'FIXTURE'

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2
passed = failed = 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:400])


def run(*extra):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.run([sys.executable, TOOL, '--endpoint', 'legal-deadlines',
                        '--action', 'add_rule'] + list(extra),
                       cwd=REPO, env=env, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


# The planted caller: a licence key, the gated action, and NO session header.
# `git ls-files` is the tool's universe, so the file has to be ADDED to the
# index -- a file on disk that git does not track is invisible to it, which is a
# property worth knowing and is asserted below.
FIXTURE = '''"""A planted caller for tests/run_gate_caller_impact_probe.py. Temporary."""
import json, urllib.request
ENDPOINT = "https://sairn.vercel.app/api/legal-deadlines"
def go(key):
    body = json.dumps({"action": "add_rule", "rule": {}}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key})
    return urllib.request.urlopen(req)
'''


def git(*args):
    return subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')


if not os.path.isfile(TOOL):
    print('COULD NOT RUN: tools/gate_caller_impact.py is not on disk. This '
          'control tested nothing, which is a third state and not a pass.')
    sys.exit(EXIT_COULD_NOT_RUN)

print('CONTROL PAIR -- tools/gate_caller_impact.py\n')

print('BASELINE -- the shipped tree')
base_rc, base_out = run()
ok(base_rc == EXIT_CLEAN,
   'with every caller accounted for, the tool exits 0 (got %d)' % base_rc,
   base_out[-400:])
ok('load_deadline_seed.py' in base_out and 'SESSION' in base_out,
   'and it still SEES the real caller -- a tool that found nothing would also '
   'exit 0, which is the always-passing checker this repo has measured',
   base_out[-400:])
ok('CHECKED / UNIVERSE' in base_out,
   'and it prints checked/universe, so a silently narrowed scan is visible')

if os.path.exists(PLANTED):
    os.remove(PLANTED)

try:
    print('\nDIRECTION 1 -- plant an unaccounted caller (SYNTHETIC fixture)')
    with io.open(PLANTED, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(FIXTURE)
    # UNTRACKED FIRST, and this is a real property rather than a setup step.
    rc_untracked, out_untracked = run()
    ok(rc_untracked == EXIT_CLEAN and PLANTED_REL not in out_untracked,
       'an UNTRACKED caller is invisible to the tool -- its universe is '
       '`git ls-files`, so a file nobody committed is not a caller yet. Worth '
       'knowing rather than discovering.',
       'rc=%d' % rc_untracked)

    add = git('add', '-N', PLANTED_REL)
    ok(add.returncode == 0, 'the fixture can be added to the index',
       add.stderr[:200])

    rc1, out1 = run()
    ok(rc1 == EXIT_FINDING,
       'THE ARM THAT MATTERS: a tracked caller sending add_rule with a licence '
       'key and no session makes the tool exit 1 (got %d)' % rc1,
       out1[-500:])
    ok(PLANTED_REL in out1,
       'and it NAMES the file -- not merely a count going up',
       '\n'.join(l for l in out1.split('\n') if 'zz_planted' in l)[:300])
    ok('KEY ONLY' in out1,
       'and marks it KEY ONLY, so the reason is legible without reading the tool')

    print('\nDIRECTION 2 -- account for it BY NAME')
    rc2, out2 = run('--expect-unauthenticated', PLANTED_REL)
    ok(rc2 == EXIT_CLEAN,
       'naming the planted caller silences the finding (exit %d)' % rc2,
       out2[-400:])
    ok('ACCOUNTED' in out2 and PLANTED_REL in out2,
       'and it is still LISTED, as ACCOUNTED -- an exemption that removed the '
       'row would hide the caller instead of accounting for it',
       '\n'.join(l for l in out2.split('\n') if 'zz_planted' in l)[:300])

    print('\nDIRECTION 2b -- the exemption is a PATH, not a switch')
    rc3, out3 = run('--expect-unauthenticated', OTHER_REL)
    ok(rc3 == EXIT_FINDING,
       'exempting a DIFFERENT path does NOT silence it (exit %d) -- or '
       '--expect-unauthenticated would be a blanket skip wearing a filename'
       % rc3,
       out3[-400:])
finally:
    if os.path.exists(PLANTED):
        os.remove(PLANTED)
    git('rm', '--cached', '-q', '--ignore-unmatch', PLANTED_REL)

print('\nAFTER -- the tree is restored')
rc4, out4 = run()
ok(rc4 == base_rc and PLANTED_REL not in out4,
   'the verdict is back to the baseline (%d) and the fixture is gone -- so the '
   'findings above were caused by the plant and by nothing else' % base_rc,
   'rc=%d' % rc4)
ok(not os.path.exists(PLANTED), 'the fixture file was removed from disk')
st = git('status', '--porcelain', PLANTED_REL)
ok(st.stdout.strip() == '',
   'and it is gone from the index too -- a probe that leaves a staged file '
   'behind has changed the repo it was measuring',
   st.stdout[:200])

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
