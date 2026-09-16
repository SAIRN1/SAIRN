"""Does the pair analysis actually discriminate -- and does it refuse to over-claim?

    python tests/run_weakness_combination_probe.py

Item 53. Two failure shapes are being guarded against and they are opposites:

  A SIGNAL THAT FIRES ON EVERY PAIR is noise with a table. The first version of
  this tool did exactly that -- 6 of 6 real pairs -- because "BOUND IS NOT A
  CONTROL" is a property of ONE entry that propagates into every pair that entry
  appears in. It is now reported per entry. Section 4 is the arm that catches
  the regression.

  A SIGNAL THAT NEVER FIRES is a clean report from a tool that is not looking.
  Every control here has its opposite arm.

And one thing this probe deliberately does NOT do: assert the real register's
current contents. Four entries today is not four entries next week, and a probe
pinned to today's register fails on somebody else's correct addition. It asserts
the PROPERTIES of the analysis, and the one structural fact the register's own
rule makes checkable.
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import weakness_combination as W                                 # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = W.main(argv)
    return rc, buf.getvalue()


def parse_text(md):
    d = tempfile.mkdtemp(prefix='weakcomb-probe-')
    p = os.path.join(d, 'r.md')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(md)
    try:
        return W.parse(p)
    finally:
        shutil.rmtree(d, ignore_errors=True)


print('\n1. THE TOOL\'S OWN BLIND LOCK RUNS IN THE SUITE')
lines, bad = W.fixtures()
check('every fixture arm passes', bad == 0,
      [l for l in lines if l.startswith('  FAIL')])
check('the lock is not empty', len(lines) >= 20, len(lines))
rc, out = run(['--fixtures'])
check('--fixtures reads no real register', 'no real register read' in out and rc == 0)

print('\n2. THE PARSER READS FIELDS, NOT JUST TEXT')
MD = """# r

## The entries

### ZZ-1 - held up by something that is itself a recorded risk

- **Where:** `one.js`
- **What bounds it:** `two.js` checks every call. That is a bound, not a control.
- **Trigger - MECHANICAL:** `tools/watcher.py`.
- **Open with:** Michael, 2026-01-01.

### ZZ-2 - a weakness in the very thing ZZ-1 leans on

- **Where:** `two.js`
- **What bounds it:** nothing.
- **Trigger - an EVENT WITH AN OWNER:** Nothing mechanical will announce it.
- **Open with:** unassigned.

### ZZ-3 - unrelated and well behaved

- **Where:** `three.js`
- **What bounds it:** a tested control in `elsewhere.js`.
- **Trigger - MECHANICAL:** `tools/watcher.py`.
- **Open with:** Michael, 2026-01-01.
"""
ents = parse_text(MD)
by = {e['id']: e for e in ents}
check('every ### entry is parsed', len(ents) == 3, ents and len(ents))
check('the id is the leading token, so an em-dash register and an ASCII fixture '
      'parse to the SAME key', sorted(by) == ['ZZ-1', 'ZZ-2', 'ZZ-3'], sorted(by))
check('WHERE and WHAT BOUNDS IT are separate fields -- conflating them makes '
      'every entry look like it bounds itself',
      by['ZZ-1']['where_mechanisms'] == ['one.js']
      and by['ZZ-1']['bound_mechanisms'] == ['two.js'], by['ZZ-1'])
check('the TRIGGER field is separate too',
      by['ZZ-1']['trigger_mechanisms'] == ['tools/watcher.py'], by['ZZ-1'])
check('CONTROL: an entry whose bound names a file nobody else is about has '
      'bound_mechanisms set and still pairs with nothing',
      by['ZZ-3']['bound_mechanisms'] == ['elsewhere.js'], by['ZZ-3'])

print('\n3. THE CITICORP ARM -- A leans on X, B is a weakness IN X')
ps = {(p['a'], p['b']): p for p in W.pairs(ents)}
names = lambda k: [s[0] for s in ps[k]['signals']]
check('ZZ-1 x ZZ-2 trips BOUND NAMES THE OTHER',
      'BOUND NAMES THE OTHER' in names(('ZZ-1', 'ZZ-2')), names(('ZZ-1', 'ZZ-2')))
check('...naming the shared mechanism so a human can check it, not just the pair',
      any('two.js' in why for k, why in ps[('ZZ-1', 'ZZ-2')]['signals']
          if k == 'BOUND NAMES THE OTHER'))
check('CONTROL: ZZ-1 x ZZ-3 does NOT -- ZZ-3 is not a weakness in anything ZZ-1 '
      'leans on, and a signal that cannot tell those apart is not a signal',
      'BOUND NAMES THE OTHER' not in names(('ZZ-1', 'ZZ-3')), names(('ZZ-1', 'ZZ-3')))
check('CONTROL: the direction is symmetric -- it fires whichever of the two is '
      'the one leaning, because the pair is unordered',
      any(k == 'BOUND NAMES THE OTHER' for k, _w in ps[('ZZ-1', 'ZZ-2')]['signals']))

print('\n4. NO SIGNAL MAY FIRE ON EVERY PAIR (the regression that made this file)')
all_pairs = W.pairs(ents)
check('at least one pair trips nothing at all -- an analysis where every pair '
      'is a hit is a list of pairs with extra prose',
      any(not p['signals'] for p in all_pairs),
      {(p['a'], p['b']): [s[0] for s in p['signals']] for p in all_pairs})
for sig in ('SHARED MECHANISM', 'BOUND NAMES THE OTHER', 'NEITHER ANNOUNCES',
            'BOTH UNOWNED'):
    hit = [p for p in all_pairs if sig in [s[0] for s in p['signals']]]
    check('%s does not fire on every pair' % sig, len(hit) < len(all_pairs),
          (sig, len(hit), len(all_pairs)))
check('BOUND IS NOT A CONTROL is an ENTRY property and appears in NO pair '
      'signal -- it propagates to every pair of the entry that carries it, '
      'which is exactly how the first version reported 6 of 6',
      all('BOUND IS NOT A CONTROL' not in [s[0] for s in p['signals']]
          for p in all_pairs),
      [(p['a'], p['b'], [s[0] for s in p['signals']]) for p in all_pairs])
check('...and it IS still recorded, per entry, so removing it from the pairs '
      'did not lose it', by['ZZ-1']['bound_is_not_a_control'] is True)

print('\n5. THE ATTENTION SIGNALS NEED BOTH SIDES')
check('NEITHER ANNOUNCES needs both triggers non-mechanical',
      'NEITHER ANNOUNCES' not in names(('ZZ-1', 'ZZ-2')), names(('ZZ-1', 'ZZ-2')))
check('BOTH UNOWNED needs both unowned',
      'BOTH UNOWNED' not in names(('ZZ-2', 'ZZ-3')), names(('ZZ-2', 'ZZ-3')))
q = parse_text(MD.replace(
    '- **Where:** `three.js`\n'
    '- **What bounds it:** a tested control in `elsewhere.js`.\n'
    '- **Trigger - MECHANICAL:** `tools/watcher.py`.\n'
    '- **Open with:** Michael, 2026-01-01.',
    '- **Where:** `three.js`\n'
    '- **What bounds it:** nothing.\n'
    '- **Trigger - an EVENT WITH AN OWNER:** Nothing mechanical will announce it.\n'
    '- **Open with:** unassigned.'))
qp = {(p['a'], p['b']): [s[0] for s in p['signals']] for p in W.pairs(q)}
check('CONTROL: make BOTH entries silent and unowned and both signals DO fire '
      '-- a control that only ever shows the negative proves nothing',
      qp[('ZZ-2', 'ZZ-3')] == ['NEITHER ANNOUNCES', 'BOTH UNOWNED'],
      qp[('ZZ-2', 'ZZ-3')])

print('\n6. "MECHANICAL" IS CHECKED AGAINST WHAT ACTUALLY RUNS')
uw = {i: w for i, _m, w in W.unwatched_triggers(ents, 'nothing relevant here')}
check('a mechanical trigger nothing runs is reported', 'ZZ-1' in uw, uw)
check('CONTROL: the same trigger IS cleared once a runner mentions it',
      'ZZ-1' not in {i: w for i, _m, w in
                     W.unwatched_triggers(ents, 'we run tools/watcher.py nightly')})
check('CONTROL: an entry with no mechanical trigger is never reported unwatched '
      '-- it never claimed to be watched', 'ZZ-2' not in uw, uw)
check('CONTROL: unreadable runners return None, not [] -- an empty list reads '
      'as "everything is watched", which is the flattering wrong answer',
      W.unwatched_triggers(ents, None) is None)
check('a MECHANICAL trigger naming no mechanism at all is its own report, not '
      'silently a pass',
      'ZZ-9' in {i: w for i, _m, w in W.unwatched_triggers(parse_text(
          MD + '\n### ZZ-9 - vague\n\n'
               '- **Where:** `nine.js`\n'
               '- **What bounds it:** nothing.\n'
               '- **Trigger - MECHANICAL:** somebody checks.\n'
               '- **Open with:** Michael, 2026-01-01.\n'), 'x')})

print('\n7. THE REAL REGISTER, AND ONLY ITS STRUCTURAL FACTS')
real = W.parse()
check('the real register parses', real is not None and len(real) >= 1,
      real and len(real))
check('every real entry has an id of the AR-n shape',
      all(e['id'].startswith('AR-') for e in real), [e['id'] for e in real])
check('CONTROL: the entries are distinct -- a parser that returned the same '
      'entry N times would pass every arm above',
      len({e['id'] for e in real}) == len(real), [e['id'] for e in real])
real_pairs = W.pairs(real)
check('the pair count is n*(n-1)/2, so nothing was skipped',
      len(real_pairs) == len(real) * (len(real) - 1) // 2,
      (len(real_pairs), len(real)))
runners = W.runner_text()
check('the runner sources are readable at all -- if they were not, the trigger '
      'check would silently clear everything', runners is not None)
check('...and the runner text is substantial rather than an empty file that '
      'happened to exist', runners and len(runners) > 5000, runners and len(runners))

print('\n8. THE RUN ITSELF DOES NOT REPORT A VERDICT IT CANNOT SUPPORT')
rc, out = run([])
check('the run does not exit 0 while printing shared properties',
      rc != 0 or 'with a shared property.' in out, rc)
check('it says out loud that none of it is a finding',
      'NONE OF THE ABOVE IS A FINDING' in out, out[-600:])
check('it discloses the residual -- a combination where one half was never '
      'written down is invisible to any pair analysis over a register',
      'never recorded is invisible here' in out, out[-600:])
check('CONTROL: the residual is not a substitute for looking -- the tool still '
      'printed the pairs it examined', 'pair(s) examined' in out, out[:300])
check('the output is ASCII-safe, because this register is full of em-dashes '
      'and stdout here is cp1252',
      out == out.encode('ascii', 'replace').decode('ascii'),
      [l for l in out.splitlines() if l != l.encode('ascii', 'replace').decode('ascii')][:2])

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
