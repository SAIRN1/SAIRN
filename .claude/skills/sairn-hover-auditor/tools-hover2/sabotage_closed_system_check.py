#!/usr/bin/env python
"""sabotage_closed_system_check.py (hover2's own build, item 3 of the
2026-09-23 standing queue) -- a cold second look at the tools hover2 built
tonight, asking one narrow question about each: is its own --selftest
actually ISOLATED (discipline #5, "isolated validation -- the deep check
runs with the subject NOT trusted"), or does it secretly validate itself
against its own live output (a closed system, "calibrating a scale by
weighing things with it")?

WHY "closed system" AND NOT "unit test coverage". Every tool below already
has a --selftest and every one currently reports green. That is not the
question this asks. The question is narrower and structural: when a
--selftest claims something passed, did it prove that against data the
tool did not produce and cannot see coming -- or did it prove that against
its OWN real log / its OWN real output, making the test and the thing
tested the same closed loop? A closed loop can be green forever and still
be worthless, the same failure discipline #6 names for two people running
the same checker: agreement is not evidence when both sides share the same
blind spot.

METHOD, STATIC ONLY, DELIBERATELY. The obvious dynamic proof would be: hide
the tool's real data file, rerun --selftest, confirm the result is
unchanged. That was considered and rejected here on purpose -- for
hover_log.py and hover_self_health.py the "real data file" IS
hover-audit-log.jsonl, this role's own append-only, hash-chained record.
Moving it aside, even under try/finally, is a hard-to-reverse operation on
the one file this whole role exists to keep tamper-evident, for a check
that a purely static read can already answer. So: this tool reads source,
never moves or truncates anything, and says so as a named limitation
rather than silently being weaker than it looks.

WHAT COUNTS AS A "REAL-DATA TOUCH" IN A SELFTEST BODY. A reference, inside
the extracted selftest function, to: the module's own LOG_PATH constant
used un-redirected; a bare open()/read of a path that is not built from
tempfile.mkdtemp()/NamedTemporaryFile(); or a live network/transport call
not going through a stub/mock/fake object. A touch is DISCLOSED if a
comment within DISCLOSURE_WINDOW lines above the touching line contains one
of DISCLOSURE_MARKERS (case-insensitive) -- i.e. the tool's own author
already said out loud "this arm is live, not a fixture", the same
convention hover_self_health.py's own selftest already uses for its one
live arm. UNDISCLOSED means the touch exists and nothing nearby admits it.

VERDICT PER TOOL:
  NO_SELFTEST        -- no --selftest flag in this file at all. Cannot be a
                         closed system in the sense checked here because
                         there is nothing self-referential to be closed --
                         but there is also no self-check whatsoever, which
                         is its own, plainer finding, reported as such.
  ISOLATED            -- --selftest exists, ran clean just now (live, this
                         run), and its body has zero real-data touches.
  DISCLOSED_LIVE(n)   -- n real-data touches, all disclosed nearby.
  UNDISCLOSED_LIVE(n) -- at least one real-data touch with no disclosure
                         marker nearby. FLAGGED.
  SELFTEST_FAILED     -- --selftest exists but did not exit 0 just now,
                         regardless of the static verdict -- reported first,
                         ahead of the closed-system question, because a
                         failing check is the louder problem.

WHAT THIS CANNOT SEE, said here rather than discovered later: a real-data
touch disclosed by a comment that is simply lying about being disclosed
(the marker is present but the arm is not actually what the comment claims
it is) -- this greps for the marker, it does not verify the claim behind
it. And it cannot see a selftest that is isolated in body but whose
FIXTURES were authored by looking at real output first (discipline #1) --
that is a documentation-provenance question this cannot answer from source
alone.

    python sabotage_closed_system_check.py
    python sabotage_closed_system_check.py --json
    python sabotage_closed_system_check.py --fixtures
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

DISCLOSURE_MARKERS = [
    'real self-log', 'not a fixture', 'not simulated', 'real incident shape',
    'mechanical proof', 'real self-log data', 'against real', 'live, not',
    'no fixture', 'no network involved', 'zero requests were actually sent',
]
DISCLOSURE_WINDOW = 6

# The five tools built tonight (2026-09-23), per the standing-queue handoff.
# hover_tool_index.py carries no --selftest of its own -- included anyway so
# that absence is reported, not silently skipped.
TARGETS = [
    {'file': 'hover_log.py', 'label': 'staleness guard + --tier-claim'},
    {'file': 'hover_tier0_exec.py', 'label': 'Tier 0'},
    {'file': 'hover_tier1_live.py', 'label': 'Tier 1'},
    {'file': 'hover_tool_index.py', 'label': 'hover_tool_index'},
    {'file': 'hover_self_health.py', 'label': 'hover_self_health'},
]
# NO HARDCODED 'flag' FIELD ANY MORE. The first version of this list
# hand-set hover_tool_index.py's flag to None, from an assumption made off
# `python hover_tool_index.py --help` (which these argparse-free scripts do
# not special-case, so it silently ran default mode) rather than from
# actually testing `--selftest`. That file has ALWAYS had a real 8-arm
# selftest -- the hand-set flag was simply wrong and this tool reported
# NO_SELFTEST on a file that had one, for one full session, uncaught
# because nothing re-derived the flag from the source. detect_selftest_flag()
# below replaces the hardcoded field with the same auto-detection
# extract_selftest_body() already does internally, so this class of error
# cannot recur silently.


def _extract_def_body(lines, def_name):
    start = None
    for i, line in enumerate(lines):
        if re.match(r'^def\s+' + re.escape(def_name) + r'\s*\(', line):
            start = i
            break
    if start is None:
        return None, []
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r'^(def|class)\s+\S', lines[j]):
            end = j
            break
    return start + 1, lines[start:end]


def extract_selftest_body(src):
    """Return (start_line_1based, lines[]) for the function that actually
    runs on --selftest, or (None, []) if none can be found.

    Prefers a literal 'def selftest(' (hover_log.py, hover_tier0_exec.py,
    hover_tier1_live.py all use this name directly). FALLS BACK to
    resolving whatever function name the '--selftest' dispatch branch
    itself calls -- hover_self_health.py inlines the check into main() and
    dispatches to run_fixtures(), a different name, so a scan that only
    looks for 'def selftest(' silently reports NO_SELFTEST on a file that
    has one. Found by running this tool against that real file, not by
    inspection."""
    lines = src.splitlines()
    start, body = _extract_def_body(lines, 'selftest')
    if start is not None:
        return start, body

    for i, line in enumerate(lines):
        if re.search(r"['\"]--selftest['\"]\s+in\s+argv|args\.selftest\b", line):
            for j in range(i, min(i + 4, len(lines))):
                m = re.search(r'\b([a-zA-Z_]\w*)\s*\(', lines[j])
                if m and m.group(1) not in ('if', 'return', 'print'):
                    return _extract_def_body(lines, m.group(1))
    return None, []


def find_log_path_const(src):
    m = re.search(r"^LOG_PATH\s*=", src, re.M)
    return m is not None


def _in_string_literal(line, pos):
    """Crude but adequate for this codebase's style: is `pos` inside a
    quoted string on this single line? Needed because this codebase's own
    convention names the function under test in the ck() PROSE description
    ("read_all() report a problem...") right next to the real assertion --
    a name match there is not a call site. Caught live: both
    hover_log.py's and hover_self_health.py's selftests describe read_all
    / read_log this way, and the first version of this scan flagged the
    prose, not the code."""
    in_s, quote = False, ''
    i = 0
    while i < pos and i < len(line):
        c = line[i]
        if in_s:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                in_s = False
        else:
            if c in ('"', "'"):
                in_s, quote = True, c
        i += 1
    return in_s


def is_tempfile_guarded(lines, idx, window=8):
    """True if a tempfile/NamedTemporaryFile/mkdtemp construction appears
    within `window` lines above idx, OR idx sits inside a class body whose
    name looks like a fake/stub/mock (scanned by INDENTATION, not a fixed
    line window -- a stub class can be declared many lines before its
    methods are used, and a fixed window missed hover_tier1_live.py's
    _StubHttpMod.fetch_json, a method DEFINITION mistaken for a real call
    on the first run of this tool)."""
    lo = max(0, idx - window)
    for k in range(lo, idx):
        if re.search(r'tempfile|mkdtemp|NamedTemporaryFile', lines[k]):
            return True

    def indent_of(s):
        return len(s) - len(s.lstrip())

    this_indent = indent_of(lines[idx])
    for k in range(idx - 1, -1, -1):
        line = lines[k]
        if not line.strip():
            continue
        ind = indent_of(line)
        if ind < this_indent:
            if re.match(r'\s*class\s+(_Fake|_Stub|Mock)\w*', line):
                return True
            if re.match(r'\s*class\s+\S', line):
                return False
            this_indent = ind
    return False


def has_disclosure(lines, idx, window=DISCLOSURE_WINDOW):
    """Looks BOTH directions from idx. This codebase's real convention puts
    the disclosure prose ("REAL self-log, not a fixture") on the ck()
    description line that FOLLOWS the actual call
    (real_report = run_report() / ck('run_report() runs cleanly against
    THIS clone\\'s REAL self-log...')) at least as often as it precedes it
    -- a backward-only window reported hover_self_health.py's own honestly
    disclosed arm as undisclosed on this tool's first correct-count run."""
    lo = max(0, idx - window)
    hi = min(len(lines), idx + window + 1)
    blob = '\n'.join(lines[lo:hi]).lower()
    return any(m in blob for m in DISCLOSURE_MARKERS)


def find_indirect_log_path_callees(src):
    """Functions defined elsewhere in this module whose OWN body reads
    LOG_PATH -- so a selftest that calls them with no override (e.g.
    run_report()) touches real data one call deep, invisibly to a scan
    that only greps the selftest body's own text for 'LOG_PATH'. This is
    exactly how hover_self_health.py's disclosed live arm (run_report(),
    default log_path=None -> LOG_PATH) was missed on this tool's own first
    live run -- found by running it, not by inspection."""
    lines = src.splitlines()
    names = set()
    cur_name, cur_start = None, None
    for i, line in enumerate(lines + ['def __end__():']):
        m = re.match(r'^def\s+(\w+)\s*\(', line)
        if m:
            if cur_name is not None:
                body = lines[cur_start:i]
                if any(re.search(r'\bLOG_PATH\b', b) for b in body):
                    names.add(cur_name)
            cur_name, cur_start = m.group(1), i + 1
    return names


def analyze_body(body_lines, has_log_path_const, indirect_callees=frozenset()):
    """Return list of (line_offset, text, disclosed:bool) for each
    real-data touch found in the selftest body, direct or one call deep."""
    touches = []
    for i, line in enumerate(body_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        real_ref = False
        if has_log_path_const and re.search(r'\bLOG_PATH\b', line) and not is_tempfile_guarded(body_lines, i):
            real_ref = True
        if re.search(r"\bopen\(\s*['\"]", line) and not is_tempfile_guarded(body_lines, i):
            # a hardcoded string path literal opened directly
            real_ref = True
        if re.match(r'\s*def\s', line):
            pass  # a method/function DEFINITION is not a live call site
        elif re.search(r'\bfetch_json\(|requests\.(get|post)\(|urllib', line) and not is_tempfile_guarded(body_lines, i):
            real_ref = True
        if not re.match(r'\s*def\s', line):
            # a def line is never a call site here either -- without this
            # guard, a selftest whose OWN body touches LOG_PATH lands in
            # indirect_callees and 'def selftest():' matches its own name
            # (the real hover_log.py line-760 false positive, 2026-09-30)
            for callee in indirect_callees:
                # ONLY a bare, zero-argument, CODE (not prose) call actually
                # exercises the LOG_PATH default. append_entry(..., path=path)
                # and read_all(path) pass an explicit override; ck('read_all()
                # report a problem...') just NAMES the function in a test
                # description string. Caught live, both false-positive shapes:
                # 5 hits from the first (hover_log.py) and 2 from the second
                # (hover_self_health.py's own ck() prose).
                for m in re.finditer(r'\b' + re.escape(callee) + r'\s*\(\s*\)', line):
                    if not _in_string_literal(line, m.start()) and not is_tempfile_guarded(body_lines, i):
                        real_ref = True
        if real_ref:
            touches.append((i, stripped, has_disclosure(body_lines, i)))
    return touches


def run_selftest_live(repo_dir, filename, flag):
    path = os.path.join(repo_dir, filename)
    try:
        p = subprocess.run([sys.executable, path, flag], cwd=repo_dir,
                            capture_output=True, text=True, timeout=120)
    except Exception as e:
        return None, 'could not run: %r' % (e,)
    ok = p.returncode == 0
    tail = (p.stdout or '').strip().splitlines()
    last = tail[-1] if tail else ''
    return ok, last


def detect_selftest_flag(src):
    """Is there ANY evidence this file responds to --selftest -- argparse
    add_argument, or the bare 'in argv' dispatch shape hover_self_health.py
    and hover_tool_index.py both use? Checked against the source text
    directly, never hand-asserted per file."""
    return bool(re.search(r"add_argument\(\s*['\"]--selftest['\"]|['\"]--selftest['\"]\s+in\s+argv", src))


def check_one(repo_dir, target):
    fname = target['file']
    fpath = os.path.join(repo_dir, fname)
    result = {'file': fname, 'label': target['label']}
    if not os.path.isfile(fpath):
        result['verdict'] = 'FILE_NOT_FOUND'
        return result
    src = io.open(fpath, encoding='utf-8').read()

    if not detect_selftest_flag(src):
        result['verdict'] = 'NO_SELFTEST'
        result['detail'] = 'no --selftest dispatch found in source (argparse or bare-argv shape) -- structurally not a closed system (nothing self-referential runs), but also not self-checked at all'
        return result

    start_line, body = extract_selftest_body(src)
    if start_line is None:
        result['verdict'] = 'NO_SELFTEST'
        result['detail'] = '--selftest flag exists in argparse but no def selftest() found by this scan'
        return result

    ok, last_line = run_selftest_live(repo_dir, fname, '--selftest')
    result['ran_now'] = ok
    result['last_line'] = last_line
    if ok is not True:
        result['verdict'] = 'SELFTEST_FAILED'
        return result

    has_log_const = find_log_path_const(src)
    indirect = find_indirect_log_path_callees(src) if has_log_const else frozenset()
    touches = analyze_body(body, has_log_const, indirect)
    undisclosed = [t for t in touches if not t[2]]
    disclosed = [t for t in touches if t[2]]

    result['real_data_touches'] = [
        {'line': start_line + i, 'text': text, 'disclosed': d}
        for (i, text, d) in touches
    ]
    if undisclosed:
        result['verdict'] = 'UNDISCLOSED_LIVE(%d)' % len(undisclosed)
    elif disclosed:
        result['verdict'] = 'DISCLOSED_LIVE(%d)' % len(disclosed)
    else:
        result['verdict'] = 'ISOLATED'
    return result


# ---------------------------------------------------------------- fixtures
FIXTURE_ISOLATED = '''
def selftest():
    import tempfile
    tmp = tempfile.mkdtemp()
    p = os.path.join(tmp, "x.json")
    with open(p, "w") as f:
        f.write("{}")
    return True
'''.strip('\n')

FIXTURE_UNDISCLOSED = '''
def selftest():
    with open(LOG_PATH) as f:
        data = f.read()
    return True
'''.strip('\n')

FIXTURE_DISCLOSED = '''
def selftest():
    # REAL self-log, not a fixture -- deliberately runs against live data
    with open(LOG_PATH) as f:
        data = f.read()
    return True
'''.strip('\n')

# real shape: hover_self_health.py inlines the dispatch in main() and calls
# a differently-named function -- 'def selftest(' alone must not find this.
FIXTURE_INLINE_DISPATCH = '''
def main(argv):
    if '--selftest' in argv:
        return 0 if run_fixtures() else 1
    return 0


def run_fixtures():
    import tempfile
    tmp = tempfile.mkdtemp()
    return True
'''.strip('\n')

# real shape: hover_tier1_live.py defines fetch_json as a STUB METHOD many
# lines below the class line -- must not be flagged as a live call.
FIXTURE_STUB_METHOD = '''
def selftest():
    class _StubHttpMod:
        def __init__(self, a):
            self.a = a

        def fetch_json(self, endpoint, timeout=25, method='POST'):
            return (200, {})
    s = _StubHttpMod(1)
    return True
'''.strip('\n')

# real shape: hover_self_health.py's run_report(log_path=None) reads
# LOG_PATH internally when called bare -- must be caught one call deep.
FIXTURE_INDIRECT_CALL = '''
LOG_PATH = "/real/self-log.jsonl"


def run_report(log_path=None):
    path = log_path or LOG_PATH
    return open(path).read()


def selftest():
    # REAL self-log, not a fixture
    r = run_report()
    tmp_path = "/tmp/scratch.jsonl"
    r2 = run_report(tmp_path)
    ck('run_report() described in prose only, not actually called here', True)
    return True
'''.strip('\n')

# real shape, caught live 2026-09-30 on hover_log.py: a selftest whose OWN
# body touches LOG_PATH puts its own name into indirect_callees, and its own
# 'def selftest():' line then matches the zero-arg call regex -- a function
# DEFINITION self-flagged as a live call site, the same def-vs-call mistake
# the network branch already guards against but the callee loop did not.
FIXTURE_SELF_NAMED_DEF = '''
LOG_PATH = "/real/self-log.jsonl"


def selftest():
    # LIVE ARM, not a fixture: reads the real self-log line count
    with open(LOG_PATH) as f:
        n = sum(1 for _ in f)
    return True
'''.strip('\n')

# real shape: the disclosure comment sits AFTER the call, on the ck() line
# describing it, not before -- hover_self_health.py's own honestly
# disclosed arm is written this way.
FIXTURE_FORWARD_DISCLOSURE = '''
LOG_PATH = "/real/self-log.jsonl"


def run_report(log_path=None):
    path = log_path or LOG_PATH
    return open(path).read()


def selftest():
    r = run_report()
    ck("run_report() runs against THIS clone's REAL self-log, not a fixture", True)
    return True
'''.strip('\n')


def run_fixtures():
    bad = []

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    start, body = extract_selftest_body(FIXTURE_ISOLATED)
    touches = analyze_body(body, has_log_path_const=True)
    ck('isolated fixture (tempfile-only) reports zero real-data touches',
       len(touches) == 0)

    start, body = extract_selftest_body(FIXTURE_UNDISCLOSED)
    touches = analyze_body(body, has_log_path_const=True)
    ck('undisclosed LOG_PATH open() is detected as a real-data touch',
       len(touches) == 1 and touches[0][2] is False)

    start, body = extract_selftest_body(FIXTURE_DISCLOSED)
    touches = analyze_body(body, has_log_path_const=True)
    ck('the same touch, with a disclosure comment nearby, is marked disclosed',
       len(touches) == 1 and touches[0][2] is True)

    start, body = extract_selftest_body('def not_selftest():\n    pass\n')
    ck('a file with no def selftest() is reported as None, not a false positive',
       start is None)

    start, body = extract_selftest_body(FIXTURE_INLINE_DISPATCH)
    ck('inline --selftest dispatch to a differently-named function (the real '
       'hover_self_health.py shape) is still resolved, not reported NO_SELFTEST',
       start is not None and any('run_fixtures' not in l and 'tempfile' in l for l in body))

    start, body = extract_selftest_body(FIXTURE_STUB_METHOD)
    touches = analyze_body(body, has_log_path_const=False)
    ck('a stub class\'s fetch_json METHOD DEFINITION is not flagged as a '
       'live call site (the real hover_tier1_live.py false positive)',
       len(touches) == 0)

    indirect = find_indirect_log_path_callees(FIXTURE_INDIRECT_CALL)
    start, body = extract_selftest_body(FIXTURE_INDIRECT_CALL)
    touches = analyze_body(body, has_log_path_const=True, indirect_callees=indirect)
    ck('an indirect LOG_PATH touch through a BARE zero-arg call '
       '(run_report(), the real hover_self_health.py shape) is caught one '
       'call deep and its disclosure comment honoured; a call WITH an '
       'explicit override argument (real hover_log.py false positive) AND '
       'a PROSE mention of the same call inside a ck() description string '
       '(real hover_self_health.py false positive) are both correctly '
       'excluded -- exactly one real touch, not three',
       len(touches) == 1 and touches[0][2] is True)

    indirect_self = find_indirect_log_path_callees(FIXTURE_SELF_NAMED_DEF)
    start, body = extract_selftest_body(FIXTURE_SELF_NAMED_DEF)
    touches = analyze_body(body, has_log_path_const=True, indirect_callees=indirect_self)
    ck('a selftest whose own name lands in indirect_callees does NOT flag '
       'its own def line as a call site (the real hover_log.py line-760 '
       'false positive) -- exactly one touch, the disclosed LOG_PATH read',
       len(touches) == 1 and touches[0][2] is True)

    indirect_fwd = find_indirect_log_path_callees(FIXTURE_FORWARD_DISCLOSURE)
    start, body = extract_selftest_body(FIXTURE_FORWARD_DISCLOSURE)
    touches = analyze_body(body, has_log_path_const=True, indirect_callees=indirect_fwd)
    ck('a disclosure comment on the ck() line AFTER the call (the real '
       'hover_self_health.py shape) is honoured by a forward-looking '
       'window, not just a backward one',
       len(touches) == 1 and touches[0][2] is True)

    ck('detect_selftest_flag() finds the bare-argv dispatch shape '
       '(hover_self_health.py AND hover_tool_index.py\'s real shape) -- '
       'the exact case a hand-set flag=None got wrong for a full session',
       detect_selftest_flag("def main(argv):\n    if '--selftest' in argv:\n        return 0\n"))
    ck('detect_selftest_flag() finds the argparse shape (hover_log.py, '
       'hover_tier0_exec.py, hover_tier1_live.py\'s real shape)',
       detect_selftest_flag("ap.add_argument('--selftest', action='store_true')\n"))
    ck('detect_selftest_flag() correctly reports False on a file with '
       'neither shape, not a false positive',
       not detect_selftest_flag("def main(argv):\n    return 0\n"))

    if bad:
        print('%d of 12 fixture(s) failed -- refusing to judge real tools' % len(bad))
        return 2
    print('OK -- 12/12 fixtures passed')
    return 0


def main(argv):
    if '--fixtures' in argv:
        return run_fixtures()

    # discipline #1: lock fixtures before judging anything real
    fx_buf = io.StringIO()
    _stdout = sys.stdout
    sys.stdout = fx_buf
    try:
        fx_rc = run_fixtures()
    finally:
        sys.stdout = _stdout
    if fx_rc != 0:
        print(fx_buf.getvalue())
        print('FIXTURES FAILED -- nothing real was judged')
        return 2

    as_json = '--json' in argv
    results = [check_one(HERE, t) for t in TARGETS]

    if as_json:
        print(json.dumps(results, indent=2))
        flagged = any('UNDISCLOSED' in r.get('verdict', '') or
                       r.get('verdict') in ('SELFTEST_FAILED', 'FILE_NOT_FOUND')
                       for r in results)
        return 1 if flagged else 0

    print('SABOTAGE CLOSED-SYSTEM CHECK -- %d tool(s), static source read + '
          'live selftest rerun, no real files moved' % len(results))
    for r in results:
        print('  %-14s %-30s %s' % (r['verdict'], r['file'], r.get('label', '')))
        if r.get('detail'):
            print('      %s' % r['detail'])
        if r.get('last_line'):
            print('      selftest tail: %s' % r['last_line'])
        for t in r.get('real_data_touches', []):
            tag = 'disclosed' if t['disclosed'] else 'UNDISCLOSED'
            print('      [%s] line %d: %s' % (tag, t['line'], t['text']))

    n_isolated = sum(1 for r in results if r['verdict'] == 'ISOLATED')
    n_disclosed = sum(1 for r in results if r['verdict'].startswith('DISCLOSED_LIVE'))
    n_undisclosed = sum(1 for r in results if r['verdict'].startswith('UNDISCLOSED_LIVE'))
    n_none = sum(1 for r in results if r['verdict'] == 'NO_SELFTEST')
    n_failed = sum(1 for r in results if r['verdict'] in ('SELFTEST_FAILED', 'FILE_NOT_FOUND'))
    print()
    print('SUMMARY: %d isolated, %d disclosed-live, %d UNDISCLOSED-live, '
          '%d no-selftest, %d failed/missing' %
          (n_isolated, n_disclosed, n_undisclosed, n_none, n_failed))
    print('LIMITATION, STATED NOT HIDDEN: static read only -- this does not '
          'prove isolation by actually hiding the real log file and '
          're-running, because that file is the tamper-evident record this '
          'role exists to keep, and a static source read already answers '
          'the question this check asks without touching it.')

    return 1 if (n_undisclosed or n_failed) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
