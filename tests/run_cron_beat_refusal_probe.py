#!/usr/bin/env python
"""The control for tools/cron_beat_refusal_check.py -- BOTH directions.

    python tests/run_cron_beat_refusal_probe.py

Exit 0 all arms pass, 1 any arm fails.

── WHY A CLEAN SWEEP FROM THIS TOOL NEEDS AN ABLATION ──────────────────────
The tool reports CLEAN over all four declared cron handlers. It can only mean
something if the tool is shown to FIRE on the real defect, so section B restores
the ACTUAL PRE-FIX shape of api/sairndental/send-reminder.js -- the 502 on a
failed dnt_appointments read that returned with no heartbeat, 23 times between
2026-09-12 and 2026-09-14 -- and demands it be reported.

Nothing on disk is mutated: the pre-fix shape is a source STRING classified in
process. This repo has had one probe restore another probe's mutation and report
byte-identical success, so an in-memory ablation is the safer shape when it is
available.

── AND THE THREE STATES THAT ARE NOT FINDINGS ──────────────────────────────
Section C pins all three, because each is correct code the tool must stay quiet
about, and one of them was a real finding it printed on its first run:

  PRE-AUTH. A 401 above the secret check must NOT beat. A beat written before the
  secret is checked lets anyone with the URL forge liveness for a job that never
  ran -- strictly worse than no beat.
  CANNOT BEAT. A post-auth 500 for a missing SUPABASE_URL is a real monitoring
  blind spot with an IMPOSSIBLE local fix: beat() writes to Supabase with that
  same variable. Reported in its own state, never as a finding and never folded
  into clean.
  NOT TERMINATING. A refusal that does not return is not this defect.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'cron_beat_refusal_check.py')
CONTROLS_FOR = ['cron_beat_refusal_check.py']

import cron_beat_refusal_check as B                              # noqa: E402

_pass, _fail = 0, 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


def section(t):
    print('\n' + t)


def run(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def verdicts(src):
    return [v for _l, _s, v in B.refusals(src)]


print('CRON REFUSAL WITHOUT A HEARTBEAT -- the control for the checker')

# ── A. THE CRITERIA LOCK GATES THE RUN ──────────────────────────────────────
section('A. break a criterion and the tool must REFUSE, not report clean')
rc, out = run('--fixtures')
check('A1. the lock passes on the shipped criteria', rc == 0
      and 'criteria lock:' in out, (rc, out[-300:]))
check('A1b. ...and there are enough fixtures that A1 is not vacuous',
      len(B.FIXTURES) >= 5, len(B.FIXTURES))

_real_refusal = B.REFUSAL
try:
    import re as _re
    B.REFUSAL = _re.compile(r'(?!x)x')          # matches nothing
    check('A2a. THE SABOTAGE APPLIES: the real pattern matches a res.status(502) '
          'line and the broken one does not -- asserted BEFORE the tool is '
          'driven, because a patch that silently failed would leave every arm '
          'below green for ever',
          bool(_real_refusal.search("res.status(502).json({})"))
          and not B.REFUSAL.search("res.status(502).json({})"),
          'the sabotage did not change anything')
    check('A2b. ...and the criteria lock then FAILS, because a fixture that must '
          'report can no longer report',
          B.run_fixtures() != [], B.run_fixtures())
finally:
    B.REFUSAL = _real_refusal
check('A3. the pattern was RESTORED -- otherwise every arm below runs against a '
      'sabotaged tool and this whole file means nothing',
      B.REFUSAL is _real_refusal
      and bool(B.REFUSAL.search("res.status(502).json({})")),
      B.REFUSAL.pattern)

# ── B. IT FIRES ON THE REAL DEFECT, RESTORED ────────────────────────────────
section('B. the outage this exists for, restored and reported')

# The actual pre-fix shape of api/sairndental/send-reminder.js: past the auth
# check, a failed appointment read returned 502 and wrote no heartbeat.
PRE_FIX = '''
  if (req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) {
    res.status(401).json({ error: { message: 'Unauthorized' } });
    return;
  }
  var listRes = await fetch(url);
  if (!listRes.ok) {
    res.status(502).json({ error: { message: 'Could not list appointments' } });
    return;
  }
'''
_v = verdicts(PRE_FIX)
check('B1. THE PRE-FIX SHAPE IS REPORTED -- the 502 below the auth check returns '
      'with no beat', _v == [B.CLEAN_PRE_AUTH, B.FINDING], _v)

POST_FIX = '''
  if (req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) {
    res.status(401).json({ error: { message: 'Unauthorized' } });
    return;
  }
  var listRes = await fetch(url);
  if (!listRes.ok) {
    await beat({ job: '/api/sairndental/send-reminder', outcome: 'failed' });
    res.status(502).json({ error: { message: 'Could not list appointments' } });
    return;
  }
'''
check('B2. THE SILENT HALF: the same handler AFTER its fix is not reported. The '
      'beat comes BEFORE res.status(), so a forward-only window would have '
      'reported the fix as the defect',
      verdicts(POST_FIX) == [B.CLEAN_PRE_AUTH, B.CLEAN_BEATS],
      verdicts(POST_FIX))

# ── C. THE THREE STATES THAT ARE NOT FINDINGS ───────────────────────────────
section('C. correct code the tool must stay quiet about')

check('C1. PRE-AUTH: a 401 for a bad secret must NOT beat -- beating before the '
      'secret is checked lets anyone with the URL forge liveness',
      verdicts('''
  if (req.headers.authorization !== process.env.CRON_SECRET) {
    res.status(401).json({});
    return;
  }
''') == [B.CLEAN_PRE_AUTH], verdicts('''
  if (req.headers.authorization !== process.env.CRON_SECRET) {
    res.status(401).json({});
    return;
  }
'''))

CANNOT = '''
  if (req.headers.authorization !== process.env.CRON_SECRET) {
    res.status(401).json({});
    return;
  }
  const missing = [!process.env.SUPABASE_URL ? 'SUPABASE_URL' : null].filter(Boolean);
  if (missing.length) {
    res.status(500).json({ error: { message: 'Server configuration error' } });
    return;
  }
'''
check('C2. CANNOT BEAT: a post-auth 500 for a missing SUPABASE_URL is its own '
      'state, not a finding -- beat() writes to Supabase with that same variable, '
      'so the fix is impossible locally',
      verdicts(CANNOT) == [B.CLEAN_PRE_AUTH, B.CLEAN_CANNOT_BEAT],
      verdicts(CANNOT))
check('C2b. ...and the dependency list is READ FROM heartbeat.js rather than '
      'retyped, so it cannot drift from the module it describes',
      B.beat_dependencies() is not None
      and 'SUPABASE_URL' in B.beat_dependencies(),
      B.beat_dependencies())
check('C2c. ...and it returns None on a read failure, never an empty set -- an '
      'empty set would silently turn every cannot-beat row back into a finding',
      'return None' in io.open(TOOL, encoding='utf-8').read().split(
          'def beat_dependencies')[1].split('def ')[0],
      'the None guard is gone')

check('C3. NOT TERMINATING: a refusal that does not return is not this defect, '
      'because execution continues and a beat may come later',
      verdicts('''
  if (req.headers.authorization !== process.env.CRON_SECRET) {
    res.status(401).json({});
    return;
  }
  if (!rows) {
    res.status(502).json({ error: 'x' });
  }
  send(rows);
''') == [B.CLEAN_PRE_AUTH, B.CLEAN_NO_RETURN], 'see the verdict list')

# ── D. THE REAL RUN AND ITS DENOMINATOR ─────────────────────────────────────
section('D. the real run says what it read and what it cannot cover')
rc, out = run()
import re                                                        # noqa: E402
_m = re.search(r'read (\d+) cron handler\(s\)', out)
check('D1. it reads a NON-EMPTY handler list derived from vercel.json -- a zero '
      'would make the verdict vacuous',
      bool(_m) and int(_m.group(1)) >= 3, _m.group(0) if _m else out[:300])
_cu = re.search(r'CHECKED / UNIVERSE: (\d+) of (\d+) declared crons', out)
check('D2. CHECKED / UNIVERSE is published and both figures are real, so a cron '
      'declared in vercel.json with no handler cannot vanish from the count',
      _cu is not None and int(_cu.group(1)) > 0
      and int(_cu.group(2)) >= int(_cu.group(1)),
      _cu.group(0) if _cu else 'no CHECKED / UNIVERSE line')
check('D3. THE CANNOT-BEAT ROWS ARE PRINTED ON A CLEAN RUN -- a clean line that '
      'swallowed a path which cannot self-report would be this tool committing '
      'the false-green defect it exists to find',
      'CANNOT BEAT' in out and 'NOT findings, and NOT nothing' in out,
      out[-500:])
check('D4. ...and it names the out-of-band answer, so a reader is told what DOES '
      'cover those paths rather than only that nothing local can',
      'cron_liveness_check.py' in out and 'different scheduler' in out,
      out[-500:])
check('D5. the pre-auth rule is stated in the output, because the reason a 401 '
      'is exempt is a security argument a reader must be able to check',
      'forge liveness' in out, out[:900])
check('D6. exit is 0, 1 or 2 and nothing else', rc in (0, 1, 2), rc)

# ── E. ANCHOR ARMS ──────────────────────────────────────────────────────────
section('E. the anchors this control depends on (discipline 8)')
_src = io.open(TOOL, encoding='utf-8').read()
check('E1. refusals() and beat_dependencies() are still the names this control '
      'calls; renaming either silently stops every arm above testing the tool',
      'def refusals(' in _src and 'def beat_dependencies(' in _src,
      'a function was renamed')
check('E2. CRITERIA_VERSION is present and appears in the real output',
      bool(str(getattr(B, 'CRITERIA_VERSION', '')).strip())
      and B.CRITERIA_VERSION in out, getattr(B, 'CRITERIA_VERSION', None))
check('E3. the tool declares this file as its control',
      'run_cron_beat_refusal_probe.py' in _src, 'CONTROLLED_BY is stale')
check('E4. IF_LINE is compiled at module level and matches a real `if (` line. '
      'Its first draft carried a LITERAL BACKSPACE and could never match, which '
      'made the pre-auth exemption dead code -- this repo already records one '
      'regex that shipped that way',
      hasattr(B, 'IF_LINE') and bool(B.IF_LINE.search('  if (bad) {')),
      getattr(B, 'IF_LINE', None))
check('E5. the window is a NAMED parameter rather than a buried constant, '
      'because a fixed distance on source text is a shape this repo sweeps for',
      'window=' in _src, 'the window is no longer named')

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
