
# REQUIREMENT: a string substitution that matched nothing is REPORTED rather than
#   silently leaving the template unchanged
#
#!/usr/bin/env python
"""tests/run_eaten_substitution_probe.py

Run:  python tests/run_eaten_substitution_probe.py

The control pair for tools/eaten_substitution_check.py -- scrubber item 18's
second vehicle.

CONTROLS_FOR = ['eaten_substitution_check.py']

THIS CHECKER REPORTS TWO FINDINGS OVER 3,000 REAL COMMITS, so almost every run
anyone ever sees will be a green one. A checker nobody has watched fire looks
exactly like a repository where the problem never happens -- which is the state
this platform keeps having to correct. So the detector is driven directly, as a
pure function over message lines, and every arm plants its own case.

THE PLANTS ARE IN-MEMORY STRINGS, NOT FILE MUTATIONS, ON PURPOSE. A sabotage
that rewrites a real source file has an anchor, and an anchor that stops
matching turns the control into a silent no-op -- scrubber item 17, and the
reason 10 of 29 probes on this platform are listed UNGUARDED by
tools/sabotage_control_check.py. A string built in the test has nothing to rot.

AND THE FALSE-POSITIVE ARM IS THE ONE THAT MATTERS. The tool's whole claim is
that this shape is vanishingly rare in real commit bodies. Section C measures
that against the real history rather than asserting it.
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
import eaten_substitution_check as T          # noqa: E402

CONTROLS_FOR = ['eaten_substitution_check.py']

_pass = 0
_fail = 0


def ok(name, cond, detail=''):
    global _pass, _fail
    print('  %s %s%s' % ('PASS' if cond else 'FAIL', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if cond:
        _pass += 1
    else:
        _fail += 1


def body(*lines):
    """A message body: subject, blank, then the paragraph under test."""
    return ['subject line', ''] + list(lines)


print('eaten_substitution_check -- the control pair')

# ── A. it fires on the real shape ──────────────────────────────────────────
print('\n--- A. the planted eaten substitution ---')
{}
hits = T.scan(body(
    "94's date work, 'one module owns what a calendar date is' -- added",
    ' to the harness as a side effect. The suite is 57 passed /',
    '0 failed today.'))
ok('A1 it fires on a continuation line beginning with a stray single space',
   len(hits) == 1, hits)
ok('A2 ...and reports the PREVIOUS line too, which is where the text was eaten',
   hits and hits[0][1].endswith('-- added'), hits)
ok('A3 ...and the body line number, so the message can be found in an editor',
   hits and hits[0][0] == 4, hits)

# Reproduce the OTHER real instance's shape as an independent second case, so
# one arm passing is not the whole evidence.
hits2 = T.scan(body(
    'fail-open, and both  records in the register are fail-opens. A signed',
    " column would delete three of validateLine's seven checks and would"))
ok('A4 it fires on the second real shape as well, not just the first',
   len(hits2) == 1, hits2)

# ── B. it stays silent on everything that legitimately looks like this ─────
print('\n--- B. the silent half -- a control that only ever fires is useless ---')
ok('B1 a normally wrapped paragraph is not a finding',
   T.scan(body('a sentence that wraps across',
               'two lines with no stray space')) == [], 'fired on clean prose')

for marker in (' * a bullet', ' - a dash bullet', ' + a plus bullet',
               ' 1. a numbered item', ' 2) a paren-numbered item',
               ' a. a lettered item'):
    ok('B2 %-26r is a list item, not a finding' % marker.strip()[:24],
       T.scan(body('an introduction to the list:', marker)) == [], marker)

ok('B3 a line that STARTS a block (previous line blank) is not a finding',
   T.scan(body('a paragraph.', '', ' an indented block opening')) == [],
   'fired where nothing was joined')

ok('B4 a two-space indent is ordinary formatting, not this shape',
   T.scan(body('an introduction', '  a two-space indented line')) == [],
   'fired on a two-space indent')

ok('B5 the subject line itself is never scanned',
   T.scan([' a subject that starts with a space', '', 'body']) == [],
   'scanned the subject')

# ── C. the false-positive claim, measured against the real history ────────
print('\n--- C. the precision claim is measured, not asserted ---')
recs, err = T.commits(None, 3000)
ok('C1 3,000 real commits could actually be read', err is None and recs, err)
flagged = []
if recs:
    for sha, subject, lines in recs:
        if T.scan(lines):
            flagged.append((sha[:8], subject))
ok('C2 the corpus is the size the claim rests on -- a short read proves nothing',
   recs and len(recs) >= 2900, len(recs) if recs else 0)
# NOT PINNED TO EXACTLY 2. A third real instance SHOULD make the tool loud, and
# an arm that fails on it trains people to edit the test. A rise here means
# READ the new ones, not raise the bound.
ok('C3 the shape is rare in real commit bodies -- 5 or fewer in 3,000',
   len(flagged) <= 5,
   'flagged %d: %s -- if these are real, that is the tool working; read them '
   'before touching this bound' % (len(flagged), flagged))
subjects = ' || '.join(s for _, s in flagged)
# Matched on SUBJECT, not SHA: four clones rebase constantly and a pasted SHA
# names a commit that stops existing. The subject survives a rebase.
ok('C4 it still finds the cron clock-freeze commit item 18 records',
   'pin the clock freeze the watchdog suite' in subjects, subjects[:300])
ok('C5 ...and the poka-yoke review commit, the other recorded instance',
   'item 41 poka-yoke review' in subjects, subjects[:300])

# ── D. could-not-run is a third state and is never folded into clean ──────
# DRIVEN BY BEHAVIOUR, NOT BY GREPPING THE SOURCE. A first draft of this
# section asserted that certain sentences appear in the file, and two arms
# failed because the sentences are split across adjacent string literals --
# which is the anchor-rot shape in miniature: the refusals were all working
# and the test was reading the wrong thing.
print('\n--- D. the states that must not read as a pass ---')

_real_git = T.git
try:
    def _no_upstream(*args):
        if args[:2] == ('rev-parse', '--abbrev-ref'):
            raise subprocess.CalledProcessError(128, 'git')
        return _real_git(*args)
    T.git = _no_upstream
    rng, limit, err = T.resolve_range([])
    ok('D1 no upstream is an ERROR, not an empty range that reads as clean',
       err is not None and rng is None and limit is None,
       'rng=%r limit=%r err=%r' % (rng, limit, err))
    ok('D2 ...and the error says outright that nothing was scanned',
       err and 'Nothing was scanned' in err, err)
finally:
    T.git = _real_git
ok('D3 the patch was really removed -- otherwise every later arm is bogus',
   T.git is _real_git, 'T.git was left patched')

p4 = subprocess.run([sys.executable,
                     os.path.join(REPO, 'tools', 'eaten_substitution_check.py'),
                     '-n', '5'],
                    capture_output=True, encoding='utf-8', errors='replace')
out4 = (p4.stdout or '') + (p4.stderr or '')
ok('D4 a clean run over real commits exits 0', p4.returncode == 0, out4[:300])
ok('D5 ...and refuses to claim the messages are intact',
   'NOT "the messages are intact"' in out4.replace('\n', ' '), out4[:500])
ok('D6 ...and names the blind spot: a substitution that produced OUTPUT',
   'produced OUTPUT leaves no gap' in out4.replace('\n', ' '), out4[:500])

src = io.open(os.path.join(REPO, 'tools', 'eaten_substitution_check.py'),
              encoding='utf-8').read()
ok('D7 the docstring states recall is NOT measured',
   'RECALL IS NOT MEASURED' in src, 'the unmeasured half stopped being disclosed')

# ── E. the tool end to end, not only its detector ──────────────────────────
print('\n--- E. the whole tool, through the command line ---')
p = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'eaten_substitution_check.py'),
                    '-n', '3000'],
                   capture_output=True, encoding='utf-8', errors='replace')
out = (p.stdout or '') + (p.stderr or '')
ok('E1 a run with findings exits 1, not 0', p.returncode == 1, p.returncode)
ok('E2 it prints how many commits it actually scanned -- the denominator',
   re.search(r'commits scanned : \d+', out), out[:300])
ok('E3 it says outright that the shape is not proof of a cause',
   'A SHAPE, NOT A CAUSE' in out, out[:300])
ok('E4 and it names the fix as commit -F, never a quoted -m',
   '--amend -F' in out and 'never a quoted -m' in out, out[:400])

p2 = subprocess.run([sys.executable,
                     os.path.join(REPO, 'tools', 'eaten_substitution_check.py'),
                     '--range', 'HEAD..HEAD'],
                    capture_output=True, encoding='utf-8', errors='replace')
out2 = (p2.stdout or '') + (p2.stderr or '')
ok('E5 an empty range reports NOTHING WAS SCANNED rather than a bare clean line',
   'NOTHING WAS SCANNED' in out2, out2[:300])

p3 = subprocess.run([sys.executable,
                     os.path.join(REPO, 'tools', 'eaten_substitution_check.py'),
                     '--range'],
                    capture_output=True, encoding='utf-8', errors='replace')
out3 = (p3.stdout or '') + (p3.stderr or '')
ok('E6 a malformed argument is COULD NOT RUN (exit 2), never a clean 0',
   p3.returncode == 2 and 'COULD NOT RUN' in out3,
   'rc=%s %s' % (p3.returncode, out3[:200]))

print('')
if _fail:
    print('eaten_substitution_check: %d ARM(S) FAILED' % _fail)
    sys.exit(1)
print('eaten_substitution_check: all %d arms pass' % _pass)
