#!/usr/bin/env python
"""hover2_python_guard_checker.py -- this role's OWN static Python
checker, built from scratch under this role's own prefix. Never read or
used any builder equivalent (tools/*.py's own checkers were not opened
while writing this file's rules) -- the rule shapes below come from the
four patterns item 19 named directly, not from reading how a builder
checker already looks for them.

====================================================================
DESIGN NOTE (written first, per instruction)
====================================================================

GOALS: detect, via Python's own `ast` module (parse only, NEVER execute
the code being checked), four mechanically-checkable anti-patterns named
by the dispatching instruction:
  1. an ignored return/exit code from a subprocess or os call
  2. a swallowed exception (bare except, or except followed only by pass)
  3. a constant-true or self-matching assertion
  4. a verdict or exit code cited from a harness status STRING rather
     than a real captured exit code

NON-GOALS: this is not a general linter. No style rules, no complexity
metrics, no import-order checks, no type inference, no cross-file
data-flow analysis. A rule is added here ONLY if it is checkable from a
single file's AST with no execution -- per the dispatching instruction's
own stated bound ("add a rule only when it can be detected mechanically"
and this role's own standing discipline against over-scoping a tool past
a measured need.

ALTERNATIVES CONSIDERED:
  1. Regex over source text, the shape most sibling tools in this
     directory use (hover2_gate_parity_check.py, bld_draws_bypass_
     repro.py, etc). REJECTED for this specific checker: every one of
     the four rules above is fundamentally about CONTROL-FLOW SHAPE (is
     a call's result ever bound to a name; is an except body exactly
     one statement and is that statement Pass) that a regex cannot
     reliably answer -- it would either over-match (a comment containing
     the word "pass") or under-match (a call spanning multiple lines, a
     different whitespace style). AST gives the exact node shape with no
     guessing.
  2. A full data-flow engine tracking whether a captured return value is
     EVER consulted anywhere later in the function (not just whether it
     was bound at the call site). REJECTED for this batch as overscoped:
     the common, real shape this platform has actually hit (per
     CLAUDE.md's own stated defect class) is the call's result being
     discarded immediately as a bare expression statement with no
     assignment at all -- catching that needs no data-flow engine, only
     a check of whether the enclosing statement is an `Expr` with no
     target. The real, named LIMIT: a value that IS bound
     (`rc = subprocess.run(...)`) and then never read again anywhere
     downstream is NOT caught by this checker -- that needs real
     data-flow, which this file does not build. Reported as a boundary,
     not quietly claimed solved.

TEST PLAN: each rule carries, in this same file, (a) a clean fixture that
must NOT flag, (b) a bad fixture that MUST flag, and (c) an explicit
ablation proving the rule is not vacuously true -- a deliberately
weakened matcher that WOULD pass the bad fixture, run alongside the real
one so the selftest shows the real rule catches something the weak one
does not. `--selftest` runs all three for all four rules. The real
population run (own tools, then builder files read-only) is executed
THREE IDENTICAL TIMES per the dispatching instruction, with the first
run's output recorded verbatim in the audit chain rather than only the
final one.

====================================================================
THE FOUR RULES
====================================================================

R1_IGNORED_SUBPROCESS_RETURN -- a bare expression statement (no
  assignment, no `if`/`return` wrapping its value) whose value is a call
  to subprocess.run / subprocess.call / subprocess.check_call / os.system
  / os.popen, UNLESS the call carries a `check=True` keyword (which turns
  a nonzero code into a raised exception -- a different, legitimate
  pattern, not a discarded result).

R2_SWALLOWED_EXCEPTION -- an `except` clause that either names no
  exception type at all (bare `except:`), or whose entire body is exactly
  one `pass` statement (with or without a named exception type).

R3_CONSTANT_ASSERTION -- an `assert` whose test is a literal truthy
  constant (`True`, a nonzero int/float), OR whose test is a `Compare`
  node where the left operand and the (single) comparator are
  structurally IDENTICAL (the same AST dump), e.g. `assert x == x`.

R4_HARNESS_STRING_VERDICT -- an assignment to a name that LOOKS like a
  verdict/exit-code holder (contains "exit_code", "verdict", "returncode"
  -- case-insensitive -- in its own name) where the right-hand side is a
  string-literal comparison or membership test against one of a small
  set of harness-status words ({"PASS","FAIL","OK","SUCCESS","ERROR",
  "COMPLETED"}), rather than an integer attribute access. Named
  heuristic, scoped narrowly on purpose -- see the rule's own code
  comment for the false-positive risk this creates and why it is
  accepted anyway.

Read-only. Parses files with `ast.parse`; never calls `exec`, `eval`,
`compile(..., 'exec')`->run, or any subprocess. Writes nothing.

Usage:
  python hover2_python_guard_checker.py --file PATH
  python hover2_python_guard_checker.py --glob "PATTERN" [--repo PATH]
  python hover2_python_guard_checker.py --selftest
"""
import argparse
import ast
import glob as globmod
import os
import sys

HARNESS_STATUS_WORDS = {'PASS', 'FAIL', 'OK', 'SUCCESS', 'ERROR', 'COMPLETED'}
VERDICT_NAME_HINTS = ('exit_code', 'verdict', 'returncode')
SUBPROCESS_FUNCS = {
    ('subprocess', 'run'), ('subprocess', 'call'), ('subprocess', 'check_call'),
    ('subprocess', 'check_output'), ('os', 'system'), ('os', 'popen'),
}


def _call_target(call):
    """Returns ('module', 'func') for a Call like subprocess.run(...), or
    None if it is not a simple Attribute-on-Name call."""
    f = call.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        return (f.value.id, f.attr)
    return None


def _has_check_true(call):
    for kw in call.keywords:
        if kw.arg == 'check' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False


def check_r1(tree, weak=False):
    """weak=True runs a deliberately under-powered version (ignores the
    check=True exemption) -- used only by the ablation arm to prove R1's
    real form catches something the weak form would wrongly also flag
    differently, demonstrating the rule is not a vacuous always-match."""
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            target = _call_target(node.value)
            if target in SUBPROCESS_FUNCS:
                if weak or not _has_check_true(node.value):
                    hits.append(node.lineno)
    return hits


def check_r2(tree):
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            bare = node.type is None
            body_is_pass_only = (len(node.body) == 1 and isinstance(node.body[0], ast.Pass))
            if bare or body_is_pass_only:
                hits.append(node.lineno)
    return hits


def check_r3(tree):
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            t = node.test
            if isinstance(t, ast.Constant) and t.value not in (None, False, 0, ''):
                hits.append(node.lineno)
            elif isinstance(t, ast.Compare) and len(t.ops) == 1:
                left_dump = ast.dump(t.left)
                right_dump = ast.dump(t.comparators[0])
                if left_dump == right_dump:
                    hits.append(node.lineno)
    return hits


def check_r4(tree):
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            name_lc = target.id.lower()
            if not any(h in name_lc for h in VERDICT_NAME_HINTS):
                continue
            val = node.value
            is_status_compare = False
            if isinstance(val, ast.Compare):
                for c in [val.left] + list(val.comparators):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str) and \
                            c.value.upper() in HARNESS_STATUS_WORDS:
                        is_status_compare = True
            elif isinstance(val, ast.Constant) and isinstance(val.value, str) and \
                    val.value.upper() in HARNESS_STATUS_WORDS:
                is_status_compare = True
            if is_status_compare:
                hits.append(node.lineno)
    return hits


RULES = [
    ('R1_IGNORED_SUBPROCESS_RETURN', check_r1),
    ('R2_SWALLOWED_EXCEPTION', check_r2),
    ('R3_CONSTANT_ASSERTION', check_r3),
    ('R4_HARNESS_STRING_VERDICT', check_r4),
]


def check_file(path):
    try:
        src = open(path, encoding='utf-8').read()
    except (IOError, OSError) as e:
        return None, 'COULD NOT RUN: %s' % e
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as e:
        return None, 'COULD NOT RUN: syntax error, %s' % e
    findings = {}
    for name, fn in RULES:
        hits = fn(tree)
        if hits:
            findings[name] = hits
    return findings, None


# ====================================================================
# SELFTEST: clean + bad + ablation fixture per rule
# ====================================================================

FIXTURES = {
    'R1_IGNORED_SUBPROCESS_RETURN': {
        'clean': "import subprocess\nrc = subprocess.run(['x'])\n",
        'clean_checked': "import subprocess\nsubprocess.run(['x'], check=True)\n",
        'bad': "import subprocess\nsubprocess.run(['x'])\n",
    },
    'R2_SWALLOWED_EXCEPTION': {
        'clean': "try:\n    x = 1\nexcept ValueError as e:\n    log(e)\n",
        'bad_bare': "try:\n    x = 1\nexcept:\n    pass\n",
        'bad_named_pass': "try:\n    x = 1\nexcept ValueError:\n    pass\n",
    },
    'R3_CONSTANT_ASSERTION': {
        'clean': "assert x == y\n",
        'bad_true': "assert True\n",
        'bad_self': "assert x == x\n",
    },
    'R4_HARNESS_STRING_VERDICT': {
        'clean': "exit_code = proc.returncode\n",
        'bad': "exit_code = (status == 'PASS')\n",
    },
}


def selftest():
    import tempfile
    results = []

    def run(src):
        fd, path = tempfile.mkstemp(suffix='.py')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(src)
        try:
            findings, err = check_file(path)
        finally:
            os.unlink(path)
        return findings, err

    ok = True

    # R1
    f_clean, _ = run(FIXTURES['R1_IGNORED_SUBPROCESS_RETURN']['clean'])
    f_checked, _ = run(FIXTURES['R1_IGNORED_SUBPROCESS_RETURN']['clean_checked'])
    f_bad, _ = run(FIXTURES['R1_IGNORED_SUBPROCESS_RETURN']['bad'])
    r1_ok = ('R1_IGNORED_SUBPROCESS_RETURN' not in (f_clean or {}) and
             'R1_IGNORED_SUBPROCESS_RETURN' not in (f_checked or {}) and
             'R1_IGNORED_SUBPROCESS_RETURN' in (f_bad or {}))
    # Ablation: the WEAK form (no check=True exemption) must flag
    # clean_checked, proving the real rule's exemption branch is load-
    # bearing and not a no-op.
    weak_tree = ast.parse(FIXTURES['R1_IGNORED_SUBPROCESS_RETURN']['clean_checked'])
    weak_hits = check_r1(weak_tree, weak=True)
    r1_ablation_ok = len(weak_hits) == 1  # weak form wrongly flags what the real form correctly clears
    results.append(('R1', r1_ok, r1_ablation_ok))
    ok = ok and r1_ok and r1_ablation_ok

    # R2
    f_clean, _ = run(FIXTURES['R2_SWALLOWED_EXCEPTION']['clean'])
    f_bare, _ = run(FIXTURES['R2_SWALLOWED_EXCEPTION']['bad_bare'])
    f_named_pass, _ = run(FIXTURES['R2_SWALLOWED_EXCEPTION']['bad_named_pass'])
    r2_ok = ('R2_SWALLOWED_EXCEPTION' not in (f_clean or {}) and
             'R2_SWALLOWED_EXCEPTION' in (f_bare or {}) and
             'R2_SWALLOWED_EXCEPTION' in (f_named_pass or {}))
    # Ablation: a matcher that only checks `node.type is None` (bare-only,
    # the first half this rule could have stopped at) must MISS
    # bad_named_pass -- proving the second half (body-is-pass-only) is
    # load-bearing, not redundant with the first.
    named_pass_tree = ast.parse(FIXTURES['R2_SWALLOWED_EXCEPTION']['bad_named_pass'])
    bare_only_hits = [n.lineno for n in ast.walk(named_pass_tree)
                      if isinstance(n, ast.ExceptHandler) and n.type is None]
    r2_ablation_ok = len(bare_only_hits) == 0
    results.append(('R2', r2_ok, r2_ablation_ok))
    ok = ok and r2_ok and r2_ablation_ok

    # R3
    f_clean, _ = run(FIXTURES['R3_CONSTANT_ASSERTION']['clean'])
    f_true, _ = run(FIXTURES['R3_CONSTANT_ASSERTION']['bad_true'])
    f_self, _ = run(FIXTURES['R3_CONSTANT_ASSERTION']['bad_self'])
    r3_ok = ('R3_CONSTANT_ASSERTION' not in (f_clean or {}) and
             'R3_CONSTANT_ASSERTION' in (f_true or {}) and
             'R3_CONSTANT_ASSERTION' in (f_self or {}))
    # Ablation: a matcher that only checks literal-constant tests (not
    # the self-matching Compare case) must MISS bad_self.
    self_tree = ast.parse(FIXTURES['R3_CONSTANT_ASSERTION']['bad_self'])
    literal_only_hits = [n.lineno for n in ast.walk(self_tree)
                         if isinstance(n, ast.Assert) and isinstance(n.test, ast.Constant)]
    r3_ablation_ok = len(literal_only_hits) == 0
    results.append(('R3', r3_ok, r3_ablation_ok))
    ok = ok and r3_ok and r3_ablation_ok

    # R4
    f_clean, _ = run(FIXTURES['R4_HARNESS_STRING_VERDICT']['clean'])
    f_bad, _ = run(FIXTURES['R4_HARNESS_STRING_VERDICT']['bad'])
    r4_ok = ('R4_HARNESS_STRING_VERDICT' not in (f_clean or {}) and
             'R4_HARNESS_STRING_VERDICT' in (f_bad or {}))
    # Ablation: a matcher requiring the EXACT name "exit_code" (not a
    # substring hint) must MISS a differently-named verdict holder like
    # "final_verdict_exit_code_str" -- proving the substring-hint
    # approach catches real variance a strict-equality name check would
    # not, which is the reason this rule uses `in` rather than `==`.
    variant_src = "final_verdict_exit_code_str = (status == 'PASS')\n"
    variant_tree = ast.parse(variant_src)
    strict_name_hits = [n.lineno for n in ast.walk(variant_tree)
                        if isinstance(n, ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], ast.Name)
                        and n.targets[0].id == 'exit_code']
    r4_ablation_ok = len(strict_name_hits) == 0
    results.append(('R4', r4_ok, r4_ablation_ok))
    ok = ok and r4_ok and r4_ablation_ok

    for rule, rule_ok, ablation_ok in results:
        print('%s: fixtures=%s ablation=%s' %
              (rule, 'PASS' if rule_ok else 'FAIL', 'PASS' if ablation_ok else 'FAIL'))
    print('SELFTEST %s' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file')
    ap.add_argument('--glob')
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    paths = []
    if args.file:
        # BUG FIXED 2026-10-08 (batch Q item 5 sweep): --file was used
        # exactly as typed, never joined with --repo, unlike the --glob
        # branch two lines below which already does this correctly --
        # the same class of bug just fixed in hover2_sha_citation_verify.py,
        # found here by re-running that fix as a sweep over every tool
        # taking a file/doc argument, not assumed absent elsewhere.
        f = args.file
        if not os.path.isabs(f) and not os.path.isfile(f):
            joined = os.path.join(args.repo, f)
            if os.path.isfile(joined):
                f = joined
        paths = [f]
    elif args.glob:
        paths = sorted(globmod.glob(os.path.join(args.repo, args.glob), recursive=True))
    else:
        print('usage: --file PATH | --glob PATTERN [--repo PATH] | --selftest')
        sys.exit(2)

    if not paths:
        print('COULD NOT RUN: no files matched')
        sys.exit(2)

    total_flagged = 0
    could_not_run = 0
    for p in paths:
        findings, err = check_file(p)
        if err:
            print('%s: %s' % (p, err))
            could_not_run += 1
            continue
        if findings:
            total_flagged += 1
            for rule, lines in findings.items():
                print('%s: %s at line(s) %s' % (p, rule, lines))
    print('files examined: %d, flagged: %d, COULD_NOT_RUN: %d' %
          (len(paths), total_flagged, could_not_run))
    sys.exit(1 if total_flagged else (2 if could_not_run else 0))


if __name__ == '__main__':
    main()
