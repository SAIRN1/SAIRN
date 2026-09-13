"""Control for tools/closing_error.py, and for the two generators using it.

    python tests/run_closing_error_probe.py     (exit 0 pass, 1 fail)

THE CONTROL COMES FIRST, which is the seventh convention in
`docs/2026-09-13-cross-domain-disciplines.md`: build the thing that makes it
fail before trusting the run that says it passed. A tripwire nobody has watched
fire is the same shape as the `--check` it was written to supplement.

TWO LAYERS, AND THE SECOND IS THE ONE THAT MATTERS:

  1. the Traverse object itself -- an empty required leg refuses, an empty
     ALLOWED leg does not, and an allowance with no reason is refused at
     declaration time rather than at read time.
  2. THE REAL GENERATORS, driven with one source deliberately emptied. A
     tripwire that works on a hand-built object and is not actually wired into
     the generator is a tripwire that has never been in the path of anything.

Layer 2 monkeypatches the generator's OWN source function in a subprocess and
requires the generator to REFUSE -- exit 2, not exit 0 with a thinner document.
The repo is never written to: each run is given a temp path to write to.

Exit 0 pass, 1 fail.
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['closing_error.py']

import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import closing_error as CE                                      # noqa: E402

fails = []


def check(cond, label):
    print('  %-5s %s' % ('ok' if cond else 'FAIL', label))
    if not cond:
        fails.append(label)


def quiet_close(t):
    """close() into a buffer. Returns (refused, text)."""
    buf = io.StringIO()
    try:
        t.close(out=buf)
        return False, buf.getvalue()
    except CE.EmptyLeg:
        return True, buf.getvalue()


# ── 1. THE OBJECT ────────────────────────────────────────────────────────────
print('1. a required leg that contributes NOTHING is a refusal')
t = CE.Traverse('docs/fake.md')
t.leg('tools on disk', 97, 'git ls-files tools/')
t.leg('hook entries', 0, '.claude/settings.json')
refused, out = quiet_close(t)
check(refused, 'an empty required leg refuses')
check('hook entries' in out and '<<< EMPTY' in out,
      '...and the empty leg is NAMED and marked, not just counted')
check('.claude/settings.json' in out,
      '...along with what it was supposed to be read FROM')

print('')
print('2. CONTROL: every leg contributing means it closes')
t = CE.Traverse('docs/fake.md')
t.leg('tools on disk', 97, 'git ls-files tools/')
t.leg('hook entries', 12, '.claude/settings.json')
refused, out = quiet_close(t)
check(not refused, 'a full traverse does not refuse')
check('every leg closed' in out, '...and says so')
# THE FLOOR IS STATED, NOT IMPLIED. A closed traverse is not a correct survey,
# and the 27 wrong probe attributions found the same day are the proof: they
# were a non-zero count the whole time.
check('not a correct survey' in out,
      '...and states its own floor -- no source MISSING is not any source RIGHT')

print('')
print('3. a leg allowed to be zero needs a REASON, at declaration time')
t = CE.Traverse('docs/fake.md')
t.optional_leg('archived apps', 0, 'archive/', 'the branch is deliberately empty')
refused, out = quiet_close(t)
check(not refused, 'an ALLOWED zero does not refuse')
check('zero, allowed' in out, '...and is marked as allowed, with its reason')

raised = False
try:
    CE.Traverse('docs/fake.md').optional_leg('x', 0, 'y', '   ')
except ValueError:
    raised = True
check(raised, 'an allowance with a BLANK reason is refused where it is written')

# ── 4. THE GENERATORS, with a source really emptied ──────────────────────────
# The layer that matters. A tripwire proven only on a hand-built object has
# never been in the path of the thing it guards.
print('')
print('4. the REAL generators refuse when one of their sources goes empty')

SHIM = (
    'import sys\n'
    'sys.path.insert(0, %r)\n'
    'import %s as G\n'
    'G.%s = lambda *a, **k: %s\n'
    'G.DOC = %r\n'
    'sys.exit(G.main([]))\n')


def run_with_empty(module, fn, empty_value, label):
    d = tempfile.mkdtemp(prefix='closing-probe-')
    shim = os.path.join(d, '_runner.py')
    doc = os.path.join(d, 'out.md')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        SHIM % (os.path.join(REPO, 'tools'), module, fn, empty_value, doc))
    try:
        p = subprocess.run([sys.executable, shim], cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=900)
        wrote = os.path.exists(doc) and os.path.getsize(doc) > 0
        return p.returncode, (p.stdout or '') + (p.stderr or ''), wrote
    finally:
        shutil.rmtree(d, ignore_errors=True)


for module, fn, empty, label in [
        ('tooling_inventory', 'suite_refs', '{}',
         'nothing under tests/ invokes anything'),
        ('tooling_inventory', 'hooked', '{}',
         'no hook entries in settings.json'),
]:
    rc, out, wrote = run_with_empty(module, fn, empty, label)
    check(rc == 2, '%s.%s -> %s: REFUSES with exit 2 (got %d)'
          % (module, fn, label, rc))
    check(not wrote, '...and writes NO document rather than a thinner one')
    check('REFUSED' in out or 'contributed NOTHING' in out,
          '...and says which source was empty')

# ...and the control in the other direction: untouched, it still writes.
d = tempfile.mkdtemp(prefix='closing-probe-ok-')
try:
    doc = os.path.join(d, 'out.md')
    shim = os.path.join(d, '_runner.py')
    io.open(shim, 'w', encoding='utf-8', newline='\n').write(
        'import sys\n'
        'sys.path.insert(0, %r)\n' % os.path.join(REPO, 'tools') +
        'import tooling_inventory as G\n'
        'G.DOC = %r\n' % doc +
        'sys.exit(G.main([]))\n')
    p = subprocess.run([sys.executable, shim], cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=900)
    check(p.returncode == 0,
          'CONTROL: untouched, the generator still writes (got %d)' % p.returncode)
    body = io.open(doc, encoding='utf-8', errors='replace').read() \
        if os.path.exists(doc) else ''
    check(len(body) > 2000, '...and the document is a real one')
    # The table goes IN the document, so a reader sees which legs closed rather
    # than a bare OK in a terminal nobody kept. Asserted on a ROW, not on the
    # heading: a heading is prose and can be reworded, while a row carries the
    # source name and its count, which is the thing convention 3 asks for. The
    # first version of this arm matched the heading, in the wrong case, and
    # went red against a document that was completely correct.
    check('git ls-files tools/' in body and 'Closing error' in body,
          '...and it carries the named, itemized source table, rows and all')
    check('not a correct survey' in body.lower() or
          'MISSING, not that any source is RIGHT' in body,
          '...and the document states the floor too, not just the terminal')
finally:
    shutil.rmtree(d, ignore_errors=True)

print('')
if fails:
    print('%d FAILING CHECK(S)' % len(fails))
    for f in fails:
        print('  %s' % f)
    sys.exit(1)
print('ALL CHECKS PASS')
