#!/usr/bin/env python
"""hover_predictive_drift_check.py (hover2's own build) -- periodic
re-validation for this platform's ROLLING/PREDICTIVE tools, as distinct
from its ordinary deterministic checkers.

WHY THIS EXISTS. EASA's ML-certification guidance (the concrete external
reference this was built from, not cited for its own sake) makes a point
that has no analogue for a deterministic check: a model's prediction
accuracy is not a fixed, one-time-provable property. It can degrade as the
real-world data distribution it scores drifts away from whatever it was
tuned or validated against -- SILENTLY, with no code change at all. A test
suite that passed once, at build time, says nothing about whether the same
tool's real-world verdicts are still trustworthy a month later. Every other
checker on this platform is re-run on every commit by construction (CI, push
gates); a tool that scores or predicts against a MOVING WINDOW of real data
is not exercised that way -- it can go stale between runs with nobody
re-looking, which is the gap this fills.

WHAT COUNTS AS A CANDIDATE, AND WHY THE LIST IS NOT EXHAUSTIVE. A
deterministic checker (does this file parse, does this pattern match) is
OUT OF SCOPE -- rerunning it finds new occurrences, not drift in a MODEL.
IN SCOPE: anything that (a) scores, classifies, or predicts, (b) reads a
ROLLING OR ACCUMULATING window of real data rather than a fixed fixture, and
(c) produces a verdict a reader is meant to trust without re-deriving it by
hand. REGISTRY below is a scan done 2026-09-22, not a closed set -- see
scan_for_more_candidates() for how to widen it.

TWO DIFFERENT KINDS OF CANDIDATE, TWO DIFFERENT MECHANISMS:

  PYTHON TOOLS WITH A REAL CLI (most of the registry) -- actually re-run,
  their JSON output's VERDICT-SHAPED fields extracted and hashed (see
  extract_verdict_signature()), compared against the last recorded
  signature. A verdict-field change is real drift, worth a look. Recorded
  under RECHECK_DAYS so the same unchanged verdict does not re-alarm daily.

  STONEDESK'S INLINE JS SCORING FORMULAS -- CANNOT be executed here; there
  is no JS runtime and no live browser session with real customer data in
  this environment. Tracked instead by SOURCE TEXT hash (has the formula
  itself changed) plus a pure staleness clock (how long since a human
  looked, regardless of whether the source changed) -- because EASA's own
  point is that the CODE not changing does not mean the model is still
  calibrated to real behaviour. This is a materially weaker signal than the
  Python half and is reported as such, not silently equated with it.

VERDICT-SIGNATURE EXTRACTION IS A HEURISTIC, DISCLOSED RATHER THAN HIDDEN:
walks the JSON tree and keeps only leaves that LOOK like a verdict (a bool,
or a short string from a small alphabet -- a band, a label, a tier) and
discards leaves that look like raw data (numbers, long prose, ISO
timestamps). This avoids hand-writing nine bespoke extractors that go stale
independently, at the cost of being approximate: it can occasionally keep a
volatile short string or drop a genuine one-word verdict. Disclosed as a
real limit, not fixed by guessing harder.

Run:
  python hover_predictive_drift_check.py                -- check all due, per RECHECK_DAYS
  python hover_predictive_drift_check.py --force         -- ignore cadence, check everything now
  python hover_predictive_drift_check.py --list          -- print the registry, no execution
  python hover_predictive_drift_check.py --selftest       -- fixture-based self-check
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

REPO_CANDIDATES = (
    'C:/Users/marsh/Documents/SAIRN-hover2',
    'C:/Users/marsh/Documents/SAIRN-hover',
)
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'predictive-drift-state.json')
RECHECK_DAYS = 7.0
TOOL_TIMEOUT = 90

# ── REGISTRY, SCAN DATE 2026-09-22 ──────────────────────────────────────────
# Found by: grepping tools/ for rolling-window/scoring/predictive docstring
# language, and grepping every app .html for a "score = 100, ... score -="
# banded-penalty shape. See module docstring for the in/out-of-scope test.
PYTHON_TOOLS = (
    {'name': 'defect_budget_policy', 'path': 'tools/defect_budget_policy.py',
     'args': ['--json'], 'why': "rolling 30-day defect-budget window; the "
     'concrete tool named when this capability was requested'},
    {'name': 'reliability_growth', 'path': 'tools/reliability_growth.py',
     'args': ['--json'], 'why': 'fits a software reliability growth model '
     'to the real defect series -- literally a predictive model'},
    {'name': 'trend_alarm', 'path': 'tools/trend_alarm.py',
     'args': ['--json'], 'why': 'PERSISTENT/WORSENING alarm state over real '
     'time series, arming conditions can flip as more data accumulates'},
    {'name': 'dora_metrics', 'path': 'tools/dora_metrics.py',
     'args': ['--json'], 'why': 'DORA tier computed over a rolling window '
     'of real git history'},
    {'name': 'checker_confidence', 'path': 'tools/checker_confidence.py',
     'args': ['--json'], 'why': 'fuses two signals into a trust SCORE per '
     'checker -- a classification, not a fixed fact'},
    {'name': 'defect_dispersion', 'path': 'tools/defect_dispersion.py',
     'args': ['--json'], 'why': 'concentrated-vs-spread verdict over the '
     'real, growing defect register'},
    {'name': 'fmea_prediction_check', 'path': 'tools/fmea_prediction_check.py',
     'args': ['--json'], 'why': 'directly measures prediction accuracy '
     '(did the FMEA draft predict the defect) -- the exact EASA-shaped '
     'question, already built, just never re-watched over time'},
    {'name': 'benford_check', 'path': 'tools/benford_check.py',
     'args': ['--json'], 'why': 'a statistical conformity verdict per '
     'corpus; corpora grow and the digit distribution can shift'},
    # No --json: text-hash fallback, a coarser signal, reported as such.
    {'name': 'allan_deviation_check', 'path': 'tools/allan_deviation_check.py',
     'args': [], 'why': 'drift-vs-noise classification over a real trend '
     'series', 'text_mode': True},
)

# StoneDesk's inline JS scoring formulas -- cannot be executed here (no JS
# runtime, no live browser session with real data). Tracked by source hash
# + staleness clock only. See module docstring.
FORMULA_CANDIDATES = (
    {'name': 'stonedesk_customer_health_score', 'file': 'stonedesk.html',
     'anchor': 'var score=100, daysSince=',
     'why': "per-customer risk score (staleness/quote-age/balance-owed "
     'penalties) shown on every customer detail panel'},
    {'name': 'stonedesk_safety_compliance_score', 'file': 'stonedesk.html',
     'anchor': 'var score = 100;\n  if(overdue.length)',
     'why': 'safety/compliance score (overdue training, incidents, ECP '
     'owner, inspections due) -- the "risk-detection health score" named '
     'when this capability was requested'},
)

_VERDICT_STRING_RE = re.compile(r'^[A-Za-z][A-Za-z _/-]{0,23}$')
_ISO_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}')


def discover_repo(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if '--repo' in argv:
        i = argv.index('--repo')
        if i + 1 < len(argv):
            return argv[i + 1]
    for candidate in REPO_CANDIDATES:
        if os.path.isdir(os.path.join(candidate, '.git')):
            return candidate
    return None


def _looks_like_verdict_string(s):
    if not isinstance(s, str) or not s:
        return False
    if _ISO_DATE_RE.match(s):
        return False
    return bool(_VERDICT_STRING_RE.match(s))


def extract_verdict_signature(obj, path=''):
    """[(path, value)], sorted, for every leaf in `obj` that looks like a
    verdict (bool, or a short label-shaped string) rather than raw data
    (number, long prose, ISO date). See module docstring for the tradeoff."""
    out = []
    if isinstance(obj, bool):
        out.append((path, obj))
    elif isinstance(obj, dict):
        for k in sorted(obj):
            out.extend(extract_verdict_signature(obj[k], path + '/' + str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(extract_verdict_signature(v, path + '[%d]' % i))
    elif _looks_like_verdict_string(obj):
        out.append((path, obj))
    return out


def _hash_signature(sig):
    blob = json.dumps(sorted(sig), sort_keys=True)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]


def run_python_tool(repo, tool):
    """(ok, signature_or_text, hash, raw_error). ok=False means COULD NOT
    RUN (never silently treated as 'no drift')."""
    path = os.path.join(repo, tool['path'].replace('/', os.sep))
    if not os.path.isfile(path):
        return False, None, None, 'tool not found at %s' % path
    try:
        r = subprocess.run([sys.executable, path] + tool['args'],
                           cwd=repo, capture_output=True, text=True,
                           encoding='utf-8', errors='replace',
                           timeout=TOOL_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, None, None, 'timed out after %ss' % TOOL_TIMEOUT
    out = r.stdout or ''
    if tool.get('text_mode'):
        # A non-zero exit with next to no stdout is the shape of a crash
        # (the real error went to stderr, stdout never got a report) rather
        # than this tool's own way of signalling a real finding -- text_mode
        # tools have no structured field to check the way --json ones do, so
        # this is the closest available signal, applied the same direction
        # as the --json branch below: do not grade a probable crash as a
        # verdict.
        if r.returncode != 0 and len(out.strip()) < 20:
            return False, None, None, ('exit %d with almost no stdout (%d chars) -- '
                                       'likely a crash, not a verdict; not graded as one'
                                       % (r.returncode, len(out.strip())))
        h = hashlib.sha256(out.encode('utf-8')).hexdigest()[:16]
        return True, {'_text_mode': True, 'exit_code': r.returncode}, h, ''
    try:
        data = json.loads(out)
    except ValueError:
        # NOT JSON does not mean the same thing at every exit code. A tool
        # that exits 0 and still prints a banner ahead of its JSON, or that
        # is legitimately a text_mode tool, is a known, disclosed shape --
        # fall back to a text hash rather than reporting nothing. A NON-ZERO
        # exit with unparsable output is a different fact: this is very
        # plausibly a crash (an unhandled exception, a traceback on stdout),
        # not a verdict, and hashing a traceback and calling two different
        # stack traces "DRIFT" would silently misreport a broken tool as a
        # changed real-world verdict -- exactly the failure mode this
        # tool's own fail-open standard exists to catch, aimed at itself.
        if r.returncode != 0:
            return False, None, None, ('exit %d with output that is not valid JSON -- '
                                       'likely a crash, not a verdict; not graded as one'
                                       % r.returncode)
        h = hashlib.sha256(out.encode('utf-8')).hexdigest()[:16]
        return True, {'_text_mode': True, 'exit_code': r.returncode,
                      '_json_parse_failed': True}, h, ''
    sig = extract_verdict_signature(data)
    sig.append(('_exit_code', r.returncode))
    return True, sig, _hash_signature(sig), ''


CONFLICT_MARKER_RE = re.compile(r'^(<{7}|={7}|>{7})', re.M)
CONFLICTED_SENTINEL = '__CONFLICTED__'


def read_formula_source(repo, candidate):
    """The function/block's own source text, located by its anchor string
    -- a fixed-size window from the anchor, not the whole file. Returns
    (text, hash) or (None, None) if the anchor is not found (the anchor
    going missing IS itself worth reporting -- the formula may have been
    renamed or restructured -- so this is surfaced as a finding, not
    silently skipped). Returns (CONFLICTED_SENTINEL, None) if the file
    carries unresolved git conflict markers -- conflict-marker sweep,
    2026-09-28: an anchor-plus-window read over a conflicted file hashes
    whichever conflict side the window lands in, silently, and a hash of
    half a merge is neither 'drifted' nor 'stable' -- it is unjudgeable
    and must say so."""
    path = os.path.join(repo, candidate['file'])
    if not os.path.isfile(path):
        return None, None
    text = io.open(path, encoding='utf-8').read()
    if CONFLICT_MARKER_RE.search(text):
        return CONFLICTED_SENTINEL, None
    idx = text.find(candidate['anchor'])
    if idx < 0:
        return None, None
    window = text[idx:idx + 600]
    h = hashlib.sha256(window.encode('utf-8')).hexdigest()[:16]
    return window, h


def load_state(path=None):
    path = path or STATE_PATH
    if not os.path.isfile(path):
        return {}
    try:
        return json.load(io.open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_state(state, path=None):
    path = path or STATE_PATH
    with io.open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, sort_keys=True)


def _due(state, name, force):
    if force:
        return True
    rec = state.get(name)
    if not rec:
        return True
    age_days = (time.time() - rec.get('checked_at_epoch', 0)) / 86400.0
    return age_days >= RECHECK_DAYS


def check_all(repo, state, force=False):
    """Returns (results, new_state). results: [{'name','kind','status',
    'detail'}], status in DRIFT/STABLE/BASELINE/SKIPPED/COULD_NOT_RUN."""
    results = []
    new_state = dict(state)
    now = time.time()

    for tool in PYTHON_TOOLS:
        name = tool['name']
        if not _due(state, name, force):
            results.append({'name': name, 'kind': 'python-tool', 'status': 'SKIPPED',
                            'detail': 'not due for %.0f more day(s)'
                            % (RECHECK_DAYS - (now - state[name]['checked_at_epoch']) / 86400.0)})
            continue
        ok, sig, h, err = run_python_tool(repo, tool)
        if not ok:
            results.append({'name': name, 'kind': 'python-tool', 'status': 'COULD_NOT_RUN',
                            'detail': err})
            continue
        prev = state.get(name)
        if prev is None:
            results.append({'name': name, 'kind': 'python-tool', 'status': 'BASELINE',
                            'detail': 'first observation, hash %s recorded' % h})
        elif prev.get('hash') != h:
            results.append({'name': name, 'kind': 'python-tool', 'status': 'DRIFT',
                            'detail': 'verdict signature changed: %s -> %s (why this tool is '
                            'in scope: %s)' % (prev.get('hash'), h, tool['why'])})
        else:
            results.append({'name': name, 'kind': 'python-tool', 'status': 'STABLE',
                            'detail': 'a lead, not a verdict: this run\'s verdict signature '
                            'matches the last one (%s) -- consistency across two live runs, '
                            'not independent proof the tool is still correct against real '
                            'behaviour' % h})
        new_state[name] = {'hash': h, 'checked_at_epoch': now,
                           'checked_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))}

    for cand in FORMULA_CANDIDATES:
        name = cand['name']
        if not _due(state, name, force):
            results.append({'name': name, 'kind': 'formula-source', 'status': 'SKIPPED',
                            'detail': 'not due for %.0f more day(s)'
                            % (RECHECK_DAYS - (now - state[name]['checked_at_epoch']) / 86400.0)})
            continue
        text, h = read_formula_source(repo, cand)
        if text == CONFLICTED_SENTINEL:
            results.append({'name': name, 'kind': 'formula-source', 'status': 'COULD_NOT_RUN',
                            'detail': '%s carries unresolved git conflict markers -- a hash '
                            'of half a merge is neither drifted nor stable; resolve the '
                            'conflict first, nothing judged' % cand['file']})
            continue
        if text is None:
            results.append({'name': name, 'kind': 'formula-source', 'status': 'COULD_NOT_RUN',
                            'detail': "anchor not found in %s -- the formula may have moved "
                            'or been rewritten; that is itself worth a look' % cand['file']})
            continue
        prev = state.get(name)
        if prev is None:
            results.append({'name': name, 'kind': 'formula-source', 'status': 'BASELINE',
                            'detail': 'first observation, source hash %s recorded. NOTE: '
                            'source-unchanged does NOT mean still-calibrated -- this is a '
                            'weaker signal than the Python half, see module docstring.'
                            % h})
        elif prev.get('hash') != h:
            results.append({'name': name, 'kind': 'formula-source', 'status': 'DRIFT',
                            'detail': 'SOURCE TEXT CHANGED since last look (%s -> %s) -- the '
                            'formula was edited; re-validate against real behaviour, not just '
                            'diff it (why this is tracked: %s)' % (prev.get('hash'), h, cand['why'])})
        else:
            age = (now - prev.get('checked_at_epoch', now)) / 86400.0
            results.append({'name': name, 'kind': 'formula-source', 'status': 'STABLE',
                            'detail': 'source unchanged for %.0f day(s) -- STALENESS CLOCK '
                            'ONLY, not a claim the model is still accurate: EASA\'s point is '
                            'that unchanged code can still drift out of calibration against '
                            'real behaviour. This tool cannot execute the JS to re-check that.'
                            % age})
        new_state[name] = {'hash': h, 'checked_at_epoch': now,
                           'checked_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))}

    return results, new_state


def main(argv):
    if '--selftest' in argv:
        return 0 if run_fixtures() else 1
    if '--list' in argv:
        print('PYTHON TOOLS (%d):' % len(PYTHON_TOOLS))
        for t in PYTHON_TOOLS:
            print('  %-24s %s -- %s' % (t['name'], t['path'], t['why']))
        print('')
        print('FORMULA CANDIDATES (%d, source-hash + staleness only):' % len(FORMULA_CANDIDATES))
        for c in FORMULA_CANDIDATES:
            print('  %-32s %s -- %s' % (c['name'], c['file'], c['why']))
        return 0

    repo = discover_repo(argv)
    if not repo:
        print('COULD NOT RUN: no readable repo found under %s' % ', '.join(REPO_CANDIDATES))
        return 2
    force = '--force' in argv
    state = load_state()
    results, new_state = check_all(repo, state, force=force)
    save_state(new_state)

    drift = [r for r in results if r['status'] == 'DRIFT']
    could_not = [r for r in results if r['status'] == 'COULD_NOT_RUN']
    stable = [r for r in results if r['status'] == 'STABLE']
    baseline = [r for r in results if r['status'] == 'BASELINE']
    skipped = [r for r in results if r['status'] == 'SKIPPED']

    print('HOVER PREDICTIVE DRIFT CHECK -- %d candidate(s): %d checked, %d skipped (not due)'
         % (len(results), len(results) - len(skipped), len(skipped)))
    print('')
    if drift:
        print('*** %d DRIFT FOUND -- read these first ***' % len(drift))
        for r in drift:
            print('  [%s] %s: %s' % (r['kind'], r['name'], r['detail']))
        print('')
    if could_not:
        print('COULD NOT RUN (%d) -- never silently folded into "no drift":' % len(could_not))
        for r in could_not:
            print('  [%s] %s: %s' % (r['kind'], r['name'], r['detail']))
        print('')
    if baseline:
        print('BASELINE, first observation (%d):' % len(baseline))
        for r in baseline:
            print('  [%s] %s: %s' % (r['kind'], r['name'], r['detail']))
        print('')
    if stable:
        print('STABLE, re-confirmed (%d):' % len(stable))
        for r in stable:
            print('  [%s] %s: %s' % (r['kind'], r['name'], r['detail']))
    return 1 if (drift or could_not) else 0


def run_fixtures():
    ok = [0]
    bad = []

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   ' + name)
        else:
            bad.append(name)
            print('  FAIL ' + name)

    ck('a bool leaf is kept as a verdict signal',
       extract_verdict_signature({'a': True}) == [('/a', True)])
    ck('a short label-shaped string is kept',
       extract_verdict_signature({'band': 'ALL HANDS'}) == [('/band', 'ALL HANDS')])
    ck('a number is discarded (raw data, not a verdict)',
       extract_verdict_signature({'count': 42}) == [])
    ck('an ISO date string is discarded even though it is short',
       extract_verdict_signature({'date': '2026-09-22'}) == [])
    ck('a long prose string is discarded',
       extract_verdict_signature({'note': 'this is a much longer sentence of prose text'}) == [])
    ck('nested dicts and lists are walked, path-qualified, sorted by key',
       extract_verdict_signature({'z': {'band': 'HIGH'}, 'a': [{'ok': True}]})
       == [('/a[0]/ok', True), ('/z/band', 'HIGH')])
    ck('signature hashing is order-independent (dict key order does not matter)',
       _hash_signature(extract_verdict_signature({'a': True, 'b': 'LOW'}))
       == _hash_signature(extract_verdict_signature({'b': 'LOW', 'a': True})))
    ck('a changed verdict value changes the hash',
       _hash_signature(extract_verdict_signature({'band': 'LOW'}))
       != _hash_signature(extract_verdict_signature({'band': 'HIGH'})))

    import tempfile
    tmpdir = tempfile.mkdtemp()

    fake_tool = os.path.join(tmpdir, 'fake_tool.py')
    with io.open(fake_tool, 'w', encoding='utf-8') as f:
        f.write('import json,sys\n'
               'print(json.dumps({"band":"LOW" if "--drift" not in sys.argv else "HIGH", '
               '"count": 7}))\n')
    tool = {'name': 'fake', 'path': 'fake_tool.py', 'args': []}
    ok1, sig1, h1, err1 = run_python_tool(tmpdir, tool)
    ck('run_python_tool() runs a real subprocess and extracts a signature',
       ok1 and not err1 and ('/band', 'LOW') in sig1)
    tool2 = {'name': 'fake', 'path': 'fake_tool.py', 'args': ['--drift']}
    ok2, sig2, h2, err2 = run_python_tool(tmpdir, tool2)
    ck('a genuinely different verdict produces a different hash',
       ok2 and h1 != h2)

    missing_tool = {'name': 'missing', 'path': 'does_not_exist.py', 'args': []}
    ok3, _sig3, _h3, err3 = run_python_tool(tmpdir, missing_tool)
    ck('a missing tool path is COULD NOT RUN, not a crash and not clean',
       ok3 is False and err3)

    # FAIL-OPEN CHECK, ADDED 2026-09-22: a tool that CRASHES (raises, exits
    # non-zero with no real JSON) must be COULD NOT RUN, never graded as a
    # verdict whose hash happens to change between runs -- hashing two
    # different tracebacks and calling that "DRIFT" would silently misreport
    # a broken tool as a changed real-world finding.
    crash_tool_path = os.path.join(tmpdir, 'crash_tool.py')
    with io.open(crash_tool_path, 'w', encoding='utf-8') as f:
        f.write('import sys\nraise RuntimeError("boom")\n')
    crash_tool = {'name': 'crash', 'path': 'crash_tool.py', 'args': []}
    ok4, sig4, h4, err4 = run_python_tool(tmpdir, crash_tool)
    ck('a tool that raises an unhandled exception (non-zero exit, unparsable '
       'stdout) is COULD NOT RUN, not graded as a text-mode verdict',
       ok4 is False and sig4 is None and err4)

    crash_text_tool_path = os.path.join(tmpdir, 'crash_text_tool.py')
    with io.open(crash_text_tool_path, 'w', encoding='utf-8') as f:
        f.write('import sys\nsys.exit(1)\n')
    crash_text_tool = {'name': 'crash_text', 'path': 'crash_text_tool.py',
                       'args': [], 'text_mode': True}
    ok5, sig5, h5, err5 = run_python_tool(tmpdir, crash_text_tool)
    ck('the SAME crash shape for a text_mode tool (non-zero exit, ~no '
       'stdout) is ALSO COULD NOT RUN, not silently graded',
       ok5 is False and sig5 is None and err5)

    src_file = os.path.join(tmpdir, 'app.html')
    with io.open(src_file, 'w', encoding='utf-8') as f:
        f.write('var score=100, daysSince=1;\nif(x)score-=20;\n')
    cand = {'name': 'fake_formula', 'file': 'app.html', 'anchor': 'var score=100, daysSince='}
    text, h4 = read_formula_source(tmpdir, cand)
    ck('read_formula_source() finds the anchor and hashes the window',
       text is not None and h4)
    missing_cand = {'name': 'fake_formula2', 'file': 'app.html', 'anchor': 'NOT PRESENT ANYWHERE'}
    text2, h5 = read_formula_source(tmpdir, missing_cand)
    ck('a missing anchor returns (None, None), not an empty-but-clean result',
       text2 is None and h5 is None)

    # KNOWN-BAD CONTROL, conflict-marker sweep, 2026-09-28: a conflicted
    # app file must be CONFLICTED_SENTINEL, never a silent hash of
    # whichever conflict side the anchor window lands in.
    conflicted_file = os.path.join(tmpdir, 'conflicted_app.html')
    with io.open(conflicted_file, 'w', encoding='utf-8') as f:
        f.write('<<<<<<< HEAD\nvar score=100, daysSince=1;\n=======\n'
               'var score=90, daysSince=2;\n>>>>>>> branch\n')
    conf_cand = {'name': 'fk', 'file': 'conflicted_app.html',
                'anchor': 'var score=100, daysSince='}
    text3, h6 = read_formula_source(tmpdir, conf_cand)
    ck('KNOWN-BAD CONTROL: a conflicted file returns the CONFLICTED '
       'sentinel and no hash, never a silent one-side hash',
       text3 == CONFLICTED_SENTINEL and h6 is None)

    state = {}
    results, new_state = check_all(tmpdir, state, force=True)
    py_results = [r for r in results if r['name'] == 'fake_tool_test_not_registered']
    ck('check_all() runs against the REAL registry (PYTHON_TOOLS/FORMULA_CANDIDATES), '
       'not the fixture tool -- confirming it does not crash on a real (if unreachable '
       'here) registry path',
       isinstance(results, list) and len(results) == len(PYTHON_TOOLS) + len(FORMULA_CANDIDATES))

    st = {'x': {'hash': 'abc', 'checked_at_epoch': time.time()}}
    ck('_due() is False for a just-checked entry inside the recheck window',
       _due(st, 'x', force=False) is False)
    ck('_due() is True once RECHECK_DAYS has elapsed',
       _due({'x': {'hash': 'abc', 'checked_at_epoch': time.time() - RECHECK_DAYS * 86400 - 1}},
            'x', force=False) is True)
    ck('_due() is True for an unseen name', _due({}, 'never-seen', force=False) is True)
    ck('_due() ignores the window when force=True',
       _due(st, 'x', force=True) is True)

    state_path = os.path.join(tmpdir, 'state.json')
    save_state({'a': 1}, state_path)
    ck('save_state()/load_state() round-trip', load_state(state_path) == {'a': 1})
    ck('load_state() on a missing file returns {}, not a crash',
       load_state(os.path.join(tmpdir, 'nope.json')) == {})

    print('')
    print('%d ok, %d failed' % (ok[0], len(bad)))
    return not bad


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
