"""Control for the report-only promotion mechanism, and for the nav-matcher fix.

    python tests/run_report_only_checks_probe.py

TWO THINGS ARE GUARDED HERE AND THE SECOND IS THE IMPORTANT ONE.

1. `tools/report_only_checks.py` -- one runner with a registry, so promoting
   the next checker is a registry entry rather than a 29th hook entry. It must
   never block, must be silent on a clean run, must say so when a checker could
   NOT run, and must gate on the command text IN CODE rather than trusting
   `.claude/settings.json` -- a hook entry's only gate is `matcher`, and an
   `"if"` key is ignored in silence (2026-09-09, ten concurrent suites).

2. `tools/nav_panel_check.py`'s element matcher. It scanned `<button>` only,
   and on its first real run reported ALL 26 of SAIRNfreedom's panels
   unreachable because that app navigates with
   `<div class="nitem" onclick="sfNav('x')">`. Wired blocking, it would have
   refused every SAIRNfreedom push while the app was fine.

   **THE FIX IS DRIVEN IN BOTH DIRECTIONS, because widening a matcher to kill a
   false alarm is exactly how you buy a silent miss.** A div-navigated app must
   PASS, and an app with a genuinely unreachable panel must still FAIL -- and
   the third arm holds the tightening that removed the two phantom controls
   without losing a real one.

FIXTURES ARE SYNTHETIC, on purpose. A probe pinned to what a real app happens
to contain this week rots the moment that app is edited -- the failure
`tests/reachability/live_mode_probe.py` records against its own first version.
Nothing here reads or writes a real app file, and the repo is never touched.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
sys.path.insert(0, os.path.join(REPO, 'tools'))
import report_only_checks as roc                                  # noqa: E402

NAV = os.path.join(REPO, 'tools', 'nav_panel_check.py')
R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def nav_on(html):
    fd, path = tempfile.mkstemp(suffix='.html')
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        fh.write(html)
    try:
        p = subprocess.run([sys.executable, NAV, path], cwd=REPO,
                           capture_output=True, text=True, timeout=120)
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    finally:
        os.remove(path)


def app(nav_calls, panels, extra=''):
    """A minimal app: a sidebar of `nav_calls`, and a panel div per `panels`."""
    side = ''.join('<div class="nitem" onclick="sfNav(\'%s\')">%s</div>' % (n, n)
                   for n in nav_calls)
    body = ''.join('<div id="panel-%s" class="panel">%s</div>' % (p, p)
                   for p in panels)
    return ('<!doctype html><html><body><nav>' + side + '</nav>' + body +
            '<script>function sfNav(k){document.getElementById("panel-"+k);}'
            + extra + '</script></body></html>')


# ── A. a DIV-navigated app passes. This is the false alarm that was found. ──
rc, out = nav_on(app(['alpha', 'beta'], ['alpha', 'beta']))
check('A1 a div-navigated app passes', rc, 0)
check('A2 and its controls are counted', 'SIDEBAR_NAV_CONTROLS:2' in out, True)
check('A3 and the tag breakdown names div, not button',
      "'div': 2" in out, True)
check('A4 no panel is reported unreachable', 'FAIL:PANELS_WITH_NO_NAV' in out, False)

# ── B. the widening did NOT buy a silent miss ──────────────────────────────
# A panel with no control anywhere must still be reported. If this arm ever
# goes green-by-passing, the matcher has been widened into uselessness.
rc, out = nav_on(app(['alpha'], ['alpha', 'orphan']))
check('B1 a genuinely unreachable panel still FAILS', rc, 1)
check('B2 and it is named', "'orphan'" in out, True)
check('B3 and the wired one is not', "'alpha'" not in out.split('FAIL:')[-1], True)

# ── C. a JS `<` comparison is not an element ───────────────────────────────
# `if(days<TRIAL_DAYS)return true;` matched as an opening tag under the first
# version of the widened pattern, ran across a dozen lines to the next `>`, and
# swallowed a real nav call -- a phantom control on two real apps. An HTML tag
# name cannot contain `_`.
rc, out = nav_on(app(['alpha'], ['alpha'],
                     extra='\nfunction t(d){if(d<TRIAL_DAYS)return true;\n'
                           '  var s=document.getElementById("x");\n  return s;}'))
check('C1 the file still passes', rc, 0)
check('C2 and TRIAL_DAYS is not counted as a control',
      'TRIAL_DAYS' in out or 'trial_days' in out, False)
check('C3 the real control is still counted', 'SIDEBAR_NAV_CONTROLS:1' in out, True)

# ── D. buttons and anchors still work -- the old shapes did not regress ────
rc, out = nav_on(
    '<!doctype html><html><body>'
    '<button class="sb-btn" id="sb-alpha" onclick="nav(\'alpha\')">A</button>'
    '<a href="#" onclick="nav(\'beta\')">B</a>'
    '<div id="panel-alpha" class="panel">a</div>'
    '<div id="panel-beta" class="panel">b</div>'
    '<script>function nav(k){document.getElementById("panel-"+k);}</script>'
    '</body></html>')
check('D1 a button+anchor app still passes', rc, 0)
check('D2 and both tags are counted', "'a': 1" in out and "'button': 1" in out, True)

# ── D2. the `page-` convention, and the two defects hiding behind it ───────
# nav_panel_check matched `panel` only, so SAIRNmechanical (17 `page-`
# containers, showPage) and stonedesk-hr (15) reported ZERO panels and
# **RESULT:PASS**. Five earlier versions of this bug all failed LOUD -- a
# working app reported broken. This one failed SILENT, which is worse, and the
# report-only registry then counted it as a passing checker.
PAGE_APP = (
    '<!doctype html><html><body>'
    '<div class="sidebar-item" onclick="showPage(\'jobs\', this)">Jobs</div>'
    '<div class="sidebar-item" onclick="showPage(\'quotes\', this)">Quotes</div>'
    '<div id="page-jobs" class="page">j</div>'
    '<div id="page-quotes" class="page">q</div>'
    '%s'
    '<script>function showPage(k,el){document.getElementById("page-"+k);}</script>'
    '</body></html>')

rc, out = nav_on(PAGE_APP % '')
check('D2a a page-/showPage app is reconciled, not reported as 0 panels',
      'PANEL_COUNT:2' in out, True)
check('D2b and passes', rc, 0)

# A nav call with a TRAILING ARGUMENT. `showPage('dashboard', this)` was
# invisible: the matcher demanded the closing paren immediately after the
# quoted argument, so stonedesk-hr's fifteen working sidebar items counted as
# zero and every page came back unreachable.
check('D2c a nav call with a second argument is seen',
      'SIDEBAR_NAV_CONTROLS:2' in out, True)

# THE FINDING THE CONVENTION EXISTS TO SURFACE must still surface. The first
# attempt adopted only the `page-` ids something CALLS by name, which is
# self-defeating: an unreachable container is by definition one nothing calls.
rc, out = nav_on(PAGE_APP % '<div id="page-orphan" class="page">o</div>')
check('D2d an unreachable page- container is REPORTED', rc, 1)
check('D2e and named', "'orphan'" in out, True)

# A camelCase container: SAIRNcash switches id="homePage" with
# showPage('home'). A fifth live naming convention, and the reason resolve_panel
# derives rather than assumes -- every version of this file that picked a side
# reported a working app as broken.
#
# THIS ARM REPLACED ONE THAT ASSERTED THE OPPOSITE, and the correction is worth
# recording. It read "an app SHELL container is not a panel, so `page-` ids
# nothing navigates to must not be adopted" -- written while the tool was
# reporting SAIRNcash's homePage/appPage as unreachable. That turned out to be
# the WRONG diagnosis: those two shells ARE navigated, by showPage('home') and
# showPage('app'), and the real defect was that resolve_panel could not map the
# argument onto the camelCase id. An unreachable container IS the finding this
# tool exists for, so refusing to adopt one would have been a silent miss
# dressed up as a fix. Measured across all 22 app files afterwards: zero false
# positives, one documented suppression.
rc, out = nav_on(
    '<!doctype html><html><body>'
    '<div class="nav-item" onclick="showPage(\'home\')">Home</div>'
    '<div class="nav-item" onclick="showPage(\'app\')">App</div>'
    '<div id="homePage" class="page active">home</div>'
    '<div id="appPage" class="page">app</div>'
    '<script>function showPage(p){}</script></body></html>')
check('D2f a camelCase id is resolved from a bare nav argument', rc, 0)
check('D2g and both containers are counted', 'PANEL_COUNT:2' in out, True)

# ── D3. a panel system this tool cannot recognise is SKIPPED, not PASSED ───
rc, out = nav_on(
    '<!doctype html><html><body>'
    '<div class="tab" onclick="goTo(\'alpha\')">A</div>'
    '<div class="tab" onclick="goTo(\'beta\')">B</div>'
    '<section id="zone-alpha">a</section><section id="zone-beta">b</section>'
    '<script>function goTo(k){document.getElementById("zone-"+k);}</script>'
    '</body></html>')
check('D3a an unrecognised container convention exits 3, not 0', rc, 3)
check('D3b and says nothing was reconciled', 'SKIPPED' in out, True)
check('D3c and does not claim PASS', 'RESULT:PASS' in out, False)

# ...but a genuinely single-purpose page has nothing to reconcile and passes.
rc, out = nav_on('<!doctype html><html><body><h1>Booking</h1>'
                 '<form><input name="x"></form></body></html>')
check('D3d a single-purpose page with no nav system still passes', rc, 0)

# ── E. the runner: registry integrity ──────────────────────────────────────
missing = [e['tool'] for e in roc.REGISTRY
           if not os.path.isfile(os.path.join(REPO, 'tools', e['tool']))]
check('E1 every registered tool exists on disk', missing, [])
check('E2 every entry records when and why it was promoted',
      [e['tool'] for e in roc.REGISTRY
       if not (e.get('promoted') and e.get('evidence') and e.get('catches'))], [])

# ── F. the target set excludes what is not served ──────────────────────────
files = roc.app_files()
check('F1 no non-root html is scanned', [f for f in files if '/' in f], [])
check('F2 the archived ancestor branch is excluded',
      [f for f in files if f.startswith('archive')], [])
check('F3 and real apps are still found', len(files) > 10, True)

# ── G. the section filter counts defects, not the informational rows ───────
SAMPLE = ('A. DEAD BUTTON -- handler target never defined  -> 0\n'
          'B. DEAD BUTTON -- inline handler is toast-only  -> 0\n'
          'C1. LIVE toast-only function (wire up or relabel)  -> 3\n'
          'C2. ORPHAN toast-only function, zero callers (delete)  -> 1\n'
          'D1. DUPLICATE, SAME scope (later silently wins -- real, fix)  -> 2\n'
          'D2. same name, DIFFERENT scopes (informational, count only)  -> 9\n')
found, _ = roc.by_section(0, SAMPLE)
check('G1 C2 and D1 are findings', len(found), 2)
check('G2 C1 is not -- the tool says it needs a human read',
      any('C1.' in f for f in found), False)
check('G3 D2 is not -- the tool labels it informational',
      any('D2.' in f for f in found), False)
check('G4 a zero section is not a finding',
      any(f.startswith('A.') for f in found), False)
# by_exit is the other half: a checker that signals by exit code.
check('G5 by_exit reports nothing on 0', roc.by_exit(0, 'PASS')[0], [])
check('G6 by_exit reports something on non-zero',
      len(roc.by_exit(1, 'FAIL: 1 issue(s)\n  - too long')[0]) > 0, True)

# ── G7. exit 3 is COULD NOT RUN, not a finding and not a pass ──────────────
# Without this the runner would file the bare string "exit 3" under findings,
# which reads as a defect in the app rather than the checker failing to
# recognise it. Driven through run_one() rather than asserted on the constant.
_saved_reg, _saved_files = roc.REGISTRY, roc.app_files
_fd, _fixture = tempfile.mkstemp(suffix='.html')
with os.fdopen(_fd, 'w', encoding='utf-8') as _fh:
    _fh.write('<!doctype html><html><body>'
              '<div class="tab" onclick="goTo(\'alpha\')">A</div>'
              '<div class="tab" onclick="goTo(\'beta\')">B</div>'
              '<section id="zone-alpha">a</section>'
              '<script>function goTo(k){}</script></body></html>')
try:
    roc.REGISTRY = [{'tool': 'nav_panel_check.py', 'mode': 'apps',
                     'verdict': roc.by_exit, 'promoted': 'probe',
                     'catches': 'probe', 'why_it_matters': 'probe',
                     'evidence': 'probe'}]
    roc.app_files = lambda verbose=False: [_fixture]
    f, u = roc.sweep(quiet=True)
    check('G7 an exit-3 checker lands in unrun, NOT in findings', len(f), 0)
    check('G8 and the reason is carried through',
          len(u) == 1 and 'SKIPPED' in u[0], True)
finally:
    roc.REGISTRY, roc.app_files = _saved_reg, _saved_files
    os.remove(_fixture)

# ── H. the hook gates on the COMMAND TEXT, in code ─────────────────────────
def hook(cmd):
    payload = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': cmd}})
    t0 = time.time()
    p = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                     'report_only_checks.py'),
                        '--hook'],
                       input=payload, cwd=REPO, capture_output=True,
                       text=True, timeout=600)
    return p.returncode, (p.stdout or ''), time.time() - t0


rc, out, secs = hook('git status')
check('H1 a non-push command exits 0', rc, 0)
check('H2 and prints nothing', out.strip(), '')
# The sweep is ~a minute of work; returning at once is proof it did not start.
check('H3 and returns without sweeping (< 15s)', secs < 15, True)

rc, out, secs = hook('git log --oneline -1  # mentions git push in prose')
check('H4 a prose mention is not a push', out.strip(), '')

rc, out, secs = hook('SAIRN_SEED_GATE=off git push origin HEAD:main')
check('H5 a real push runs the sweep and STILL exits 0', rc, 0)
check('H6 and a clean sweep stays silent', out.strip(), '')

for k in sorted(R):
    ok, actual, expected = R[k]
    print('  %-6s %s' % ('ok' if ok else 'FAIL', k))
    if not ok:
        print('         expected %r, got %r' % (expected, actual))
bad = [k for k in R if not R[k][0]]
print()
print('report-only mechanism: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
