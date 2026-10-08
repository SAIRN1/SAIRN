"""Probe tools/comment_sensitivity_check.py, by attacking it.

The tool's claim is "these checkers' answers do not depend on the target's
comments". A comparison that can never differ would report exactly the same
thing, so every arm below builds a throwaway checker whose sensitivity is known
in advance and demands the tool get it right.

ARM 2 IS THE CONTROL THAT MATTERS. A tool that reported EVERY checker as
sensitive would pass arm 1 and be useless; a checker that deliberately ignores
comments must come back silent.

Run: python tests/run_comment_sensitivity_probe.py
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['comment_sensitivity_check.py']

import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'comment_sensitivity_check.py')

failures = []


def check(name, ok, detail=''):
    print('  %-4s %-58s %s' % ('PASS' if ok else 'FAIL', name, detail))
    if not ok:
        failures.append(name)


# A checker that COUNTS a pattern over the raw file: sensitive by construction,
# because a commented-out occurrence counts the same as a live one.
SENSITIVE = (
    "import io, sys\n"
    "s = io.open(sys.argv[1], encoding='utf-8', errors='replace').read()\n"
    "print('HITS:%d' % s.count('needleFn('))\n"
)
# The same question asked of code only. Insensitive by construction.
INSENSITIVE = (
    "import io, sys\n"
    "s = io.open(sys.argv[1], encoding='utf-8', errors='replace').read()\n"
    "code = '\\n'.join(l for l in s.split('\\n') if l.strip()[:4] != '<!--')\n"
    "print('HITS:%d' % code.count('needleFn('))\n"
)

APP = ('<html><body>\n'
       '<!-- the old call was needleFn(1) -->\n'
       '<script>function needleFn(x){ return x; }\nneedleFn(2);</script>\n'
       '</body></html>\n')


def run(checker_body, tool_name):
    tmp = tempfile.mkdtemp(prefix='cs_probe_')
    os.makedirs(os.path.join(tmp, 'tools'))
    io.open(os.path.join(tmp, 'app.html'), 'w', encoding='utf-8', newline='\n').write(APP)
    io.open(os.path.join(tmp, 'tools', tool_name), 'w', encoding='utf-8',
            newline='\n').write(checker_body)
    shim = os.path.join(tmp, '_runner.py')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        'import sys\n'
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import comment_sensitivity_check as C\n'
        'C.REPO = %r\n' % tmp +
        'C.CHECKERS = [%r]\n' % tool_name +
        'sys.exit(C.main(["x"]))\n')
    p = subprocess.run([sys.executable, shim], capture_output=True, text=True,
                       encoding='utf-8', errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    shutil.rmtree(tmp, ignore_errors=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


print('COMMENT SENSITIVITY PROBE -- the sensitivity of each fixture is known in advance\n')

# ── 1. a checker whose answer depends on comments is caught
rc, out = run(SENSITIVE, 'fx_sensitive.py')
check('1a  a comment-sensitive checker is reported',
      'answers that CHANGE when comments are removed: 1' in out, '')
check('1b  and the exit code is non-zero', rc == 1, 'exit %d' % rc)
check('1c  and it is named', 'fx_sensitive.py' in out, '')

# ── 2. CONTROL: one that ignores comments is silent
rc, out = run(INSENSITIVE, 'fx_insensitive.py')
check('2a  CONTROL: a comment-blind checker is NOT reported',
      'answers that CHANGE when comments are removed: 0' in out, '')
check('2b  CONTROL: and exits 0', rc == 0, 'exit %d' % rc)
check('2c  CONTROL: and it really compared something',
      'comparisons run   : 1' in out, 'a tool that compares 0 also exits 0')

# ── 3. THE STRIPPER MUST NOT DESTROY REAL CONTENT.
# This is the defect this tool found in tools/comment_quote_check.py on
# 2026-09-11: the SQL `--` branch ran on every file type, so
# "<title>SAIRNmechanical -- HVAC & Mechanical</title>" lost its closing tag and
# panel_nesting_check came back NO_PANELS_FOUND on a stripped copy. A prose
# double dash must survive outside a .sql file.
sys.path.insert(0, os.path.join(REPO, 'tools'))
from comment_quote_check import strip_comments  # noqa: E402
html = '<title>SAIRNmechanical -- HVAC & Mechanical</title>\n'
check('3a  a prose double-dash does NOT blank the rest of an HTML line',
      '</title>' in strip_comments(html), repr(strip_comments(html).strip()[-30:]))
check('3b  CONTROL: and it still strips a real SQL comment when asked',
      '-- gone' not in strip_comments('select 1; -- gone\n', sql=True), '')
check('3c  CONTROL: an HTML comment is still blanked',
      'secret' not in strip_comments('<!-- secret -->'), '')

# ── 4. the real repo, whatever it says today
p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True,
                   encoding='utf-8', errors='replace', cwd=REPO,
                   env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
check('4a  the real run completes and could run every checker',
      'could not run     : 0' in p.stdout, '')
check('4b  and it compared a real number of pairs',
      'comparisons run   : 0' not in p.stdout and 'comparisons run' in p.stdout,
      [l.strip() for l in p.stdout.split('\n') if 'comparisons run' in l][:1])

# ── 5. THE FINDING THIS DETECTOR PRODUCED, LOCKED SO IT CANNOT COME BACK ──
# ADDED 2026-10-07, batch 18. Arms 1-4 prove the DETECTOR works. This one
# proves the DEFECT IT FOUND is fixed, which is a different claim and the one
# that regresses.
#
# What it found: `nav_panel_check.py on sairncode.html -- exit 1 raw vs 0
# stripped. It is matching text that describes code rather than code.`
# sairncode.html has THREE `mr-kx-ytd` and only ONE is a live element; the
# second sits in a `<!-- -->` block documenting an input that was removed on
# purpose. `FAIL:DUPLICATE_IDS` was a false positive produced by a comment
# explaining a past fix.
#
# A SYNTHETIC FIXTURE, NOT sairncode.html. Pointing this arm at the real app
# would make it pass or fail on whatever somebody edits in that file next --
# the stale-anchor shape cross-domain convention 8 names. The fixture carries
# the SHAPE: one live id, one id inside a comment, nothing else.
_fx = tempfile.mkdtemp(prefix='navpanel_comment_')
try:
    _html = (
        '<html><body>\n'
        '<div class="sidebar">\n'
        '  <button onclick="nav(\'alpha\')">Alpha</button>\n'
        '</div>\n'
        '<div class="panel" id="panel-alpha">\n'
        '  <!-- THE FIELD WAS REMOVED ON PURPOSE.\n'
        '       It was `<input id="dup-me">` and nothing backed the number. -->\n'
        '  <input id="dup-me">\n'
        '</div>\n'
        '<script>function nav(x){}</script>\n'
        '</body></html>\n')
    _p = os.path.join(_fx, 'fixture.html')
    io.open(_p, 'w', encoding='utf-8', newline='\n').write(_html)
    _r = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                      'nav_panel_check.py'), _p],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', cwd=REPO)
    check('5a  nav_panel_check does NOT report DUPLICATE_IDS when the second '
          'occurrence is inside an HTML comment. One live element is not a '
          'duplicate, and a comment that explains a REMOVED element is the '
          'commonest way this file acquires a false positive',
          'DUPLICATE_IDS' not in _r.stdout,
          _r.stdout.strip()[-200:])
    # STATIC_IDS:2 is `panel-alpha` plus the ONE live `dup-me`. The commented
    # `dup-me` must not be counted, so 3 would be the old behaviour and 1 would
    # mean the tool stopped seeing the panel container as well -- the number is
    # asserted exactly rather than as "non-zero" for that reason.
    check('5b  ...and the fixture is not vacuous: the tool really read it and '
          'counted exactly the TWO live ids (panel-alpha and dup-me), not the '
          'commented third. Without this, 5a would pass on a file the tool '
          'failed to parse at all',
          'STATIC_IDS:2' in _r.stdout, _r.stdout.strip()[:200])

    # THE PAIRED POSITIVE. Two LIVE ids with the same name must still FAIL --
    # otherwise 5a could be satisfied by a tool that stopped checking.
    _html2 = _html.replace(
        '  <!-- THE FIELD WAS REMOVED ON PURPOSE.\n'
        '       It was `<input id="dup-me">` and nothing backed the number. -->\n',
        '  <input id="dup-me">\n')
    _p2 = os.path.join(_fx, 'fixture_real_dupe.html')
    io.open(_p2, 'w', encoding='utf-8', newline='\n').write(_html2)
    _r2 = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                       'nav_panel_check.py'), _p2],
                         capture_output=True, text=True, encoding='utf-8',
                         errors='replace', cwd=REPO)
    check('5c  THE PAIRED POSITIVE: two LIVE ids with the same name DO still '
          'fail. Stripping comments must not turn the duplicate-id check off, '
          'and sairncare.html fc-name and sairnfreedom.html ac-name are real '
          'duplicates this must keep catching',
          'DUPLICATE_IDS' in _r2.stdout and _r2.returncode == 1,
          'exit=%d %s' % (_r2.returncode, _r2.stdout.strip()[-200:]))
finally:
    shutil.rmtree(_fx, ignore_errors=True)

print('\n%d arm(s) failed' % len(failures))
for f in failures:
    print('  %s' % f)
sys.exit(1 if failures else 0)
