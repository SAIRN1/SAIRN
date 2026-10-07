#!/usr/bin/env python
# OWNER: cc
"""Four syntactic shapes that make a program report a verdict it did not earn.

    python tools/py_guard_check.py                 # tools/, the default scope
    python tools/py_guard_check.py tools tests     # explicit scope
    python tools/py_guard_check.py --selftest      # the arms, reads no subject
    python tools/py_guard_check.py --disable R1    # for the ablation; repeatable
    python tools/py_guard_check.py --quiet
    python tools/py_guard_check.py --help

Exit 0 clean, 1 findings, 2 COULD NOT RUN -- including an argument not
recognised. REPORT ONLY: it writes nothing, proposes nothing, and edits nothing.

Design note, committed BEFORE this file: docs/2026-10-07-cc-py-guard-design-note.md.
It carries the goals, the two rejected alternatives, the three shapes rejected
as NOT mechanically detectable, and the security and test plans. Read it before
adding a rule.

-- IT NEVER EXECUTES WHAT IT READS, AND THAT IS STRUCTURAL ------------------
`ast.parse` builds a tree and evaluates nothing. There is no exec, no eval, no
compile(..., 'exec'), no importlib, no __import__, and no subprocess invocation
of a subject anywhere in this file. ARM 0 of --selftest asserts that against
this file's own source, so the claim is checked on every run rather than
promised in a docstring.

The alternative -- a runtime harness that runs each tool and watches what it
swallows -- is strictly more powerful and was REJECTED ON BLAST RADIUS. 79 of
the 164 ownerless tools/*.py have a detected write site and 85 more cannot be
proved read-only by any static read. On 2026-10-07 an exec-based probe that
disabled a generator's --check to see what it would write overwrote a legal
deadline seed. A checker that must execute its subjects cannot be run safely
on this tree.

-- A FILE IT CANNOT PARSE IS A THIRD STATE ---------------------------------
COULD NOT PARSE is counted and printed separately. It is never folded into
clean (that would be PR 1.11's fail-open) and never into a finding (that would
be an accusation against a file nobody read). The clean line names the number.

-- WHAT A CLEAN RUN MEANS, AND WHAT IT DOES NOT ----------------------------
It means: these four shapes were not found in the files it PARSED. It does NOT
mean the code fails loudly, that exit codes are checked, or that the assertions
test anything. Those are the three shapes the design note rejects as not
mechanically detectable, and this tool cannot answer them.
"""
import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── R1 ──────────────────────────────────────────────────────────────────────
# `check_call` and `check_output` are NOT here, and that is a correction made
# while hand-verifying the first full run rather than a design choice: both
# RAISE on a non-zero exit, so a bare `subprocess.check_call(...)` statement has
# checked the exit code -- by not surviving it. Including them would have made
# correct code a finding, which is the defect class in cross-domain-disciplines
# item 1 (criteria set by what the real data happened to show).
_PROC_CALLS = {
    ('subprocess', 'run'), ('subprocess', 'call'), ('subprocess', 'Popen'),
    ('os', 'system'), ('os', 'popen'), ('os', 'spawnv'), ('os', 'spawnl'),
}


def _checks_its_own_exit(call):
    """`subprocess.run(..., check=True)` raises on non-zero: already checked.

    FOUND BY HAND-VERIFYING THE FIRST RUN. tools/outline.py:80 was flagged and is
    correct code -- `check=True` is the exit-code check, expressed as an
    exception rather than an if. A rule that cannot see that reports a file for
    doing the right thing.
    """
    for kw in call.keywords:
        if kw.arg == 'check':
            v = kw.value
            if isinstance(v, ast.Constant) and v.value:
                return True
    return False

# ── R4(b) ───────────────────────────────────────────────────────────────────
# NARROWED WHILE HAND-VERIFYING THE FIRST FULL RUN, and the thing removed was
# `status`. On this platform `status` is overwhelmingly the name of a STRING
# VERDICT -- 'ok rc=1', 'TIMEOUT', 'UnicodeEncodeError', 'DRIFTED' -- and
# comparing one of those to a string is correct code. Six of the first run's
# eleven R4 flags were that shape, in cp1252_console_sweep.py (3),
# push_retry.py and register_freshness_propose.py. `ret` went with it for the
# same reason: a bare `ret` is as often a string as a code.
#
# What is LEFT is the set of names that are an exit code or nothing:
# rc, retcode, returncode, exit, exitcode, exit_code, exit_status.
_EXIT_NAME = re.compile(r'^(rc|retcode|returncode|exit|exitcode|exit_code'
                        r'|exit_status)$', re.I)

RULES = {
    'R1': ('ignored-exit',
           'a subprocess/os call whose result is DISCARDED -- a bare expression '
           'statement, so the exit code cannot have been read',
           'CANNOT SEE: `rc = subprocess.run(...)` where `rc` is never read. '
           'That needs flow analysis and a wrong answer there is worse than '
           'none.'),
    'R2': ('swallowed-exception',
           'a bare `except:`, or a handler whose body is only `pass` / `...` / '
           'a docstring -- the failure is caught and nothing is done with it',
           'CANNOT SEE: a handler that logs and continues when continuing is '
           'wrong. Logging is a decision; `pass` is a silence.'),
    'R3': ('vacuous-assert',
           'an assertion that cannot fail -- a truthy constant, a non-empty '
           'literal container (the classic `assert (x, "msg")`), or `x == x`',
           'CANNOT SEE: an assertion that still runs and no longer tests '
           'anything. The count holds and the sense is inverted, and no '
           'syntactic test distinguishes that from a correct assertion.'),
    'R4': ('exit-code-from-string',
           'an exit status taken from or compared against a STRING -- '
           '`sys.exit("text")` exits 1 rather than the code named, and a '
           'numeric status compared to a string can never be equal',
           'CANNOT SEE: an exit code read from the wrong element of a '
           'pipeline. That is what the exit_status_attributable hook is for; '
           'it is a shell fact, not a Python one.'),
}


def _dotted(node):
    """('subprocess', 'run') for subprocess.run, (None, 'exit') for exit."""
    if isinstance(node, ast.Attribute):
        base = node.value
        if isinstance(base, ast.Name):
            return (base.id, node.attr)
        return (None, node.attr)
    if isinstance(node, ast.Name):
        return (None, node.id)
    return (None, None)


def _only_statement_is_silence(body):
    """A handler body that does nothing: pass, ..., or a bare docstring."""
    real = [s for s in body
            if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                    and isinstance(s.value.value, str))]
    if not real:
        return bool(body)                       # docstring only
    if len(real) != 1:
        return False
    s = real[0]
    if isinstance(s, ast.Pass):
        return True
    return (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
            and s.value.value is Ellipsis)


def _documented(handler, lines):
    """Is this silence a DECISION or an oversight? A comment is the difference.

    ADDED WHILE HAND-VERIFYING THE FIRST FULL RUN. All 57 of the first run's R2
    flags were typed handlers whose body is only `pass` -- not one bare
    `except:` in 306 files. Many of them carry a comment saying exactly why the
    failure is swallowed, and four of those are in a file I wrote myself. A
    `pass` with a reason above it is a decision somebody can disagree with; a
    `pass` with nothing is a silence.

    THIS IS A TAG AND NOT A FILTER. The documented ones are still counted and
    still reported -- the shape is present either way, and a comment is not
    evidence that the decision is right. What it buys is an ORDER: read the
    undocumented ones first.

    `ast` discards comments, so this reads the physical lines -- the handler's
    own span plus the three above the `except`, which is where this repo puts
    the reason.
    """
    if not lines:
        return False
    lo = max(0, handler.lineno - 4)
    hi = min(len(lines), getattr(handler, 'end_lineno', handler.lineno) or handler.lineno)
    for raw in lines[lo:hi]:
        t = raw.strip()
        if t.startswith('#') and len(t) > 3:
            return True
    return False


def _truthy_constant(node):
    if isinstance(node, ast.Constant):
        try:
            return bool(node.value)
        except Exception:                                      # noqa: BLE001
            return False
    return False


def _nonempty_literal_container(node):
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return bool(node.elts)
    if isinstance(node, ast.Dict):
        return bool(node.keys)
    return False


def _same_source(a, b):
    try:
        return ast.unparse(a) == ast.unparse(b)
    except Exception:                                          # noqa: BLE001
        return False


def _string_shaped(node):
    """A string literal, an f-string, or str()/format() -- never a number."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.Call):
        _, name = _dotted(node.func)
        return name in ('str', 'format')
    return False


def scan_tree(tree, enabled, lines=None):
    """-> [(rule, lineno, evidence)]. Pure: no disk, no execution.

    `lines` is the subject's source split on newlines, used ONLY by R2 and only
    to see COMMENTS, which `ast` discards. Optional so every arm that drives
    scan_tree on a tree alone still works.
    """
    out = []
    for node in ast.walk(tree):

        if 'R1' in enabled and isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if (_dotted(node.value.func) in _PROC_CALLS
                    and not _checks_its_own_exit(node.value)):
                out.append(('R1', node.lineno, ast.unparse(node.value)[:90]))

        if 'R2' in enabled and isinstance(node, ast.ExceptHandler):
            if node.type is None:
                out.append(('R2', node.lineno, 'bare `except:`'))
            elif _only_statement_is_silence(node.body):
                tag = 'UNDOCUMENTED' if not _documented(node, lines) else 'documented'
                out.append(('R2', node.lineno,
                            '%s -- except %s: <nothing>'
                            % (tag, ast.unparse(node.type)[:50])))

        if 'R3' in enabled and isinstance(node, ast.Assert):
            t = node.test
            why = None
            if _truthy_constant(t):
                why = 'assert on a truthy constant'
            elif _nonempty_literal_container(t):
                why = 'assert on a non-empty literal container -- always true'
            elif (isinstance(t, ast.Compare) and len(t.comparators) == 1
                  and _same_source(t.left, t.comparators[0])):
                why = 'assert compares an expression with itself'
            if why:
                out.append(('R3', node.lineno,
                            '%s: %s' % (why, ast.unparse(t)[:70])))

        if 'R4' in enabled and isinstance(node, ast.Call):
            base, name = _dotted(node.func)
            if ((base in (None, 'sys') and name in ('exit', 'SystemExit'))
                    and node.args and _string_shaped(node.args[0])):
                out.append(('R4', node.lineno,
                            '%s() given a STRING -- exits 1, not the code named'
                            % ('%s.%s' % (base, name) if base else name)))

        if 'R4' in enabled and isinstance(node, ast.Compare):
            if len(node.comparators) == 1:
                _, left = _dotted(node.left)
                right = node.comparators[0]
                if (left and _EXIT_NAME.match(left)
                        and isinstance(right, ast.Constant)
                        and isinstance(right.value, str)):
                    out.append(('R4', node.lineno,
                                'exit-shaped name `%s` compared to the STRING %r '
                                '-- never equal' % (left, right.value)))
    return sorted(set(out))


def scan_source(src, enabled):
    """-> (findings, parse_error). A parse failure is a THIRD STATE."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [], 'line %s: %s' % (e.lineno, e.msg)
    except Exception as e:                                     # noqa: BLE001
        return [], str(e)[:120]
    return scan_tree(tree, enabled, src.split(chr(10))), None


def python_files(scopes):
    out = []
    for scope in scopes:
        p = os.path.join(ROOT, scope.replace('/', os.sep))
        if os.path.isfile(p) and p.endswith('.py'):
            out.append(os.path.relpath(p, ROOT))
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = [d for d in dirnames if d != '__pycache__']
            for fn in sorted(filenames):
                if fn.endswith('.py'):
                    out.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
    return sorted(set(out))


# ════════════════════════════════════════════════════════════════════════════
#  SELFTEST -- a planted-bad and a clean example per rule, plus the ablation
# ════════════════════════════════════════════════════════════════════════════
# Both directions per rule, deliberately: a rule that flags EVERYTHING passes a
# planted-bad test on its own. The clean example is what makes the bad one mean
# something.
#
# The ablation is PER ARM and not per exit code -- cross-domain disciplines item
# 12. Disabling R2 must leave R2's planted-bad example unflagged and must leave
# the other three rules' planted-bad examples still flagged.

BAD = {
    'R1': 'import subprocess\nsubprocess.run(["x"])\n',
    'R2': 'try:\n    f()\nexcept ValueError:\n    pass\n',
    'R3': 'def t():\n    assert (1 == 2, "this never fails")\n',
    'R4': 'import sys\nsys.exit("something went wrong")\n',
}
CLEAN = {
    'R1': 'import subprocess\nrc = subprocess.run(["x"]).returncode\nif rc:\n    raise SystemExit(rc)\n',
    'R2': 'try:\n    f()\nexcept ValueError as e:\n    print("could not run: %s" % e)\n    raise SystemExit(2)\n',
    'R3': 'def t():\n    assert 1 == 2, "this can fail"\n',
    'R4': 'import sys\nsys.exit(2)\n',
}
# Shapes a careless rule would flag and must not. Each one is a real pattern
# from this repo rather than an invented counter-example.
NEAR_MISS = {
    'R2-docstring': '"""A docstring mentioning except: pass, which is TEXT about code."""\n',
    'R2-string':    'MSG = "we used to write except: pass here"\n',
    'R2-handled':   'try:\n    f()\nexcept OSError:\n    return 2\n',
    'R1-assigned':  'import subprocess\nr = subprocess.run(["x"])\nif r.returncode:\n    raise SystemExit(1)\n',
    'R1-other':     'import subprocess\nprint(subprocess.run(["x"]).returncode)\n',
    'R3-real':      'def t():\n    assert len(x) == 3, "wrong length"\n',
    'R3-empty':     'def t():\n    assert ()\n',   # an EMPTY tuple is falsy
    'R4-numeric':   'import sys\nrc = 2\nif rc == 2:\n    sys.exit(rc)\n',
    'R4-strvar':    'name = "x"\nif name == "x":\n    pass\n',
    # BOTH OF THESE WERE REAL FALSE POSITIVES ON THE FIRST FULL RUN, found by
    # hand-verifying every flag, and both are correct code.
    'R1-check-true': 'import subprocess\nsubprocess.run(["x"], check=True)\n',
    'R1-check-call': 'import subprocess\nsubprocess.check_call(["x"])\n',
    # The six false positives of the first full run, as arms.
    'R4-status-str': 'status = f()\nif status != "ok":\n    pass\n',
    'R4-status-tmo': 'status = f()\nif status == "TIMEOUT":\n    pass\n',
}

# ── WHAT ARM 0 FORBIDS, AS SYNTAX AND NOT AS SUBSTRINGS ─────────────────────
# The first version of ARM 0 searched this file's text for 'exec(', 'eval(',
# 'compile(' and so on. IT FAILED ON ITS FIRST RUN, on `re.compile(` -- which is
# the regex compiler and has nothing to do with executing code. That is PR 1.2
# inside the tool written to avoid PR 1.2: a substring cannot tell `compile` the
# builtin from `compile` the attribute of another module.
#
# So the arm asks the TREE. A bare call to one of these names, or an import of
# one of these modules, is what it forbids -- `re.compile` has a base and is not
# the builtin, and that distinction is now structural rather than hoped for.
_FORBIDDEN_BARE_CALLS = frozenset(('exec', 'eval', 'compile', '__import__'))
_FORBIDDEN_IMPORTS = frozenset(('importlib', 'subprocess'))
_FORBIDDEN_DOTTED = frozenset((('os', 'system'), ('os', 'popen'),
                               ('os', 'execv'), ('os', 'spawnv')))


def _execution_sites(tree):
    """Every way this file could run code it reads. Syntax, not substrings."""
    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            base, name = _dotted(n.func)
            if base is None and name in _FORBIDDEN_BARE_CALLS:
                hits.append('%s() at line %d' % (name, n.lineno))
            elif (base, name) in _FORBIDDEN_DOTTED:
                hits.append('%s.%s() at line %d' % (base, name, n.lineno))
        elif isinstance(n, ast.Import):
            for al in n.names:
                if al.name.split('.')[0] in _FORBIDDEN_IMPORTS:
                    hits.append('import %s at line %d' % (al.name, n.lineno))
        elif isinstance(n, ast.ImportFrom):
            if (n.module or '').split('.')[0] in _FORBIDDEN_IMPORTS:
                hits.append('from %s import at line %d' % (n.module, n.lineno))
    return sorted(hits)


def selftest():
    arms = []
    ALL = set(RULES)

    # ── ARM 0: the no-execution claim, checked against this file's own source ─
    try:
        me = io.open(os.path.abspath(__file__), encoding='utf-8').read()
    except Exception as e:                                     # noqa: BLE001
        me = None
        arms.append(('ARM 0 could not read its own source: %s' % e, True, False))
    if me is not None:
        arms.append(('ARM 0  this file executes nothing it reads -- no exec, eval, '
                     'compile, __import__, importlib, subprocess or os.system '
                     'CALL SITE in its tree',
                     _execution_sites(ast.parse(me)), []))
        # And the arm must be able to FAIL, or it is the vacuous assertion R3
        # exists to find. Driven on a hand-built source that does execute.
        arms.append(('ARM 0 can fail -- a source that DOES exec is reported',
                     bool(_execution_sites(ast.parse(
                         'import subprocess\nexec("x")\nos.system("y")\n'))),
                     True))

    # ── one planted-bad and one clean example per rule ───────────────────────
    for rid in sorted(RULES):
        found, err = scan_source(BAD[rid], ALL)
        arms.append(('%s planted-bad example IS flagged' % rid,
                     (err, sorted({f[0] for f in found})), (None, [rid])))
        found, err = scan_source(CLEAN[rid], ALL)
        arms.append(('%s clean example is NOT flagged' % rid,
                     (err, sorted({f[0] for f in found})), (None, [])))

    # ── ABLATION, per rule and per ARM ───────────────────────────────────────
    for rid in sorted(RULES):
        enabled = ALL - {rid}
        found, err = scan_source(BAD[rid], enabled)
        arms.append(('ABLATION %s disabled -> its planted-bad goes UNFLAGGED' % rid,
                     (err, sorted({f[0] for f in found})), (None, [])))
        others = sorted(ALL - {rid})
        still = []
        for oid in others:
            f2, e2 = scan_source(BAD[oid], enabled)
            still.append(sorted({x[0] for x in f2}) == [oid] and e2 is None)
        arms.append(('ABLATION %s disabled -> the other %d rules STILL fire'
                     % (rid, len(others)), still, [True] * len(others)))

    # ── near misses: shapes a careless rule would flag ───────────────────────
    for name, src in sorted(NEAR_MISS.items()):
        found, err = scan_source(src, ALL)
        arms.append(('NEAR MISS %-14s is not flagged' % name,
                     (err, sorted({f[0] for f in found})), (None, [])))

    # ── the R2 TAG, both directions. A comment is the difference between a
    # decision and a silence, and the tag decides reading ORDER rather than
    # whether the shape is reported.
    f1, _ = scan_source('try:\n    f()\nexcept OSError:\n    pass\n', ALL)
    arms.append(('R2 an UNDOCUMENTED silence is tagged UNDOCUMENTED',
                 [('UNDOCUMENTED' in e) for _, _, e in f1], [True]))
    f2, _ = scan_source('try:\n    f()\nexcept OSError:\n    # absent is the same as empty here, and that is the whole point\n    pass\n', ALL)
    arms.append(('R2 a silence with a REASON above it is still reported, tagged '
                 'documented',
                 [(r, 'UNDOCUMENTED' in e) for r, _, e in f2], [('R2', False)]))

    # ── a parse failure is a THIRD STATE, not clean and not a finding ────────
    found, err = scan_source('def broken(:\n', ALL)
    arms.append(('a file that will not parse is COULD NOT PARSE, not clean',
                 (found, err is not None), ([], True)))

    # ── the argv guard ───────────────────────────────────────────────────────
    arms.append(('a bare run means the default scope, not a refusal',
                 classify([])[0], 'scan'))
    arms.append(('an unknown flag is refused',
                 classify(['--bogus']), ('unknown', '--bogus')))
    arms.append(('--disable takes a rule id and nothing else',
                 classify(['--disable', 'R9']), ('badrule', 'R9')))

    lines, passed = [], 0
    for name, got, want in arms:
        ok = got == want
        passed += ok
        lines.append('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
        if not ok:
            lines.append('       wanted %r' % (want,))
            lines.append('       got    %r' % (got,))
    return passed, len(arms) - passed, lines


# ════════════════════════════════════════════════════════════════════════════
KNOWN_FLAGS = ('--selftest', '--quiet', '--help', '-h', '--disable')


def classify(argv):
    """-> ('scan', scopes, disabled) | ('selftest',) | ('help',)
           | ('unknown', arg) | ('badrule', arg). Pure.

    An unrecognised flag exits 2 and does nothing -- this batch's Rule B. A
    POSITIONAL is a scope and is allowed, because the tool takes paths.
    """
    scopes, disabled, i = [], set(), 0
    while i < len(argv):
        a = argv[i]
        if a == '--disable':
            if i + 1 >= len(argv):
                return ('badrule', '<missing>')
            rid = argv[i + 1].upper()
            if rid not in RULES:
                return ('badrule', argv[i + 1])
            disabled.add(rid)
            i += 2
            continue
        if a in ('--help', '-h'):
            return ('help',)
        if a == '--selftest':
            return ('selftest',)
        if a == '--quiet':
            i += 1
            continue
        if a.startswith('-'):
            return ('unknown', a)
        scopes.append(a)
        i += 1
    return ('scan', scopes or ['tools'], disabled)


def main(argv):
    mode = classify(argv)
    if mode[0] == 'unknown':
        print('COULD NOT RUN -- argument not recognised: %s' % mode[1])
        print('Nothing was read. Recognised: %s' % ', '.join(KNOWN_FLAGS))
        return 2
    if mode[0] == 'badrule':
        print('COULD NOT RUN -- --disable wants a rule id, got %r. Known: %s'
              % (mode[1], ', '.join(sorted(RULES))))
        return 2
    if mode[0] == 'help':
        # ENCODE-SAFE, and this is a defect this tool had. On a cp1252 console
        # `print(__doc__)` raised UnicodeEncodeError and --help exited 1 -- the
        # class tools/cp1252_console_sweep.py exists for, in a brand new file,
        # found by its own CLI probe asserting `--help exits 0`. The docstring
        # is now ASCII; this belt is here because the docstring is not the only
        # thing a later edit could put through this print.
        enc = (getattr(sys.stdout, 'encoding', None) or 'ascii')
        text = __doc__.rstrip()
        sys.stdout.write(text.encode(enc, 'replace').decode(enc) + chr(10))
        return 0
    if mode[0] == 'selftest':
        p, f, lines = selftest()
        print('PY GUARD selftest: %d/%d arm(s) pass' % (p, p + f))
        for ln in lines:
            print(ln)
        return 1 if f else 0

    _, scopes, disabled = mode
    enabled = set(RULES) - disabled
    quiet = '--quiet' in argv

    # THE SELFTEST RUNS ON THE DEFAULT PATH AND ITS RESULT IS PRINTED, because a
    # self-test that only runs under a flag is a control with a shorter name --
    # tools/checker_selftest_check.py's own words. If it fails, this run reports
    # COULD NOT RUN rather than a clean scan: a checker that cannot prove it
    # still works has not measured anything.
    sp, sf, slines = selftest()
    print('criteria lock: %d/%d arm(s) pass, on hand-built sources only'
          % (sp, sp + sf))
    if sf:
        print('COULD NOT RUN -- the criteria lock FAILED, so this run proves '
              'nothing about any subject. Nothing was scanned.')
        for ln in slines:
            if ln.strip().startswith('FAIL') or ln.strip().startswith('wanted') \
                    or ln.strip().startswith('got'):
                print(ln)
        return 2

    files = python_files(scopes)
    if not files:
        print('COULD NOT RUN -- no .py file under %s. An empty population '
              'reports clean and would mean nothing.' % ', '.join(scopes))
        return 2

    findings, unparsed = [], []
    for rel in files:
        try:
            src = io.open(os.path.join(ROOT, rel), encoding='utf-8',
                          errors='strict').read()
        except Exception as e:                                 # noqa: BLE001
            unparsed.append((rel, 'unreadable: %s' % e))
            continue
        got, err = scan_source(src, enabled)
        if err:
            unparsed.append((rel, err))
            continue
        for rid, line, ev in got:
            findings.append((rel, line, rid, ev))

    if disabled:
        print('ABLATED: %s disabled by --disable. This run does NOT cover '
              '%s.' % (', '.join(sorted(disabled)),
                       ', '.join(RULES[r][0] for r in sorted(disabled))))

    print('read %d python file(s) under %s' % (len(files), ', '.join(scopes)))
    print('rules active: %s'
          % ', '.join('%s %s' % (r, RULES[r][0]) for r in sorted(enabled)))

    if unparsed:
        print('')
        print('COULD NOT PARSE %d file(s) -- a THIRD STATE, counted here and '
              'folded into neither clean nor findings:' % len(unparsed))
        for rel, why in unparsed:
            print('  %-54s %s' % (rel, why))

    if findings:
        print('')
        by = {}
        for rel, line, rid, ev in findings:
            by.setdefault(rid, []).append((rel, line, ev))
        for rid in sorted(by):
            print('%s %s -- %d' % (rid, RULES[rid][0], len(by[rid])))
            print('   %s' % RULES[rid][1])
            print('   %s' % RULES[rid][2])
            if not quiet:
                for rel, line, ev in sorted(by[rid]):
                    print('     %s:%d  %s' % (rel, line, ev))
        print('')
        print('%d finding(s) in %d of %d file(s). REPORT ONLY -- nothing was '
              'written and nothing is proposed.'
              % (len(findings), len({f[0] for f in findings}), len(files)))
        print('EVERY FLAG IS A CANDIDATE, NOT A VERDICT. Each rule prints what '
              'it cannot see, above; read the line before acting on it.')
        return 1

    print('')
    print('CLEAN -- none of the %d shape(s) found in the %d file(s) PARSED.'
          % (len(enabled), len(files) - len(unparsed)))
    print('That is NOT a claim that this code fails loudly, that its exit codes '
          'are checked, or that its assertions test anything. See section 8 of '
          'docs/2026-10-07-cc-py-guard-design-note.md.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
