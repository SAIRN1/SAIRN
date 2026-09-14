"""tests/run_financial_invariant_probe.py -- both halves of the financial-write
piece: the invariant runner and the idempotency checker.

    python tests/run_financial_invariant_probe.py

THE ARMS THAT MATTER ARE THE CONTROLS. Both tools report clean on this repo
today, and a tool that reports clean is indistinguishable from one that looks at
nothing unless it can be shown to go red. So:

  * a real engine is SABOTAGED by one cent and the runner must catch it;
  * a synthetic in-memory-keyed write must read as GUARDED-IN-MEMORY, because
    no real instance exists on this platform to point at;
  * each tool's blind lock must BITE -- break a criterion and the tool must
    refuse to judge anything real, exiting 2 rather than reporting a pass.

ACCURACY AND STABILITY ARE PINNED AS SEPARATE FIELDS (arm 3). Collapsing them
would have hidden the first real finding of this build: ledger.validateEntry
read 2000/2000 STABLE while MISCLASSIFIED, because the adapter compared
undefined with undefined. A single score would have said PASS.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import idempotency_check as I                                   # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(('  PASS ' if ok else '  FAIL ') + label + (('   ' + str(detail)) if detail else ''))
    if not ok:
        failures.append(label)


def node(*args, **kw):
    p = subprocess.run(['node', os.path.join(kw.get('root', REPO), 'tools',
                                             'invariant_runner.js')] + list(args),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=kw.get('root', REPO))
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def py(*args):
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'idempotency_check.py')]
                       + list(args), capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=REPO)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print('1. the blind lock runs in ISOLATION, before any engine is called')
rc, out = node('--fixtures')
check('1a  the runner lock passes on its own', rc == 0, 'exit %d' % rc)
check('1b  and it says the fixtures ran before any engine was called',
      'before any engine was called' in out)
rc, out = py('--fixtures')
check('1c  the idempotency lock passes on its own', rc == 0, 'exit %d' % rc)
check('1d  and its POSITIVE fixture is the real api/ledger.js, not a synthetic one',
      'REAL api/ledger.js' in out)

print('2. THE LOCK BITES -- a broken criterion stops everything')
tmp = tempfile.mkdtemp(prefix='fininv-')
shutil.copytree(os.path.join(REPO, 'tools'), os.path.join(tmp, 'tools'))
shutil.copytree(os.path.join(REPO, 'api'), os.path.join(tmp, 'api'),
                ignore=shutil.ignore_patterns('*.test.js'))
reg = os.path.join(tmp, 'tools', 'invariant_registry.js')
src = io.open(reg, encoding='utf-8').read()
# Invert the double-entry criterion: balanced now means UNbalanced.
# THE SABOTAGE MUST ACTUALLY APPLY, AND THAT IS NOW ASSERTED.
# The anchor was `o.debit_total === o.credit_total`. When the registry moved to
# integer cents that string stopped existing, str.replace() silently did
# nothing, and arms 2a/2b failed against a tool that was working perfectly -- a
# control that no longer breaks its target tests nothing, which is the SECOND
# time that exact shape has appeared in this file.
_sab = src.replace('o.debit_total_cents === o.credit_total_cents',
                   'o.debit_total_cents !== o.credit_total_cents', 1)
check('2z  the sabotage anchor still matches -- a control that no longer breaks '
      'its target is not a control', _sab != src,
      'the registry changed shape and this anchor did not follow')
io.open(reg, 'w', encoding='utf-8', newline=chr(10)).write(_sab)
rc, out = node(root=tmp)
check('2a  an inverted criterion makes the runner exit 2', rc == 2, 'exit %d' % rc)
check('2b  and it says NOTHING REAL WAS RUN', 'NOTHING REAL WAS RUN' in out)
shutil.rmtree(tmp, ignore_errors=True)

print('3. ACCURACY and STABILITY are two fields, never one score')
rc, out = node('--cases', '200', '--json')
data = json.loads(out[out.index('{'):])
for r in data['results']:
    check('3a  %-34s has both fields' % r['id'],
          'accuracy' in r and 'stability' in r and 'verdict' in r['accuracy']
          and 'held' in r['stability'])
check('3b  every row carries the EVIDENCE its type was read from',
      all(len(r.get('evidence', '')) > 40 for r in data['results']))
# ── ARM 3c REWRITTEN 2026-09-13, AND THE REASON IS A CORRECTION TO ME ──
# It used to assert margin appeared on EXACTLY ONE row, "not padded onto
# equalities". That was right about the mathematics and wrong about the code:
# roofing-billing and care-charges both check `|stated - computed| < 0.005`, and
# a 0.005 tolerance band has real unused headroom. ledger is the genuine
# exception -- a bare `===` on FLOATS with no band at all, which is itself the
# finding rather than an absence of one.
#
# This is a criterion corrected on the merits after measuring the engines, NOT
# an assertion loosened to make a changed tool pass. The distinction is the one
# docs/2026-09-13-cross-domain-disciplines.md item 1 exists to keep visible, and
# the old wording is quoted above so a reader can see exactly what changed.
withmargin = [r for r in data['results'] if r['margin'].get('worst') is not None]
check('3c  every engine now reports a margin -- the tolerance band is in the CODE '
      'even where the identity is an equality',
      len(withmargin) == len(data['results']),
      '%d of %d' % (len(withmargin), len(data['results'])))
check('3d  a margin is never displayed wider than the band it sits inside',
      all(abs(r['margin']['worst']) <= 0.0050001 for r in withmargin),
      [(r['id'], r['margin']['worst']) for r in withmargin])
check('3e  the double-entry row is distinguishable: a zero-width band reports a '
      'NON-POSITIVE margin, because there is no headroom to have',
      [r for r in withmargin if r['id'].startswith('ledger')][0]['margin']['worst'] <= 0)

print('4. CONTROL -- sabotage a REAL engine by one cent and the runner must catch it')
target = os.path.join(REPO, 'api', '_lib', 'roofing-billing.js')
orig = io.open(target, encoding='utf-8').read()
old = '  const subtotal = money(lines.reduce(function (s, l) { return s + l.amount; }, 0));'
try:
    assert old in orig, 'sabotage anchor missing -- the control cannot run'
    io.open(target, 'w', encoding='utf-8', newline='\n').write(
        orig.replace(old, old[:-2] + ') - 0.01;', 1))
    rc, out = node('--cases', '200')
    check('4a  a one-cent error in a real engine is caught', rc == 1, 'exit %d' % rc)
    check('4b  and it is reported as a STABILITY failure, not an accuracy one',
          'TYPE CONFIRMED   0/200' in out or '0/200' in out)
finally:
    io.open(target, 'w', encoding='utf-8', newline='\n').write(orig)
check('4c  the engine was restored byte-identical',
      io.open(target, encoding='utf-8').read() == orig)
rc, out = node('--cases', '200')
check('4d  and the restored tree is clean again', rc == 0, 'exit %d' % rc)

print('5. the idempotency checker names the dangerous shape')
got = I.analyse('x.js', "const seen = new Map();\n"
                        "if (seen.has(payload.idempotency_key)) return;\n"
                        "await fetch(rest('t'), { method: 'POST' });")
check('5a  a module-level key store consulted WITH the caller key is GUARDED-IN-MEMORY',
      got['verdict'] == 'GUARDED-IN-MEMORY', got['verdict'])
got = I.analyse('x.js', "const BOUNDARY_LOGGED = new Set();\n"
                        "if (!BOUNDARY_LOGGED.has(seenKey)) log();\n"
                        "const q = 'source_id';\n"
                        "await fetch(rest('t'), { method: 'POST' });")
check('5b  CONTROL: a LOG-dedupe store is NOT -- the real api/sd-data.js false '
      'positive that forced this narrowing',
      got['verdict'] != 'GUARDED-IN-MEMORY', got['verdict'])
got = I.analyse('x.js', "await fetch('https://x', { method: 'POST' });")
check('5c  a retryable write with no key is UNGUARDED', got['verdict'] == 'UNGUARDED')
check('5d  a file with no write at all is not judged',
      I.analyse('x.js', "const a = 1;") is None)

rc, out = py()
check('5e  the real run exits 1 while unguarded writes exist', rc == 1, 'exit %d' % rc)
check('5f  and it DISCLOSES that its negative fixture is synthetic',
      'NEGATIVE FIXTURE IS SYNTHETIC' in out)

# ── 6. THE KEY VOCABULARY IS HAND-WRITTEN AND WAS WRONG ────────────────────
# api/sairndental/public-complaint-submit.js has a real, deliberate, durable
# guard -- a hashed submission_key read back inside a ten-minute window, with
# its own migration -- and read as UNGUARDED for a day, because the key was not
# one of the seven names this checker knew. Section 6 holds the correction.
print('\n--- 6. the key vocabulary, and the guard it could not see ---')
check('6a  submission_key is in the vocabulary',
      'submission_key' in I.KEY_NAMES, I.KEY_NAMES)
check('6b  the REAL guard reads as durably guarded, not UNGUARDED',
      I.analyse('api/sairndental/public-complaint-submit.js',
                io.open(os.path.join(REPO, 'api', 'sairndental',
                                     'public-complaint-submit.js'),
                        encoding='utf-8', errors='replace').read()
                )['verdict'] == 'GUARDED-DURABLE',
      'the second real positive fixture is not reading as guarded')
check('6c  the blind lock passes with it included', I.run_fixtures() == [],
      str(I.run_fixtures()))
check('6d  and it is PINNED as a real fixture, so dropping the term takes the '
      'lock RED rather than going silent',
      'public-complaint-submit' in io.open(
          os.path.join(REPO, 'tools', 'idempotency_check.py'),
          encoding='utf-8').read(),
      'the second real positive fixture is gone from run_fixtures()')
cov = I.key_term_coverage()
check('6e  coverage is MEASURED per term, so a never-matching term is visible',
      isinstance(cov, dict) and set(cov) == set(I.KEY_TERMS), str(cov))
check('6f  ...and the run prints it rather than keeping it internal',
      'THE KEY VOCABULARY IS HAND-WRITTEN' in out, out[:400])
check('6g  the three terms that match nothing are named, not hidden',
      'match NO file and never have' in out, out[:600])

# ── 6b. THE CANDIDATES ARE DERIVED, EVEN THOUGH THE CLASSIFICATION IS NOT ──
# Three derivations of the vocabulary itself were built and measured; all three
# were worse and the numbers are recorded at KEY_SHAPE in the tool. What IS
# derivable is the CANDIDATE LIST, and that is the half that failed:
# submission_key sat in the tree for a day with a real guard on it and nothing
# pointed at it.
print('\n--- 6b. a new key cannot sit in the tree unnamed ---')
cands = I.derive_key_candidates(I.REPO)
check('6h  candidates are derived from api/, not read from a list',
      isinstance(cands, dict) and len(cands) > 0, str(cands))
check('6i  every derived candidate has a hand-written judgment today',
      all(k in I.KEY_CANDIDATES_JUDGED for k in cands),
      'UNCLASSIFIED: ' + str(sorted(k for k in cands
                                    if k not in I.KEY_CANDIDATES_JUDGED)))
check('6j  ...and each judgment says WHY, not just yes/no',
      all(len(v) > 30 for v in I.KEY_CANDIDATES_JUDGED.values()),
      str([k for k, v in I.KEY_CANDIDATES_JUDGED.items() if len(v) <= 30]))
# THE ARM THAT PROVES IT PREVENTS THE RECURRENCE. Pretend submission_key was
# never added to the vocabulary: the reporter must surface it as UNCLASSIFIED,
# which is what would have happened on the day it was written.
_terms = I.KEY_TERMS
try:
    I.KEY_TERMS = [t for t in _terms if t != 'submission_key']
    back = I.derive_key_candidates(I.REPO)
    un = sorted(k for k in back if k not in I.KEY_CANDIDATES_JUDGED)
    check('6k  REPLAY: with submission_key unknown, the reporter surfaces it',
          un == ['submission_key'], 'unclassified was ' + str(un))
    check('6l  ...and points at the file that carries it',
          back.get('submission_key') ==
          ['api/sairndental/public-complaint-submit.js'],
          str(back.get('submission_key')))
finally:
    I.KEY_TERMS = _terms
check('6m  the patch was removed, or every later arm is bogus',
      I.KEY_TERMS is _terms and 'submission_key' in I.KEY_TERMS, str(I.KEY_TERMS))
check('6n  the run PRINTS the derived candidates and the unclassified count',
      'DERIVED FROM api/' in out and 'UNCLASSIFIED' in out, out[:900])
# Newlines collapsed before matching: the sentence wraps in the real output and
# the first version of this arm asserted a phrase that spans a line break --
# the same reading-the-wrong-thing failure two D-arms in the claims probe hit.
_flat = ' '.join(out.split())
check('6o  ...and refuses to read "all judged" as "the vocabulary is complete"',
      'not the same as the vocabulary being complete' in _flat
      and 'not key-shaped at all is invisible' in _flat, _flat[:1200])

# ── 7. ITEM 6 TRIAGE -- a denominator for "being triaged" ──────────────────
print('\n--- 7. how many has anybody actually read ---')
tri, terr = I.load_triage()
check('7a  the triage register loads', terr is None and isinstance(tri, dict), str(terr))
check('7b  every entry carries a verdict AND a reason -- an exemption with no '
      'reason is an ignored finding',
      all(v.get('verdict') and v.get('why') for v in tri.values()),
      str([k for k, v in tri.items() if not (v.get('verdict') and v.get('why'))]))
check('7c  the verdicts are from the declared vocabulary',
      all(v['verdict'] in ('SAFE', 'FIX', 'FIXED', 'ACCEPTED', 'UNTRIAGED')
          for v in tri.values()),
      str(sorted(set(v['verdict'] for v in tri.values()))))
check('7d  the run reports judged and untriaged as SEPARATE numbers',
      'ITEM 6 TRIAGE' in out and 'untriaged' in out, out[:400])
check('7e  ...and names every untriaged file rather than only counting them',
      'UNTRIAGED (nobody has read these' in out, out[:600])
check('7f  a judgment for a file the checker no longer flags is called out as '
      'stale, not left to look current',
      'JUDGED BUT NO LONGER UNGUARDED' in out, out[-1500:])
# AN UNREADABLE REGISTER MUST NOT READ AS AN EMPTY ONE. Driven directly rather
# than by moving the real file, so nothing on disk is touched.
_real = I.TRIAGE
try:
    I.TRIAGE = os.path.join(REPO, 'tools', '__no_such_triage__.json')
    _t, _e = I.load_triage()
    check('7g  a missing register is an ERROR, not "nobody has judged anything"',
          _t is None and _e, 'returned %r / %r' % (_t, _e))
finally:
    I.TRIAGE = _real
check('7h  ...and the patch was removed, or every later arm is bogus',
      I.TRIAGE == _real, 'TRIAGE left patched')

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  ' + f)
sys.exit(1 if failures else 0)
