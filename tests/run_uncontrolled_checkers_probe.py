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

Exit 0 pass, 1 fail. Exit 3 SKIPPED when `node` is absent, because two of these
checkers need it and "could not run" is not "ran clean".
"""
import io
import os
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
                       cwd=REPO, capture_output=True, text=True, timeout=600)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def tmpfile(name, body):
    d = tempfile.mkdtemp(prefix='ctl-probe-')
    p = os.path.join(d, name)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(body)
    return d, p


if shutil.which('node') is None:
    print('SKIPPED: `node` is not on PATH. checkblocks.py parses JavaScript with')
    print('it, so without node this probe would prove nothing about the checker')
    print('that prompted the whole exercise. Could not run is not ran clean.')
    sys.exit(3)


# ── 1. checkblocks.py -- THE ONE THAT COULD NOT FAIL ─────────────────────────
print('1. checkblocks.py -- Guardian Check 0a, which always exited 0 until today')
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
d, p = tmpfile('noscript.html', '<html><body><p>no script here</p></body></html>\n')
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

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
