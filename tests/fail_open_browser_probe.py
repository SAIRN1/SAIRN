"""Probe fail_open_check.py's browser-side pass, added 2026-09-04.

The three original patterns are all `res.ok ? await res.json() : []` -- an
api/*.js fetch. Pointing the tool at an app's HTML returned zero for a reason
that had nothing to do with the app, and that zero was very nearly recorded as
a clean sweep. The browser-side pass finds the storage loader every SAIRN app
has, where a corrupt record and an absent one return the same value.

FIXTURES, NOT THE REAL TREE, for the two arms that need a shape the tree does
not currently contain. Every live loader is silent, so the "a loader that LOGS
is not reported" exclusion cannot be exercised against real files -- a negative
control proved exactly that by deleting the exclusion and seeing the count not
move. An untestable branch in a checker is how a checker quietly stops working.

Run: python tests/fail_open_browser_probe.py
"""
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'fail_open_check.py')

SILENT = """<html><script>
function zzLd(k,d){try{var r=localStorage.getItem(k);return r===null?d:JSON.parse(r);}catch(e){return d;}}
</script></html>
"""
LOGGING = """<html><script>
function zzLd(k,d){try{var r=localStorage.getItem(k);return r===null?d:JSON.parse(r);}
  catch(e){console.error('zz: unreadable record for '+k);return d;}}
</script></html>
"""
OTHER_RETURN = """<html><script>
function zzLd(k,d){try{var r=localStorage.getItem(k);return r===null?d:JSON.parse(r);}catch(e){return null;}}
</script></html>
"""


def run(target):
    p = subprocess.run([sys.executable, TOOL, target],
                       capture_output=True, text=True, cwd=REPO)
    return (p.stdout or '') + (p.stderr or '')


def loader_count(out):
    m = re.search(r'\((\d+) storage loader\(s\)', out)
    assert m, 'could not parse the loader count from:\n' + out
    return int(m.group(1))


def with_file(name, body, fn):
    p = os.path.join(REPO, name)
    io.open(p, 'w', encoding='utf-8', newline='').write(body)
    try:
        return fn(name)
    finally:
        if os.path.exists(p):
            os.remove(p)


results = {}

results['a_silent_loader_is_reported'] = with_file(
    'zz_fo_silent.html', SILENT, lambda n: loader_count(run(n)) == 1)

# THE ARM THE TREE CANNOT PROVIDE. No live loader logs, so without this fixture
# the exclusion is dead code that nothing exercises.
results['a_LOGGING_loader_is_NOT_reported'] = with_file(
    'zz_fo_logging.html', LOGGING, lambda n: loader_count(run(n)) == 0)

# A catch that returns something other than the default is a different shape
# and is deliberately out of scope -- reporting it would widen the pattern
# past the one defect it describes.
results['a_catch_returning_null_is_NOT_this_shape'] = with_file(
    'zz_fo_other.html', OTHER_RETURN, lambda n: loader_count(run(n)) == 0)

# And the real tree, so the pass is known to run where it matters.
#
# ── THESE TWO ARMS COULD ONLY PASS WHILE THE DEFECT EXISTED (2026-09-08) ──
# They were `loader_count(out) > 0` and `'stonedesk.html' in out`: the first
# asserted the real tree is scanned BY FINDING AT LEAST ONE SILENT LOADER, and
# the second asserted the HTML walk happens BY FINDING StoneDesk NAMED IN THE
# FINDINGS. Both stopped being true the moment the last of the fourteen
# loaders was fixed -- so finishing the work broke the probe, and the probe
# had no way to say "clean" versus "did not run".
#
# WORSE, IT WENT UNNOTICED. This is a .py probe, so the JS suite runs that
# gated every one of those loader commits never executed it.
#
# The arms now assert that the SCAN happened, which is what they were always
# trying to say: the tool walked HTML files and printed its browser-side
# section, whatever the count turns out to be. `live_loader_count` stays as a
# reported number rather than an assertion -- it is the burndown, and it is
# expected to be 0 now.
full = subprocess.run([sys.executable, TOOL], capture_output=True, text=True, cwd=REPO)
out = (full.stdout or '')
results['the_browser_pass_actually_ran'] = 'BROWSER-SIDE' in out
results['the_real_tree_is_scanned'] = 'fail-open reads found:' in out
results['html_is_in_the_default_walk'] = '.html' in out and 'HTML' in out.upper()
results['live_loader_count'] = loader_count(out)

print('--- results ---')
bad = 0
for k in sorted(results):
    v = results[k]
    print('  %-38s %s' % (k, v))
    if isinstance(v, bool) and not v:
        bad += 1
print('\n%s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
sys.exit(1 if bad else 0)
