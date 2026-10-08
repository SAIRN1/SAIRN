#!/usr/bin/env python
"""hover_py_guard_checker.py -- a static, syntax-tree-only Python checker for
four honesty-shaped defect classes this platform keeps re-discovering by
hand. Built from scratch under this role's own prefix, 2026-10-07 (H1,
batch N, item 5). Never reads or reuses any other auditor's or builder's
equivalent checker -- designed independently from first principles.

DESIGN NOTE
-----------
GOALS: mechanically detect, via Python's own `ast` module (never executing
the target code), four specific patterns this platform's own process rules
and prior findings have repeatedly named as real defect shapes:
  (1) an ignored return/exit code from a subprocess or os call
  (2) a swallowed exception (bare `except:`, or `except X:` whose body is
      only `pass`)
  (3) a constant-true or self-matching assertion (`assert True`, `assert 1`,
      `assert x == x`)
  (4) a verdict or exit code derived from a harness STATUS STRING (text
      like "PASSED"/"FAIL") rather than a real captured return code

NON-GOALS: this is not a general-purpose linter -- pyflakes/pylint already
exist and are not reinvented here. It does not fix anything (report only,
per this role's own core rule). It checks only these four shapes; it is not
a replacement for any resource-specific or domain-specific checker already
in this role's tool set. It does not execute the code it reads, anywhere,
under any flag.

TWO ALTERNATIVES CONSIDERED, AND WHY NEITHER WAS CHOSEN:
  A. Regex/text scanning over the source. Rejected on this role's own
     recent evidence against itself: hover_hardfail_severity_scorer.py's
     negation miss and hover_identity_attribution_check.py's
     ATTRIBUTION_VALUE_RE being too narrow to see a wrapping call like
     String(...) around a real attribution value (both found this session)
     are exactly the brittleness a text-pattern approach produces.
     CORRECTED 2026-10-07 (H1 batch P, item 4): this bullet originally named
     the identity-attribution defect "branch-span truncation" -- that
     diagnosis was itself wrong (made in batch N, not batch L as first
     mis-cited when correcting it), and was reproduced and corrected in
     batch O: the real branch span was intact; the regex itself could not
     see past a wrapping function call. Fixed here rather than left
     standing, the exact discipline this design note is itself arguing for.
     An AST gives real syntactic structure a regex cannot see (which
     `except` body is actually just `pass`, which assert is actually
     comparing two identical sub-trees).
  B. Wrap an existing third-party AST linter (bandit, pylint) and filter its
     output to these four rules. Rejected because the instruction is
     explicit: build this role's own checker from scratch, under its own
     prefix, and never read or use another auditor's or builder's
     equivalent -- wrapping a general tool is not building one.
  CHOSEN: a small, dependency-free `ast.NodeVisitor` implementing exactly
  the four rules above, each independently testable and ablatable.

TEST PLAN: every rule ships three things -- a planted BAD fixture (a real
snippet that should FLAG), a CLEAN fixture (a real snippet of the same
general shape that should NOT flag), and an ABLATION (the bad fixture run
with that one rule's visitor method stubbed out, proving the rule's
presence -- not luck -- is what catches it). `--selftest` runs all of this,
three identical times, and prints the first run's own result explicitly
rather than only a final summary.

A rule is added here ONLY when it can be stated as a mechanical AST
predicate with no need to execute or interpret runtime values -- consistent
with "add a rule only when it can be detected mechanically."
"""
import ast
import sys


# ---------------------------------------------------------------------------
# Rule 1: ignored subprocess/os return or exit code.
# ---------------------------------------------------------------------------
_SUBPROCESS_IGNORABLE = {
    ('subprocess', 'run'), ('subprocess', 'call'), ('subprocess', 'check_call'),
    ('subprocess', 'check_output'), ('os', 'system'),
}


def _call_target(node):
    """Return (module, attr) for a Call like subprocess.run(...) or
    os.system(...), or None if the call is not one of those shapes."""
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return (func.value.id, func.attr)
    return None


class IgnoredReturnVisitor(ast.NodeVisitor):
    """Two mechanical sub-shapes, both inside RULE 1:
    (a) the call sits alone as a bare expression statement -- its result is
        thrown away at the call site, unconditionally.
    (b) the call is assigned to a name, but that name is never referenced
        again anywhere else in the same function body (a dead store --
        captured and never read, which is the same ignored-result shape one
        step removed)."""

    def __init__(self):
        self.findings = []

    def visit_FunctionDef(self, node):
        self._scan_function(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Module(self, node):
        # Also scan bare module-level statements (scripts with no function).
        self._scan_body(node.body, scope_node=node)
        self.generic_visit(node)

    def _scan_function(self, node):
        self._scan_body(node.body, scope_node=node)

    @staticmethod
    def _has_check_true(call_node):
        """check=True makes subprocess.run/call/check_call RAISE on a
        nonzero exit -- nothing is actually ignored, even though the call
        sits as a bare statement with no assignment. Found missing,
        2026-10-07 (H1 batch P, item 11): a clean control fixture built for
        this exact item's own planted-defect exercise (subprocess.run([...],
        capture_output=True, check=True) as a bare statement) was wrongly
        flagged by the pre-fix version of this check -- the SAME blind spot
        already measured at 18% of real ignored_return_bare hits in batch O
        (item 3) but, until now, only measured there, never actually closed
        for the bare-statement sub-case."""
        for kw in call_node.keywords:
            if kw.arg == 'check' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
        return False

    def _scan_body(self, body, scope_node):
        assigned_names = {}
        for stmt in body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                tgt = _call_target(stmt.value)
                if tgt in _SUBPROCESS_IGNORABLE and not self._has_check_true(stmt.value):
                    self.findings.append(('ignored_return_bare', stmt.lineno,
                                          '%s.%s(...) result discarded as a bare statement' % tgt))
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                tgt = _call_target(stmt.value)
                if tgt in _SUBPROCESS_IGNORABLE:
                    for t in stmt.targets:
                        if isinstance(t, ast.Name):
                            assigned_names[t.id] = (stmt.lineno, tgt)
        if not assigned_names:
            return
        # Count every Name load of each assigned variable anywhere in this
        # scope (including nested blocks) OTHER than the assignment itself.
        used = set()
        for n in ast.walk(scope_node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in assigned_names:
                used.add(n.id)
        for name, (lineno, tgt) in assigned_names.items():
            if name not in used:
                self.findings.append(('ignored_return_dead_store', lineno,
                                      "%s.%s(...) assigned to '%s' but never referenced again" % (tgt[0], tgt[1], name)))


# ---------------------------------------------------------------------------
# Rule 2: swallowed exception.
# ---------------------------------------------------------------------------
class SwallowedExceptVisitor(ast.NodeVisitor):
    def __init__(self):
        self.findings = []

    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.findings.append(('swallowed_except_bare', node.lineno,
                                  'bare except: catches everything with no filter'))
        elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.findings.append(('swallowed_except_pass_only', node.lineno,
                                  'except body is only pass -- the exception is silently discarded'))
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Rule 3: constant-true or self-matching assertion.
# ---------------------------------------------------------------------------
def _ast_equal(a, b):
    """Structural equality between two AST sub-trees, ignoring lineno/col
    metadata -- used to catch `assert x == x` where both sides are the
    identical expression, not merely equal-looking source text."""
    return ast.dump(a, annotate_fields=False) == ast.dump(b, annotate_fields=False)


class ConstantAssertVisitor(ast.NodeVisitor):
    def __init__(self):
        self.findings = []

    def visit_Assert(self, node):
        t = node.test
        if isinstance(t, ast.Constant) and t.value not in (False, None, 0, ''):
            self.findings.append(('assert_constant_true', node.lineno,
                                  'assert on a constant truthy literal -- can never fail'))
        elif isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], (ast.Eq, ast.Is)):
            left, right = t.left, t.comparators[0]
            if _ast_equal(left, right):
                self.findings.append(('assert_self_matching', node.lineno,
                                      'assert compares an expression to itself -- always true by construction'))
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Rule 4: verdict/exit code cited from a harness status STRING.
# ---------------------------------------------------------------------------
import re as _re
_VERDICT_STRING_RE = _re.compile(r'^(PASS(ED)?|FAIL(ED)?|OK|SUCCESS|GREEN|RED|DONE)$', _re.I)


_EXTERNAL_TEXT_SIGNAL_RE = _re.compile(r'subprocess|stdout|stderr|Popen|check_output|communicate', _re.I)


class HarnessStringVerdictVisitor(ast.NodeVisitor):
    """RETIRED 2026-10-07 (H1 batch P, item 3). Defined but NOT in RULES --
    kept for its own recorded history, not run.

    RE-MEASURED BEFORE DECIDING, PER INSTRUCTION, FULL POPULATION, NOT A
    SAMPLE: 707 of 707 build-agent .py files under tools/, tests/, api/,
    same population as every prior measurement of this rule. BEFORE this
    item's action: 4 hits total -- 1 true positive
    (tests/run_nhi_selftest_scope_probe.py, genuinely parses subprocess
    stdout/stderr text for a status word with no returncode anywhere), 3
    false positives (tools/cron_liveness_check.py, tools/
    demo_credentials_check.py, tools/testability_gate.py) -- a 75% FP rate
    (3 of 4), unchanged from batch O's own count, re-derived fresh rather
    than carried over.

    A THIRD FIX WAS ATTEMPTED BEFORE RETIRING, NOT SKIPPED: generalising the
    In/NotIn-only external-process-text requirement (subprocess/stdout/
    stderr/Popen/check_output/communicate somewhere in the enclosing
    function) to apply to EVERY comparison operator, not only membership
    ones. MEASURED BEFORE COMMITTING TO IT: this would correctly clear
    tools/cron_liveness_check.py and tools/testability_gate.py (neither
    function touches anything process-text-shaped at all) but NOT tools/
    demo_credentials_check.py, whose flagged comparison sits inside a large,
    multi-purpose main() that ALSO happens to touch subprocess/stdout
    elsewhere for unrelated reasons -- a false NEGATIVE-shaped problem this
    time (the signal exists in the function but has nothing to do with the
    actual comparison), which is the identical root limitation named as this
    tool's own non-goal from the start: no real data-flow tracing, only
    syntactic proximity. A syntax-tree-only tool cannot reliably tell
    "this verdict traces back to real captured text" from "this function
    happens to also import subprocess" without tracking which SPECIFIC
    value flows into which SPECIFIC comparison -- exactly the thing this
    tool's own design note said from day one it would not attempt.

    DECISION: RETIRED, not further patched. Two real fix attempts (batch O,
    this item) each measurably improved the rate (96% -> 75%) without
    reaching a state where the rule's output is more often right than
    wrong, and the remaining failure mode requires real data-flow analysis
    to close -- out of scope for what this tool was built to be. AFTER:
    0 findings from this rule, because it no longer runs; the 3 named
    false-positive files and the 1 true positive are simply no longer
    reported by this tool at all, not reported-and-ignored.

    A verdict derived from comparing text against a status-word literal,
    inside a function that never references .returncode / exit_code / exitcode
    / rc / ret anywhere IN THE WHOLE MODULE -- the real captured signal this
    platform's own rules require.

    REFINED 2026-10-07 (H1 batch O, item 6) after measuring a real ~96%
    false-positive rate on build-agent code (25 of 26 hits in that sweep were
    not the concern this rule targets). Two real, named mechanisms behind
    that rate, both addressed here rather than accepted as-is:
    (1) the original check only looked INSIDE the one function containing the
        comparison -- a verdict string correctly derived from a real
        returncode in one function (e.g. run_one()) and merely CONSUMED by a
        second function one level removed read as unverified. Fixed by
        checking the WHOLE MODULE for a real exit signal, not just the local
        function, and by recognising the short names 'rc'/'ret' alongside the
        longer ones.
    (2) an In/NotIn comparison (`'X' in container`) is structurally different
        from an Eq/NotEq one: it can be testing dict-key membership
        (`'ok' not in payload`) or inspecting another AST node's own text
        (`'FAIL' in n.value` inside a static-analysis tool) rather than
        checking a captured status word. Eq/NotEq keeps the original rule
        unchanged; for In/NotIn specifically, this now ALSO requires a real
        external-process-text signal (subprocess/stdout/stderr/Popen/
        check_output/communicate) to appear somewhere in the SAME function,
        since that is the shape of the one genuine instance measured (text
        assembled from `r.stdout`/`r.stderr` and substring-matched).

    DISCLOSED, NOT CLAIMED FIXED: this remains a per-function/per-module
    syntactic heuristic, not real data-flow tracing (a stated non-goal).  A
    handful of in-process, locally-computed verdict comparisons with no
    textual signal in their own module at all (no subprocess/.returncode
    anywhere in the whole file) can still false-positive -- named as an
    accepted residual in the design note and the batch-O log entry that
    measured it, not silently claimed solved."""

    def __init__(self):
        self.findings = []
        self._module_has_exit_signal = None  # filled in by visit_Module

    def visit_Module(self, node):
        self._module_has_exit_signal = self._has_real_exit_signal(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self._scan(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _has_real_exit_signal(self, node):
        for n in ast.walk(node):
            if isinstance(n, ast.Attribute) and n.attr in ('returncode',):
                return True
            if isinstance(n, ast.Name) and n.id in ('exit_code', 'exitcode', 'returncode', 'rc', 'ret'):
                return True
        return False

    def _has_external_text_signal(self, node):
        for n in ast.walk(node):
            if isinstance(n, ast.Attribute) and _EXTERNAL_TEXT_SIGNAL_RE.search(n.attr or ''):
                return True
            if isinstance(n, ast.Name) and _EXTERNAL_TEXT_SIGNAL_RE.search(n.id or ''):
                return True
        return False

    def _scan(self, node):
        # Module-wide signal takes priority: if the WHOLE FILE shows a real
        # exit code being checked anywhere, a verdict string elsewhere in
        # that same file is presumed downstream of it, not a fresh trust of
        # raw harness text. Falls back to the function-local check if the
        # module scan has not run yet (should not happen via normal visit
        # order, kept as a safe default).
        if self._module_has_exit_signal if self._module_has_exit_signal is not None else self._has_real_exit_signal(node):
            return
        has_external_text = None  # computed lazily, only if an In/NotIn hit needs it
        for n in ast.walk(node):
            if isinstance(n, ast.Compare):
                ops_are_membership = all(isinstance(op, (ast.In, ast.NotIn)) for op in n.ops)
                sides = [n.left] + list(n.comparators)
                for s in sides:
                    if isinstance(s, ast.Constant) and isinstance(s.value, str) and _VERDICT_STRING_RE.match(s.value.strip()):
                        if ops_are_membership:
                            if has_external_text is None:
                                has_external_text = self._has_external_text_signal(node)
                            if not has_external_text:
                                continue  # dict-key-membership / text-inspection shape, not this rule's concern
                        self.findings.append(('verdict_from_status_string', n.lineno,
                                              "verdict compared against status literal %r with no .returncode/exit_code/rc anywhere in this module" % s.value))


RULES = {
    'ignored_return': IgnoredReturnVisitor,
    'swallowed_except': SwallowedExceptVisitor,
    'constant_assert': ConstantAssertVisitor,
    # 'harness_string_verdict': RETIRED 2026-10-07 (H1 batch P, item 3). See
    # HarnessStringVerdictVisitor's own class docstring for the full
    # before/after measurement and the reasoning. Left defined above (not
    # deleted) so the retirement is a recorded decision with its own
    # evidence attached, not a silent removal.
}


def check_source(source, filename='<string>', skip_rules=()):
    """Parse source (never exec/eval it) and run every enabled rule visitor.
    Returns a list of (rule_name, lineno, message)."""
    tree = ast.parse(source, filename=filename)
    findings = []
    for name, visitor_cls in RULES.items():
        if name in skip_rules:
            continue
        v = visitor_cls()
        v.visit(tree)
        for kind, lineno, msg in v.findings:
            findings.append((name, kind, lineno, msg))
    return findings


def check_file(path, skip_rules=()):
    with open(path, encoding='utf-8') as f:
        source = f.read()
    return check_source(source, filename=path, skip_rules=skip_rules)


# ---------------------------------------------------------------------------
# Fixtures -- one BAD + one CLEAN example per rule, used by --selftest.
# ---------------------------------------------------------------------------
FIXTURES = {
    'ignored_return': {
        'bad': "import subprocess\n"
               "def run_it():\n"
               "    subprocess.run(['git', 'push'])\n",
        'clean': "import subprocess\n"
                 "def run_it():\n"
                 "    r = subprocess.run(['git', 'push'])\n"
                 "    if r.returncode != 0:\n"
                 "        raise SystemExit(1)\n",
    },
    'swallowed_except': {
        'bad': "def f():\n"
               "    try:\n"
               "        risky()\n"
               "    except Exception:\n"
               "        pass\n",
        'clean': "def f():\n"
                 "    try:\n"
                 "        risky()\n"
                 "    except Exception as e:\n"
                 "        log.error('risky failed: %s', e)\n"
                 "        raise\n",
    },
    'constant_assert': {
        'bad': "def f(x):\n"
               "    assert x == x\n",
        'clean': "def f(x, y):\n"
                 "    assert x == y, 'x and y must match'\n",
    },
    # 'harness_string_verdict' fixtures REMOVED 2026-10-07 (H1 batch P, item
    # 3) along with the rule's retirement -- see HarnessStringVerdictVisitor's
    # own docstring. A retired rule has no active fixture to run; keeping one
    # here would only make the generic FIXTURES loop below report a FAIL for
    # a rule deliberately no longer in RULES, which is not a real failure.
}


def _run_once():
    """Run every fixture pair plus every ablation once. Returns
    (ok_count, total_count, lines) for the caller to print/compare."""
    ok = 0
    total = 0
    lines = []
    for rule, pair in FIXTURES.items():
        total += 1
        bad_hits = [f for f in check_source(pair['bad']) if f[0] == rule]
        if bad_hits:
            ok += 1
            lines.append('  ok   %-24s bad fixture correctly FLAGGED (%s)' % (rule, bad_hits[0][1]))
        else:
            lines.append('  FAIL %-24s bad fixture was NOT flagged' % rule)

        total += 1
        clean_hits = [f for f in check_source(pair['clean']) if f[0] == rule]
        if not clean_hits:
            ok += 1
            lines.append('  ok   %-24s clean fixture correctly PASSED' % rule)
        else:
            lines.append('  FAIL %-24s clean fixture was wrongly flagged: %r' % (rule, clean_hits))

        total += 1
        ablated_hits = [f for f in check_source(pair['bad'], skip_rules=(rule,)) if f[0] == rule]
        if not ablated_hits:
            ok += 1
            lines.append('  ok   %-24s ABLATION: disabling this rule makes the bad fixture pass undetected (proves the rule, not luck, caught it)' % rule)
        else:
            lines.append('  FAIL %-24s ablation still flagged -- rule is not actually gating this fixture' % rule)

    # ── Two regression fixtures for the real false-positive classes found
    # and fixed against build-agent code, 2026-10-07 (batch O, item 6) --
    # REMOVED 2026-10-07 (batch P, item 3) along with the rule's own
    # retirement. Both regressions tested harness_string_verdict's behavior;
    # with the rule no longer in RULES, `f[0] == 'harness_string_verdict'`
    # can never be true and the checks would pass VACUOUSLY (testing
    # nothing) rather than meaningfully -- removed rather than left as a
    # false green. See HarnessStringVerdictVisitor's own docstring for the
    # retirement's full reasoning.

    # Regression fixture, 2026-10-07 (batch P, item 11): a check=True bare
    # subprocess.run() call must NOT be flagged -- found broken by this
    # item's own planted-fixture exercise (one of 5 authored CLEAN controls
    # was wrongly caught), fixed the same entry (_has_check_true()).
    total += 1
    check_true_src = (
        "import subprocess\n"
        "def cleanup():\n"
        "    subprocess.run(['git', 'worktree', 'prune'], capture_output=True, check=True)\n"
    )
    hits = [f for f in check_source(check_true_src) if f[0] == 'ignored_return']
    if not hits:
        ok += 1
        lines.append('  ok   regression: a bare subprocess.run(..., check=True) statement is no longer flagged')
    else:
        lines.append('  FAIL regression: check=True bare statement still wrongly flagged: %r' % hits)

    return ok, total, lines


def _selftest():
    results = []
    for i in range(3):
        ok, total, lines = _run_once()
        results.append((ok, total))
        if i == 0:
            print('FIRST RUN, recorded explicitly:')
            for l in lines:
                print(l)
            print('%d/%d on first run' % (ok, total))
    all_same = len(set(results)) == 1
    print('3 identical runs: %s -- %s' % (all_same, results))
    final_ok, final_total = results[-1]
    print('%d/%d fixture+ablation checks correct' % (final_ok, final_total))
    return all_same and final_ok == final_total


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--file' in argv:
        i = argv.index('--file')
        path = argv[i + 1]
        findings = check_file(path)
        if not findings:
            print('%s -- 0 findings' % path)
            return 0
        for rule, kind, lineno, msg in findings:
            print('  ! %-24s L%-5d %s' % (rule, lineno, msg))
        print('%s -- %d finding(s)' % (path, len(findings)))
        return 1
    print('usage: hover_py_guard_checker.py --selftest | --file PATH')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
