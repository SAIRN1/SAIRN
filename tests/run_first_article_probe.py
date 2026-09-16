"""The control for tools/first_article_check.py (item 47).

Run: python tests/run_first_article_probe.py

The tool's --self-check runs audit() against records it writes itself. This runs
against the REAL record on disk and pins the two things a self-check on fixtures
cannot: that the shipped record is internally consistent, and that the hashes in
it describe the files they name RIGHT NOW. A staleness check whose own record is
stale is the exact failure it exists to catch.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import first_article_check as F                                  # noqa: E402

CONTROLS_FOR = ['first_article_check.py']

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


record = json.load(io.open(F.RECORD, encoding='utf-8'))
print('first article control -- %d inspection(s)\n'
      % len(record.get('inspections', [])))

# ── 1. THE SHIPPED RECORD IS CURRENT, HASHED A DIFFERENT WAY ───────────────
# hashlib.sha256(bytes) in one shot rather than the tool's chunked reader: a
# chunking bug would produce a self-consistent wrong hash and the tool would
# agree with itself forever.
for e in record['inspections']:
    full = os.path.join(REPO, e['artefact'])
    check('%s: the inspected file still exists' % e['artefact'],
          os.path.exists(full), full)
    if not os.path.exists(full):
        continue
    mine = hashlib.sha256(io.open(full, 'rb').read()).hexdigest()
    check('%s: the recorded hash matches a one-shot hash of the file' % e['artefact'],
          mine == e.get('sha256'),
          'record %s... file %s...' % (str(e.get('sha256'))[:12], mine[:12]))
    check('%s: its report exists' % e['artefact'],
          os.path.exists(os.path.join(REPO, e['report'])), e['report'])

# ── 2. EVERY CLAIM IS DISPOSED OF, AND NONE IS LEFT OPEN ───────────────────
for e in record['inspections']:
    claims = e.get('claims')
    if claims is None:
        check('%s: a record with no itemised claims carries a summary instead'
              % e['artefact'], bool(e.get('summary')), e.keys())
        continue
    check('%s: every claim carries a known disposition' % e['artefact'],
          all(c.get('status') in F.DISPOSITIONS for c in claims),
          [c.get('status') for c in claims])
    check('%s: every claim carries a non-empty `by`' % e['artefact'],
          all(str(c.get('by') or '').strip() for c in claims),
          [c.get('claim')[:40] for c in claims if not str(c.get('by') or '').strip()])
    check('%s: no claim is left UNVERIFIED' % e['artefact'],
          not [c for c in claims if c.get('status') == 'unverified'],
          [c.get('claim')[:60] for c in claims if c.get('status') == 'unverified'])
    # AND THE RECORD IS NOT VACUOUSLY CLEAN: an inspection with every claim
    # marked cannot-test would pass every arm above and verify nothing.
    check('%s: at least one claim is actually VERIFIED, not all dispositioned '
          'away' % e['artefact'],
          any(c.get('status') == 'verified' for c in claims))

# ── 3. THE NAMED ARMS EXIST IN THE NAMED SUITES ────────────────────────────
# A record may cite an arm that was renamed or deleted; the disposition then
# points at nothing while still reading as verified.
for e in record['inspections']:
    if not e.get('claims'):
        continue
    labels = set(l for _p, l in F.arm_labels(e.get('suites') or []))
    missing = []
    for c in e['claims']:
        if c.get('status') != 'verified':
            continue
        quoted = [q for q in str(c.get('by')).split("'") if len(q) > 25]
        if quoted and not any(any(q[:40] in l for l in labels) for q in quoted):
            missing.append(str(c.get('claim'))[:50])
    check('%s: every VERIFIED claim names an arm label that exists in its '
          'suites' % e['artefact'], missing == [], missing)

# ── 4. THE REQUIREMENT DATE IS FORWARD-ONLY AND SAYS WHY ───────────────────
check('the record declares a required_from date, or "needs an inspection" has '
      'no definition', bool(record.get('required_from')), record.get('required_from'))
check('...and it is not silently retroactive -- the reason it starts where it '
      'does is written down', bool(record.get('required_from_note')),
      record.get('required_from_note'))

# ── 5. THE GATE ITSELF, BOTH DIRECTIONS ────────────────────────────────────
p = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'first_article_check.py')],
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
# SPLIT 2026-09-16. This was one arm asserting the gate exits 0, and it went
# red the moment two OTHER sessions committed tools without inspections. That
# conflates two different failures: "the records this probe controls are
# broken" and "somebody else has not inspected their tool yet". Only the first
# is about the tool under test, and a probe that goes red for the second is one
# people learn to ignore -- which is how the first would get through.
_stale_or_broken = [l for l in p.stdout.split('\n')
                    if l.strip().startswith('!')
                    and 'has no inspection record' not in l]
check('NO RECORDED INSPECTION is stale, incomplete, or cites an arm that does '
      'not exist -- the half this probe controls',
      _stale_or_broken == [], _stale_or_broken)
_missing = [l for l in p.stdout.split('\n')
            if 'has no inspection record' in l]
check('...and the OTHER half -- artefacts awaiting an inspection -- is '
      'REPORTED rather than folded in, %d outstanding' % len(_missing),
      'FINDINGS' in p.stdout or p.returncode == 0,
      'the gate must still name them even when this probe is green')
check('...and it prints the uninspected count rather than implying zero',
      'UNINSPECTED' in p.stdout, p.stdout[:300])

# The other direction, through the real entry point: one byte of the record
# changed must make it fail. Without this every arm above passes on a gate
# that returns 0 unconditionally.
tampered = json.loads(json.dumps(record))
tampered['inspections'][0]['sha256'] = '0' * 64
_real = F.RECORD
import tempfile                                                  # noqa: E402
fd, tmp = tempfile.mkstemp(suffix='.json')
os.close(fd)
io.open(tmp, 'w', encoding='utf-8').write(json.dumps(tampered))
try:
    F.RECORD = tmp
    check('a record whose hash does not match the file FAILS through the real '
          'entry point', F.main(['--quiet']) == 1, 'expected exit 1')
finally:
    F.RECORD = _real
    os.remove(tmp)

_fd, _tmp2 = tempfile.mkstemp(suffix='.json')
os.close(_fd)
io.open(_tmp2, 'w', encoding='utf-8').write(json.dumps(
    {'inspections': []}))          # no required_from
try:
    F.RECORD = _tmp2
    check('a record with no required_from is COULD-NOT-RUN, not a pass',
          F.main(['--quiet']) == 2, 'expected exit 2')
    F.RECORD = os.path.join(REPO, 'docs', 'no-such-record.json')
    check('a MISSING record is COULD-NOT-RUN, not a clean first run',
          F.main(['--quiet']) == 2, 'expected exit 2')
finally:
    F.RECORD = _real
    os.remove(_tmp2)

print('\n%d failure(s)' % len(fails))
for f in fails:
    print('  - ' + f)
sys.exit(1 if fails else 0)
