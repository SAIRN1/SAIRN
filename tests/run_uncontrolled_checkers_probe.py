"""Control pairs for the promoted checkers that had none.

    python tests/run_uncontrolled_checkers_probe.py     (exit 0 pass, 1 fail)

WHY THIS FILE EXISTS. `tools/checker_control_check.py` asked every promoted
checker for proof it can fire, and **five had none at all** -- nothing anywhere
in `tests/` so much as named them:

    checkblocks.py            div_balance_check.py      orphan_register_check.py
    sairn_dead_button_audit.py                          vercel_config_check.py

`checkblocks.py` is why the meta-checker exists. It **always exited 0**, even
while printing `FAILED_BLOCKS:1`, and it is Guardian Check 0a -- the one
CLAUDE.md calls non-negotiable and says hard-blocks everything else. It was
fixed on 2026-09-12. **Nothing proved the fix**, which is the same gap one level
up: a repair nobody has watched fail is a repair nobody has tested.

EVERY SECTION IS A PAIR AND BOTH HALVES ARE REQUIRED:

    plant the defect -> the checker must REPORT it
    plant clean      -> the checker must STAY SILENT

A checker that always reports passes the first half alone; one that never
reports passes the second alone. Only the pair says anything.

FIXTURES ARE WRITTEN TO A TEMP DIRECTORY AND NEVER TO A REAL APP FILE. A control
that mutates a tracked file in place is how this platform stranded five PROBE
commits on `origin/main` in one day.

THE DOCSTRING ABOVE NAMED FIVE AND THE FILE TESTED THREE, for its first day.
`orphan_register_check.py` and `sairn_dead_button_audit.py` were listed up there
as checkers that had no control, and then no section was ever written for them --
so the only place they appeared was the prose. That is precisely the FILE LEVEL
over-credit `checker_control_check.py`'s own history records: a file naming five
checkers in its docstring while testing three. The meta-checker was not fooled,
because attribution is declared rather than read -- but a human reading this
docstring would have been. Sections 4 and 5 close it, 2026-09-13.

Exit 0 pass, 1 fail. Exit 3 SKIPPED when `node` is absent -- but only sections
that actually need it are skipped, and a real failure elsewhere still exits 1,
because a skip must never swallow a red arm.

`node` IS NEEDED BY EXACTLY ONE OF THESE CHECKERS, not two. This file said two
and gated ALL FIVE sections behind it, so on a machine without node the three
pure-Python controls did not run either and the file reported SKIPPED. Verified
by grep: `checkblocks.py` is the only tool here that shells out to node.
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['checkblocks.py', 'div_balance_check.py', 'vercel_config_check.py',
                'orphan_register_check.py', 'sairn_dead_button_audit.py']

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, 'tools')
fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def run(tool, *args):
    p = subprocess.run([sys.executable, os.path.join(TOOLS, tool)] + list(args),
                       cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def tmpfile(name, body):
    d = tempfile.mkdtemp(prefix='ctl-probe-')
    p = os.path.join(d, name)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    return d, p


HAVE_NODE = shutil.which('node') is not None


# ── 1. checkblocks.py -- THE ONE THAT COULD NOT FAIL ─────────────────────────
print('1. checkblocks.py -- Guardian Check 0a, which always exited 0 until today')
if not HAVE_NODE:
    print('   SKIPPED: `node` is not on PATH, and checkblocks.py parses')
    print('   JavaScript with it. Could not run is not ran clean, so the file')
    print('   exits 3 at the end -- unless something else failed outright.')
if HAVE_NODE:
    BROKEN = ('<html><body>\n<script>\nfunction zz({ {{{ ;\n</script>\n'
              '</body></html>\n')
    CLEAN = ('<html><body>\n<script>\nfunction zz(){ return 1; }\n</script>\n'
             '</body></html>\n')
    d, p = tmpfile('broken.html', BROKEN)
    try:
        rc, out = run('checkblocks.py', p)
        check(rc == 1, 'a block that does not parse exits 1 (got %d)' % rc)
        check('FAILED_BLOCKS:1' in out, '...and says FAILED_BLOCKS:1')
    finally:
        shutil.rmtree(d, ignore_errors=True)
    d, p = tmpfile('clean.html', CLEAN)
    try:
        rc, out = run('checkblocks.py', p)
        check(rc == 0, 'a file whose blocks all parse exits 0 (got %d)' % rc)
        check('FAILED_BLOCKS:0' in out, '...and says FAILED_BLOCKS:0')
    finally:
        shutil.rmtree(d, ignore_errors=True)
    # COULD NOT TELL IS ITS OWN ANSWER. A file with no <script> at all is the
    # extractor failing, not a clean file, and reporting 0 there would be the
    # original defect wearing a different hat.
    d, p = tmpfile('noscript.html',
                   '<html><body><p>no script here</p></body></html>\n')
    try:
        rc, out = run('checkblocks.py', p)
        check(rc == 2, 'a file with NO script block exits 2, not 0 (got %d)' % rc)
        check('COULD NOT RUN' in out, '...and says COULD NOT RUN in those words')
    finally:
        shutil.rmtree(d, ignore_errors=True)

# ── 2. div_balance_check.py ──────────────────────────────────────────────────
print('')
print('2. div_balance_check.py')
d, p = tmpfile('unbalanced.html', '<html><body>\n<div><div>\n</div>\n</body></html>\n')
try:
    rc, out = run('div_balance_check.py', p)
    check(rc == 1, 'an unclosed <div> exits 1 (got %d)' % rc)
finally:
    shutil.rmtree(d, ignore_errors=True)
d, p = tmpfile('balanced.html', '<html><body>\n<div><div>\n</div></div>\n</body></html>\n')
try:
    rc, out = run('div_balance_check.py', p)
    check(rc == 0, 'a balanced file exits 0 (got %d)' % rc)
finally:
    shutil.rmtree(d, ignore_errors=True)
# The 2026-08-07 fix: a <div> inside an HTML COMMENT must not count. Pinned here
# because nothing pinned it, and a fix nobody watched fail is untested.
d, p = tmpfile('commented.html',
               '<html><body>\n<div>\n<!-- <div> this one is prose -->\n</div>\n'
               '</body></html>\n')
try:
    rc, out = run('div_balance_check.py', p)
    check(rc == 0, 'a <div> inside an HTML COMMENT does not count (got %d)' % rc)
finally:
    shutil.rmtree(d, ignore_errors=True)

# ── 3. vercel_config_check.py ────────────────────────────────────────────────
print('')
print('3. vercel_config_check.py -- the 256-char buildCommand ceiling')
LONG = 'cp a.html dist/a.html && ' * 20
d, p = tmpfile('vercel.json',
               '{"buildCommand": "%s", "rewrites": []}\n' % LONG.rstrip(' &'))
try:
    rc, out = run('vercel_config_check.py', p)
    check(rc == 1, 'a buildCommand over the ceiling exits 1 (got %d)' % rc)
    check(len(LONG) > 256, 'fixture is valid: the command really is over 256 chars')
finally:
    shutil.rmtree(d, ignore_errors=True)
d, p = tmpfile('vercel.json', '{"buildCommand": "cp a.html dist/a.html", '
                              '"rewrites": [{"source": "/a", "destination": "/a.html"}]}\n')
try:
    rc, out = run('vercel_config_check.py', p)
    check(rc == 0, 'a config within the ceiling exits 0 (got %d)' % rc)
finally:
    shutil.rmtree(d, ignore_errors=True)

# ── 4. orphan_register_check.py ──────────────────────────────────────────────
# It reads TWO files and hardcodes one of them: `APP` is stonedesk.html at module
# level, with no flag to move it. So the fixtures are driven through a shim that
# imports the module and re-points APP -- the same pattern
# tests/run_snapshot_freshness_probe.py uses on SNAPSHOT, and for the same
# reason: a control that edited the real stonedesk.html to plant its defect
# would be the tracked-file mutation this file's own header warns about.
print('')
print('4. orphan_register_check.py -- the register vs the file, and the index')

REGISTER = ('<html><body><script>\n'
            '// @REGISTER module=zz-yard removed=2026-01-01 canonical=zzKeep'
            ' canonical_key=zz_live deleted=zzGone orphan_keys=zz_dead\n'
            'function zzKeep(){ return localStorage.getItem(\'zz_live\'); }\n'
            '</script></body></html>\n')

# SEVEN COLUMNS, because that is what the real index has and the tool reads the
# status out of cell 3 by position. A three-column fixture put the status where
# the item goes, and a CLOSED row came back as a finding -- the fixture was
# wrong, not the tool, and a probe that had shipped with it would have recorded
# a false defect against a checker that was behaving correctly.
INDEX_HEAD = ('| App | Item | Status | Owner | Blocked by | Next action | Sz |\n'
              '|---|---|---|---|---|---|---|\n')
ROW = '| **Tooling** | **%s** | %s | Fourth | -- | trace it | S |\n'


def orphan_run(app_body, index_body):
    d = tempfile.mkdtemp(prefix='ctl-orphan-')
    app = os.path.join(d, 'app.html')
    idx = os.path.join(d, 'index.md')
    io.open(app, 'w', encoding='utf-8', newline='\n').write(app_body)
    io.open(idx, 'w', encoding='utf-8', newline='\n').write(index_body)
    shim = os.path.join(d, '_runner.py')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        'import sys\n'
        'sys.path.insert(0, %r)\n' % TOOLS +
        'import orphan_register_check as S\n'
        'S.APP = %r\n' % app +
        'sys.exit(S.main(["--index", %r]))\n' % idx)
    try:
        q = subprocess.run([sys.executable, shim], cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=600,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                    PYTHONUTF8='1'))
        return q.returncode, (q.stdout or '') + (q.stderr or '')
    finally:
        shutil.rmtree(d, ignore_errors=True)


rc, out = orphan_run(REGISTER, INDEX_HEAD + ROW % ('something unrelated', 'Open'))
check(rc == 0, 'a register that matches the file, and an index that does not '
               'mention it, is CLEAN (got %d)' % rc)

rc, out = orphan_run(REGISTER,
                     INDEX_HEAD + ROW % ('zzGone double-render still live', 'Open'))
check(rc == 1, 'an OPEN index row naming a deleted= function is reported '
               '(got %d)' % rc)
check('zzGone' in out, '...and the name is printed')

# THE SUPPRESSION HALF. If a CLOSED row still counted, the tool would report
# every historical row forever and be routed around within a day.
rc, out = orphan_run(REGISTER, INDEX_HEAD + ROW % ('zzGone double-render still '
                                                   'live', '**CLOSED 2026-01-02**'))
check(rc == 0, 'the SAME row marked CLOSED is not a finding (got %d)' % rc)

# The register side, which is checked against the FILE rather than the index.
rc, out = orphan_run(REGISTER.replace('</script>',
                                      'function zzGone(){ return 1; }\n</script>'),
                     INDEX_HEAD + ROW % ('something unrelated', 'Open'))
check(rc == 1, 'a deleted= name that is DEFINED again is reported (got %d)' % rc)

rc, out = orphan_run(REGISTER.replace(
    'function zzKeep(){ return localStorage.getItem(\'zz_live\'); }',
    'var x = localStorage.getItem(\'zz_live\');'),
    INDEX_HEAD + ROW % ('something unrelated', 'Open'))
check(rc == 1, 'a canonical= survivor that no longer exists is reported '
               '(got %d)' % rc)

# A FILE WITH NO @REGISTER LINES IS EXIT 2, NOT A PASS -- the same
# could-not-tell rule as checkblocks.py's no-script case above. A tool pointed
# at the wrong file checks nothing, and nothing is not clean.
rc, out = orphan_run('<html><body><script>function zzKeep(){return 1;}</script>'
                     '</body></html>\n',
                     INDEX_HEAD + ROW % ('something unrelated', 'Open'))
check(rc == 2, 'a file carrying NO @REGISTER line exits 2, not 0 (got %d)' % rc)
check('checking NOTHING' in out, '...and says it is checking nothing')


# ── 5. sairn_dead_button_audit.py ────────────────────────────────────────────
# IT ALWAYS EXITS 0, WHATEVER IT FINDS. That is not a defect being pinned here
# for later repair -- tools/report_only_checks.py deliberately reads it by
# SECTION COUNT (`by_section`) rather than by exit code, and says so. So this
# control asserts the counts, which is the contract that actually holds, and
# asserts the always-0 property explicitly so that a future change to either
# side cannot quietly break the other.
print('')
print('5. sairn_dead_button_audit.py -- Guardian check 27, read by section count')


def buttons_on(body):
    d, p = tmpfile('app.html', body)
    try:
        return run('sairn_dead_button_audit.py', p)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def section(out, label):
    """The count the registry's by_section() parser reads, for one section."""
    m = re.search(r'^%s\..*?->\s*(\d+)\s*$' % re.escape(label), out, re.M)
    return int(m.group(1)) if m else -1


rc, out = buttons_on('<html><body>\n'
                     '<button onclick="zzMissingFn()">Go</button>\n'
                     '<script>function zzReal(){ return 1; }</script>\n'
                     '</body></html>\n')
check(section(out, 'A') == 1, 'a handler whose target is never defined is '
                              'section A (got %d)' % section(out, 'A'))
check('zzMissingFn' in out, '...and the name is printed')
check(rc == 0, 'AND IT STILL EXITS 0 -- the property report_only_checks.py\'s '
               'by_section() exists for (got %d)' % rc)

rc, out = buttons_on('<html><body>\n'
                     '<button onclick="zzReal()">Ok</button>\n'
                     '<script>function zzReal(){ return 1; }</script>\n'
                     '</body></html>\n')
check(section(out, 'A') == 0, 'a handler whose target IS defined is not a '
                              'finding (got %d)' % section(out, 'A'))

rc, out = buttons_on('<html><body>\n'
                     '<button onclick="showToast(\'not built\')">Export</button>\n'
                     '<script>function showToast(m){}</script>\n'
                     '</body></html>\n')
check(section(out, 'B') == 1, 'an inline handler whose only action is a toast '
                              'is section B (got %d)' % section(out, 'B'))

# C1 AND C2 ARE OPPOSITE FIXES and the tool says so in its own output. One
# fixture produces both, so the split is driven rather than assumed: the
# difference is the CALLER COUNT and nothing else.
rc, out = buttons_on('<html><body>\n'
                     '<button onclick="zzLive()">Live</button>\n'
                     '<script>\nfunction showToast(m){}\n'
                     'function zzLive(){ showToast(\'nope\'); }\n'
                     'function zzOrphan(){ showToast(\'nope\'); }\n'
                     '</script>\n</body></html>\n')
check(section(out, 'C1') == 1, 'a toast-only function WITH a caller is C1, '
                               'wire-up (got %d)' % section(out, 'C1'))
check(section(out, 'C2') == 1, 'a toast-only function with ZERO callers is C2, '
                               'delete (got %d)' % section(out, 'C2'))

rc, out = buttons_on('<html><body><script>\n'
                     'function zzDup(){ return 1; }\n'
                     'function zzDup(){ return 2; }\n'
                     'function outer(){ function zzScoped(){ return 1; } }\n'
                     'function other(){ function zzScoped(){ return 2; } }\n'
                     '</script></body></html>\n')
check(section(out, 'D1') == 1, 'two definitions in the SAME scope are D1, a '
                               'real collision (got %d)' % section(out, 'D1'))
check(section(out, 'D2') == 1, 'the same name in DIFFERENT scopes is D2, '
                               'informational (got %d)' % section(out, 'D2'))

# THE 58-PHANTOM-FINDING FIXTURE. A naive /\*.*?\*/ comment strip blanks a regex
# literal and a URL containing `/*`, and every definition after it then reads as
# "never defined". The tool uses a real state machine; this is what proves it.
rc, out = buttons_on('<html><body>\n'
                     '<button onclick="zzReal()">Ok</button>\n'
                     '<script>\n'
                     'var re = /\\/\\* not a comment \\*\\//;\n'
                     'var url = "https://example.com/*/x";\n'
                     'function zzReal(){ return re.test(url) ? 1 : 2; }\n'
                     '</script>\n</body></html>\n')
check(section(out, 'A') == 0, 'a regex literal and a URL containing /* do not '
                              'blank the file (got %d)' % section(out, 'A'))

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
if not HAVE_NODE:
    print('SKIPPED: section 1 did not run -- `node` is not on PATH. Everything')
    print('else passed, but this is not a clean run of this file.')
    sys.exit(3)
print('ALL CHECKS PASS')
