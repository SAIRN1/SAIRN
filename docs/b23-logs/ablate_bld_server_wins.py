"""ABLATION HARNESS for tests/sairnbuild_server_wins.js.

Mutates a COPY of sairnbuild.html and re-runs the suite against the copy.
The live clone is NEVER written: a temp tree is built with the same relative
layout the suite expects (ROOT/sairnbuild.html, ROOT/tests/<suite>.js), so the
suite's own `path.join(__dirname, '..')` resolves to the copy.

THE CONTROL COMES FIRST. An unmutated copy must come back exit 0 with the
baseline arm count, or nothing below is attributable to a mutation.

Usage:  python ablate_bld.py            run every mutation
        python ablate_bld.py N1 D1      run only the named ones
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = r"C:\Users\marsh\Documents\SAIRN-cody"
APP = os.path.join(REPO, 'sairnbuild.html')
SUITE_REL = os.path.join('tests', 'sairnbuild_server_wins.js')
SUITE = os.path.join(REPO, SUITE_REL)

# (name, what layer is removed, old, new)
MUTATIONS = [
    # ── bld_bids PENDING TRACKING, fourth b28 check 4 (HIGH) ──────────────
    ('N1', 'the DECLARATION replaced by a LINE COMMENT carrying it',
     "BLD_PENDING_TRACKED['bld_bids'] = true;",
     "// BLD_PENDING_TRACKED['bld_bids'] = true;"),
    ('N2', 'the DECLARATION deleted outright (control: must be REFUSED)',
     "BLD_PENDING_TRACKED['bld_bids'] = true;",
     ""),
    ('N3', 'the DECLARATION flipped to false (control: must be REFUSED)',
     "BLD_PENDING_TRACKED['bld_bids'] = true;",
     "BLD_PENDING_TRACKED['bld_bids'] = false;"),
    ('N4', 'the retry GUARD broken, a BLOCK COMMENT carries a satisfying one',
     "if(!BLD_PENDING_TRACKED[key]||!Array.isArray(o[key]))return;",
     "/* was: if(!BLD_PENDING_TRACKED[key]||...) */ if(!Array.isArray(o[key]))return;"),
    ('N5', 'a real bldPendingMark call site deleted, a COMMENT carries the literal',
     "if(syncResult)bldPendingClear('bld_bids',String(b.id));else bldPendingMark('bld_bids',String(b.id));",
     "// if(syncResult)bldPendingClear('bld_bids',...);else bldPendingMark('bld_bids',...);"),
    ('N6', 'the retry GUARD broken, a STRING LITERAL carries a satisfying one',
     "if(!BLD_PENDING_TRACKED[key]||!Array.isArray(o[key]))return;",
     "var _n='BLD_PENDING_TRACKED[key]';if(!Array.isArray(o[key]))return;"),

    # ── bld_draws, fourth b28 check 2 (the no-arm gap) ─────────────────────
    ('D1', 'bld_draws:false in BLD_SESSION_REQUIRED (THE GAP)',
     "var BLD_SESSION_REQUIRED = { bld_bids: true, bld_draws: true };",
     "var BLD_SESSION_REQUIRED = { bld_bids: true, bld_draws: false };"),
    ('D2', 'bld_bids:false in BLD_SESSION_REQUIRED (control: must be REFUSED)',
     "var BLD_SESSION_REQUIRED = { bld_bids: true, bld_draws: true };",
     "var BLD_SESSION_REQUIRED = { bld_bids: false, bld_draws: true };"),
    ('D3', 'bld_draws DROPPED from BLD_SESSION_REQUIRED entirely',
     "var BLD_SESSION_REQUIRED = { bld_bids: true, bld_draws: true };",
     "var BLD_SESSION_REQUIRED = { bld_bids: true };"),
    ('D4', 'the DECLARATION kept but a COMMENT carries bld_draws:true',
     "var BLD_SESSION_REQUIRED = { bld_bids: true, bld_draws: true };",
     "var BLD_SESSION_REQUIRED = { bld_bids: true /* bld_draws: true */ };"),

    # ── REGRESSION: fourth b27 / b27-resume's M-series, re-driven because b23
    #    replaced that arm's two inline strippers with the shared code() and
    #    struct(). A consolidation that quietly loosened a working control
    #    would be invisible without these.
    ('M1', 'REGRESSION: the retry call-site fourth argument DELETED',
     "jobs.push(bldData('write',key,rec,!!BLD_SESSION_REQUIRED[key]).then(function(saved){",
     "jobs.push(bldData('write',key,rec).then(function(saved){"),
    ('M2', 'REGRESSION: fourth argument replaced by `false`',
     "jobs.push(bldData('write',key,rec,!!BLD_SESSION_REQUIRED[key]).then(function(saved){",
     "jobs.push(bldData('write',key,rec,false).then(function(saved){"),
    ('M3', 'REGRESSION: fourth argument replaced by `0`',
     "jobs.push(bldData('write',key,rec,!!BLD_SESSION_REQUIRED[key]).then(function(saved){",
     "jobs.push(bldData('write',key,rec,0).then(function(saved){"),
    ('M5', 'REGRESSION: real retry call broken, BLOCK COMMENT carries a satisfying one',
     "jobs.push(bldData('write',key,rec,!!BLD_SESSION_REQUIRED[key]).then(function(saved){",
     "/* bldData('write',key,rec,!!BLD_SESSION_REQUIRED[key]) */ jobs.push(bldData('write',key,rec).then(function(saved){"),
    ('M6', "REGRESSION: retry call-site verb 'write' -> 'read'",
     "jobs.push(bldData('write',key,rec,!!BLD_SESSION_REQUIRED[key]).then(function(saved){",
     "jobs.push(bldData('read',key,rec,!!BLD_SESSION_REQUIRED[key]).then(function(saved){"),
    ('M7', 'REGRESSION: real retry call broken, a STRING carries a satisfying one',
     "jobs.push(bldData('write',key,rec,!!BLD_SESSION_REQUIRED[key]).then(function(saved){",
     "var _m=\"bldData('write',key,rec,!!BLD_SESSION_REQUIRED[key])\";jobs.push(bldData('write',key,rec).then(function(saved){"),
]


def die(why):
    print('COULD NOT RUN: %s Nothing was verified.' % why)
    sys.exit(2)


def run(tag, old, new):
    """Returns (exit, passed, failed, red_arm_names, output)."""
    work = tempfile.mkdtemp(prefix='b23-bld-')
    try:
        os.makedirs(os.path.join(work, 'tests'))
        src = io.open(APP, encoding='utf-8', newline='').read()
        if old is not None:
            n = src.count(old)
            if n != 1:
                return (None, None, None, [],
                        'anchor occurs %d times, expected exactly 1 -- '
                        'MUTATION NOT APPLIED' % n)
            src = src.replace(old, new, 1)
        io.open(os.path.join(work, 'sairnbuild.html'), 'w',
                encoding='utf-8', newline='').write(src)
        shutil.copy(SUITE, os.path.join(work, SUITE_REL))
        r = subprocess.run(['node', os.path.join(work, SUITE_REL)],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=work)
        o = (r.stdout or '') + (r.stderr or '')
        # ANCHORED TO THE SUITE'S OWN SUMMARY LINE, and this is not pedantry:
        # the first version read `(\d+) passed, (\d+) failed` unanchored, and
        # b23's new assertion MESSAGES quote the phrase "at 25 passed, 0
        # failed" as evidence. So on every run where one of those arms went
        # red, this harness parsed the count out of the failure text instead
        # of the summary and reported ACCEPTED for a mutation the suite had
        # just REFUSED by name. The measuring tool had the same defect as the
        # thing it was measuring, one layer out.
        m = re.search(r'^sairnbuild_server_wins: (\d+) passed, (\d+) failed$',
                      o, re.M)
        reds = re.findall(r'^  FAIL (.+)$', o, re.M)
        return (r.returncode,
                int(m.group(1)) if m else None,
                int(m.group(2)) if m else None,
                reds, o)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if not os.path.isfile(APP):
    die('sairnbuild.html is absent.')
if not os.path.isfile(SUITE):
    die('%s is absent.' % SUITE_REL)

only = [a for a in sys.argv[1:] if not a.startswith('-')]

print('ABLATION -- tests/sairnbuild_server_wins.js, on a COPY. '
      'Live clone never written.')
print('')

rc0, p0, f0, reds0, out0 = run('BASELINE', None, None)
print('  %-4s %-62s exit=%-3s %s passed, %s failed'
      % ('CTRL', 'the UNMUTATED copy (control -- must be exit 0)', rc0, p0, f0))
if rc0 != 0 or f0 != 0 or not p0:
    print('')
    print('CONTROL FAILED. Nothing below is attributable to a mutation.')
    print(out0[-1800:])
    sys.exit(2)
BASE = p0
print('       baseline arm count: %d passed, 0 failed' % BASE)
print('')

accepted, refused, notapplied = [], [], []
for name, what, old, new in MUTATIONS:
    if only and name not in only:
        continue
    rc, p, f, reds, o = run(name, old, new)
    if rc is None:
        print('  %-4s %-62s %s' % (name, what[:62], reds or o))
        notapplied.append(name)
        continue
    # THE VERDICT IS THE EXIT CODE PLUS A NAMED RED ARM, never the parsed
    # count alone: a count read out of the wrong line is how the first run of
    # this harness reported six false ACCEPTEDs.
    if rc != 0 and reds:
        verdict = 'REFUSED'
        refused.append(name)
    else:
        verdict = '*** ACCEPTED -- THE LAYER IS UNPROTECTED ***'
        accepted.append(name)
    print('  %-4s %-62s exit=%-3s %s/%s  %s'
          % (name, what[:62], rc, p, f, verdict))
    if reds:
        for rname in reds[:3]:
            print('         red arm: %s' % rname[:95])

print('')
print('%d REFUSED, %d ACCEPTED, %d not applied'
      % (len(refused), len(accepted), len(notapplied)))
if accepted:
    print('ACCEPTED (unprotected): %s' % ', '.join(accepted))
sys.exit(1 if (accepted or notapplied) else 0)
