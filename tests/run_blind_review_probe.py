"""Is the worksheet actually blind, and does the accept actually cost something?

    python tests/run_blind_review_probe.py

Item 79. The whole value of this flow is an ORDERING, and an ordering is worth
exactly what its controls are worth. Two failure shapes, opposite to each other:

  A WORKSHEET THAT LEAKS. Then the round still runs, still prints an agreement
  rate, and that rate means nothing -- worse than not running, because it
  produces a number people will quote.

  A LEAK SCAN THAT REFUSES EVERYTHING. `low` is a substring of `allowed` and
  `follow`. A scanner that cannot tell those apart blocks every round and gets
  switched off, which is the same outcome as having no scanner.

Both directions are driven here, and so is the one that is neither: the
PREAMBLE deliberately contains every possible answer, because it names the
vocabulary. The first fixture run refused a round over exactly that, and the
resolution -- scan the body, not the page -- is held in section 3.

NOTHING HERE TOUCHES A REAL ROUND. Every write goes to a temp path, and section
6 proves the real sealed file and worksheet were not disturbed: a probe that
could open or overwrite a sealed round would defeat the flow it is testing.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import blind_review as B                                         # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = B.main(argv)
    return rc, buf.getvalue()


REC = {'commit': 'abc123', 'date': '2026-01-01', 'app': 'PLATFORM',
       'subject': 'a thing broke', 'summary': 'it stopped working',
       'severity': 'high', 'phase_confidence': 'secret-ish'}

print('\n1. THE TOOL\'S OWN BLIND LOCK RUNS IN THE SUITE')
lines, bad = B.fixtures()
check('every fixture arm passes', bad == 0,
      [l for l in lines if l.startswith('  FAIL')])
check('the lock is not empty', len(lines) >= 10, len(lines))
rc, out = run(['--fixtures'])
check('--fixtures reads no register', 'no register read' in out and rc == 0)

print('\n2. THE EVIDENCE IS A WHITELIST')
ev = B.evidence_of(REC)
check('the withheld field is absent', B.WITHHELD not in ev, ev)
check('CONTROL: a field nobody whitelisted is absent too, so a column added to '
      'the register tomorrow is withheld by default rather than leaked by '
      'default', 'phase_confidence' not in ev, ev)
check('CONTROL: the evidence is not empty -- withholding everything would make '
      'the round unjudgeable and trivially blind', len(ev) >= 4, ev)
check('every whitelisted field that the record has is present',
      all(k in ev for k in ('commit', 'subject', 'summary')), ev)

print('\n3. THE LEAK SCAN, IN ALL THREE DIRECTIONS')
check('an answer stated in the text is caught',
      B.leak_scan('severity is high here', ['high']) == ['high'])
check('CONTROL: clean text scans clean',
      B.leak_scan('two files changed', ['high']) == [])
check('CONTROL: a substring is NOT a leak -- `low` inside `allowed` and '
      '`follow`. A scanner that refuses every round is switched off, which is '
      'the same outcome as no scanner',
      B.leak_scan('this is allowed, follow it', ['low']) == [],
      B.leak_scan('this is allowed, follow it', ['low']))
check('...and a real standalone `low` still is', B.leak_scan('it is low', ['low']) == ['low'])
check('the scan is case-insensitive', B.leak_scan('it is HIGH', ['high']) == ['high'])
pre, body = B.build_worksheet([{'id': 'R01', 'record': REC}])
check('the generated BODY is clean of the answer', B.leak_scan(body, ['high']) == [],
      B.leak_scan(body, ['high']))
check('THE DESIGN THE FIRST FIXTURE RUN FORCED: the PREAMBLE contains every '
      'possible answer because it names the vocabulary, so scanning the whole '
      'page would refuse every round forever',
      B.leak_scan(pre, ['high']) == ['high'], B.leak_scan(pre, ['high']))
leaky = B.build_worksheet([{'id': 'R01', 'record': dict(
    REC, summary='a high severity break')}])[1]
check('CONTROL: an answer inside a record\'s own EVIDENCE is still caught, so '
      'excluding the preamble did not disable the scan',
      B.leak_scan(leaky, ['high']) == ['high'])
check('CONTROL: the body never names the sealed file',
      os.path.basename(B.SEALED) not in body)

print('\n4. A ROUND REFUSES TO START IF IT WOULD LEAK')
tmp = tempfile.mkdtemp(prefix='blind-review-probe-')
REAL = (B.REGISTER, B.ROUNDS, B.WORKSHEET, B.SEALED)
real_seal_before = (os.path.exists(B.SEALED),
                    io.open(B.SEALED, 'rb').read() if os.path.exists(B.SEALED) else None)
real_ws_before = (os.path.exists(B.WORKSHEET),
                  io.open(B.WORKSHEET, 'rb').read() if os.path.exists(B.WORKSHEET) else None)
try:
    B.WORKSHEET = os.path.join(tmp, 'ws.md')
    B.SEALED = os.path.join(tmp, 'sealed.json')

    B.REGISTER = os.path.join(tmp, 'leaky.json')
    io.open(B.REGISTER, 'w', encoding='utf-8', newline='\n').write(json.dumps(
        [dict(REC, commit='c%d' % i, severity='high',
              summary='this one is high severity, plainly') for i in range(5)]))
    rc, msg = B.start(5)
    check('a register whose evidence states the answer REFUSES the round '
          'outright', rc == 2 and 'LEAKS' in str(msg), (rc, str(msg)[:180]))
    check('CONTROL: and nothing was written, so a refused round leaves no '
          'half-made worksheet to be judged from',
          not os.path.exists(B.WORKSHEET) and not os.path.exists(B.SEALED))

    B.REGISTER = os.path.join(tmp, 'clean.json')
    io.open(B.REGISTER, 'w', encoding='utf-8', newline='\n').write(json.dumps(
        [dict(REC, commit='c%d' % i, subject='thing %d' % i,
              summary='it stopped working, case %d' % i,
              severity=B.VOCAB[i % len(B.VOCAB)]) for i in range(8)]))
    rc, msg = B.start(6)
    check('a clean register starts a round', rc == 0, (rc, str(msg)[:180]))
    ws = io.open(B.WORKSHEET, encoding='utf-8').read()
    sealed = json.load(io.open(B.SEALED, encoding='utf-8'))
    check('the sealed file holds one answer per record',
          len(sealed['answers']) == 6, sealed.get('answers'))
    check('...and the worksheet does not name the sealed file',
          os.path.basename(B.SEALED) not in ws)
    tiny = os.path.join(tmp, 'tiny.json')
    io.open(tiny, 'w', encoding='utf-8', newline='\n').write(
        json.dumps([dict(REC, commit='x', summary='it stopped, case x')]))
    B.REGISTER = tiny
    check('CONTROL: a register too small REFUSES rather than running a round of '
          'one -- an agreement rate over one record is not a rate',
          B.start(5)[0] == 2, B.start(5))
    B.REGISTER = os.path.join(tmp, 'clean.json')

    print('\n5. THE DEFEATER IS THE PRICE OF AN ACCEPT')
    B.REGISTER = os.path.join(tmp, 'clean.json')
    io.open(B.REGISTER, 'w', encoding='utf-8', newline='\n').write(json.dumps(
        [dict(REC, commit='c%d' % i, subject='thing %d' % i,
              summary='it stopped working, case %d' % i,
              severity=B.VOCAB[i % len(B.VOCAB)]) for i in range(8)]))
    B.start(6)
    sealed = json.load(io.open(B.SEALED, encoding='utf-8'))
    ids = sorted(sealed['answers'])
    sub = os.path.join(tmp, 'sub.json')

    def write_sub(rows):
        io.open(sub, 'w', encoding='utf-8', newline='\n').write(json.dumps(rows))
        os.utime(sub, (time.time() + 5, time.time() + 5))
        return sub

    good = 'x' * (B.MIN_DEFEATER_CHARS + 5)
    rc, res = B.submit(write_sub(
        [{'id': ids[0], 'severity': 'high', 'defeater': 'looks right'}]))
    check('a judgment with a THIN defeater is refused -- recording a word is '
          'not judging, and the reveal re-anchors an unreasoned accept anyway',
          rc == 2 and any('NO DEFEATER' in p for p in res), res)
    rc, res = B.submit(write_sub([{'id': ids[0], 'severity': 'high'}]))
    check('a judgment with NO defeater at all is refused', rc == 2, res)
    rc, res = B.submit(write_sub(
        [{'id': ids[0], 'severity': 'catastrophic', 'defeater': good}]))
    check('a severity outside the vocabulary is refused', rc == 2, res)
    rc, res = B.submit(write_sub(
        [{'id': 'NOT-A-RECORD', 'severity': 'high', 'defeater': good}]))
    check('a judgment naming a record not in this round is refused', rc == 2, res)
    rc, res = B.submit(write_sub(
        [{'id': ids[0], 'severity': 'high', 'defeater': good},
         {'id': ids[0], 'severity': 'low', 'defeater': good}]))
    check('the same record judged twice is refused -- otherwise a reviewer can '
          'submit both answers and be right', rc == 2, res)
    rc, res = B.submit(write_sub(
        [{'id': i, 'severity': 'high', 'defeater': good} for i in ids]))
    check('CONTROL: a complete, reasoned submission is ACCEPTED. A flow that '
          'refuses everything enforces nothing', rc == 0, res)
    check('...and it reports agreement per record against the sealed answer',
          rc == 0 and len(res['rows']) == len(ids)
          and all('recorded' in r for r in res['rows']))
    check('CONTROL: the agreement is real -- judging everything `high` against '
          'a register of mixed severities does NOT agree everywhere',
          rc == 0 and not all(r['agree'] for r in res['rows']),
          rc == 0 and [(r['mine'], r['recorded']) for r in res['rows']])
    rc, res = B.submit(write_sub(
        [{'id': ids[0], 'severity': 'high', 'defeater': good}]))
    check('a PARTIAL submission is accepted and the unjudged records are '
          'reported by name rather than counted as agreement',
          rc == 0 and len(res['missing']) == len(ids) - 1, rc == 0 and res['missing'])

    print('\n6. THE ORDERING IS ENFORCED AS FAR AS A FILE CAN CARRY IT')
    old = os.path.join(tmp, 'prepared.json')
    io.open(old, 'w', encoding='utf-8', newline='\n').write(json.dumps(
        [{'id': ids[0], 'severity': 'high', 'defeater': good}]))
    os.utime(old, (1, 1))
    rc, res = B.submit(old)
    check('a submission that PREDATES the round is refused -- a file prepared '
          'in advance was not written against this worksheet',
          rc == 2 and 'predates' in str(res), (rc, str(res)[:160]))
    check('CONTROL: the same content with a current mtime is accepted, so the '
          'refusal is about the ORDER and not about the content',
          B.submit(write_sub([{'id': ids[0], 'severity': 'high',
                               'defeater': good}]))[0] == 0)
    rc, res = B.submit(os.path.join(tmp, 'nope.json'))
    check('a missing submission is refused rather than treated as empty', rc == 2)
finally:
    B.REGISTER, B.ROUNDS, B.WORKSHEET, B.SEALED = REAL
    shutil.rmtree(tmp, ignore_errors=True)

print('\n7. THE REAL ROUND WAS NOT TOUCHED')
check('the module paths are restored',
      (B.REGISTER, B.WORKSHEET, B.SEALED) == (REAL[0], REAL[2], REAL[3]))
check('the real sealed file is exactly as it was -- a probe that could open or '
      'overwrite a sealed round would defeat the flow it is testing',
      (os.path.exists(B.SEALED), io.open(B.SEALED, 'rb').read()
       if os.path.exists(B.SEALED) else None) == real_seal_before)
check('the real worksheet is exactly as it was',
      (os.path.exists(B.WORKSHEET), io.open(B.WORKSHEET, 'rb').read()
       if os.path.exists(B.WORKSHEET) else None) == real_ws_before)
gi = io.open(os.path.join(REPO, '.gitignore'), encoding='utf-8').read()
check('the sealed file is GITIGNORED -- a reviewer who can read the answers in '
      'the repo is not reviewing blind',
      os.path.basename(B.SEALED) in gi, gi[-300:])

print()
if fails:
    print('%d ARM(S) FAILED:' % len(fails))
    for f in fails:
        print('  - ' + f)
else:
    print('ALL ARMS PASS')
sys.exit(1 if fails else 0)
