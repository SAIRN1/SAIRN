"""code_quality_baseline.py -- a real, first cyclomatic-complexity baseline
for this platform, never computed before tonight (2026-09-18), per direct
instruction, closing one of SKILL.md's own explicitly-named never-picked-up
items ("code-quality metrics (SonarQube-style)").

WHAT THIS COMPUTES, AND WHAT IT DOES NOT. Cyclomatic complexity: 1 + the
count of real decision points inside a function body (if/else if, for,
while, case, catch, &&, ||, ??, ternary ?:). This is the real, standard
metric (McCabe, 1976) SonarQube and every other real static-analysis tool
compute the same way. It does NOT compute Technical Debt Ratio -- that needs
a real cost model (minutes-to-fix per violation type) this tool does not
have and should not invent a number for; naming that honestly rather than
fabricating a percentage.

METHOD, AND ITS REAL LIMIT. Regex + balanced-brace extraction, not a real
AST parser -- this platform has no JS/HTML parser dependency installed and
this tool does not install one (same standing rule as every other tool
here: never import/install, build from what's on hand). This means real,
disclosed blind spots: arrow functions without the `function` keyword are
not found; a decision point inside a nested function is double-counted
against the OUTER function too, because brace-matching does not distinguish
"nested function, count separately" from "just a block." Named explicitly,
not smoothed over -- see the blind lock's own control case for it.

BLIND LOCK. Run before any real file is read, against synthetic functions
with a HAND-COUNTED, independently-known complexity, in both directions
(a function with zero branches must score 1; a function with N real
decision points must score N+1; the nested-function double-count blind
spot is itself asserted as a KNOWN, accepted limit, not silently passed).
"""

import io
import os
import re
import statistics
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
# Fallback: this file lives outside the platform repo; the real repo path is
# passed explicitly via --repo, this default is only for a quick sanity path.


FUNC_DECL = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')

# Real McCabe decision-point tokens. `else if` is counted once via `if`
# already appearing in it; a bare `else` is NOT a decision point (it does
# not add a new path, it is the fallthrough of the `if` already counted).
DECISION_RX = re.compile(
    r'\bif\s*\(|\bfor\s*\(|\bwhile\s*\(|\bcatch\s*\(|\bcase\s+[^:]+:'
    r'|&&|\|\||\?\?|\?(?!\.)'
)


def balanced_body(src, open_brace_idx, max_len=20000):
    depth = 0
    for i in range(open_brace_idx, min(len(src), open_brace_idx + max_len)):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return src[open_brace_idx:i + 1]
    return src[open_brace_idx:open_brace_idx + max_len]  # unbalanced/too long


def complexity_of(body):
    return 1 + len(DECISION_RX.findall(body))


def functions_in(src):
    """Yields (name, complexity) for every `function name(...){...}` found."""
    for m in FUNC_DECL.finditer(src):
        brace = src.find('{', m.end())
        if brace < 0:
            continue
        body = balanced_body(src, brace)
        yield m.group(1), complexity_of(body)


def selftest():
    cases = [
        ("function zero(){ return 1; }", 1),
        ("function oneIf(){ if(x){ return 1; } return 0; }", 2),
        ("function threeIf(){ if(a){} if(b){} if(c){} }", 4),
        ("function loopAndOr(){ for(i=0;i<9;i++){ if(a&&b){} } }", 4),
        ("function ternaryAndCase(){ switch(x){ case 1: break; case 2: break; } "
         "return a?b:c; }", 4),
    ]
    print("BLIND LOCK -- complexity calculator, hand-counted fixtures")
    ok_count = 0
    for src, expected in cases:
        got = None
        for name, c in functions_in(src):
            got = c
        ok = got == expected
        ok_count += 1 if ok else 0
        print("  %s  expected=%d got=%s  %s" % (
            "ok  " if ok else "FAIL", expected, got, src[:50]))

    # KNOWN, ACCEPTED LIMIT, ASSERTED RATHER THAN SILENTLY PASSED: a nested
    # function's decision points are double-counted into the outer function's
    # balanced-brace body too, because brace-matching alone cannot tell
    # "this is a separate function" from "this is just a block."
    nested_src = ("function outer(){ if(a){} function inner(){ if(b){} } }")
    results = dict(functions_in(nested_src))
    double_counted = results.get("outer") == 3  # 1 + outer's if + inner's if
    print("  %s  KNOWN LIMIT confirmed present (nested fn inflates outer): "
          "outer=%s (expected inflated value 3, real is 2)"
          % ("ok  " if double_counted else "FAIL", results.get("outer")))
    ok_count += 1 if double_counted else 0

    total = len(cases) + 1
    print("BLIND LOCK -- %d/%d correct (including the known-limit assertion)"
          % (ok_count, total))
    return ok_count == total


def main(argv):
    if "--selftest" in argv:
        return 0 if selftest() else 1

    if "--repo" not in argv:
        print("--repo PATH is required, or --selftest")
        return 2
    repo = argv[argv.index("--repo") + 1]

    print("Running blind lock before trusting a real scan...")
    if not selftest():
        print("BLIND LOCK FAILED -- refusing to compute a real baseline.")
        return 2
    print()

    targets = []
    for f in sorted(os.listdir(repo)):
        if f.endswith(".html"):
            targets.append(os.path.join(repo, f))
    api_dir = os.path.join(repo, "api")
    if os.path.isdir(api_dir):
        for dp, _dn, fn in os.walk(api_dir):
            for f in fn:
                if f.endswith(".js") and not f.endswith(".test.js"):
                    targets.append(os.path.join(dp, f))

    all_complexities = []
    per_file_max = {}
    top_functions = []
    for path in targets:
        try:
            src = io.open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        rel = os.path.relpath(path, repo)
        file_complexities = []
        for name, c in functions_in(src):
            all_complexities.append(c)
            file_complexities.append(c)
            top_functions.append((c, rel, name))
        if file_complexities:
            per_file_max[rel] = max(file_complexities)

    if not all_complexities:
        print("COULD NOT TELL: zero functions matched across %d files -- "
              "either the tree is empty or the FUNC_DECL pattern found "
              "nothing, which is itself worth checking before trusting a "
              "silent zero." % len(targets))
        return 2

    top_functions.sort(reverse=True)

    print("CODE-QUALITY BASELINE (Cyclomatic Complexity) -- %d functions "
          "across %d files, first real computation on this platform"
          % (len(all_complexities), len(targets)))
    print("  mean:   %.2f" % statistics.mean(all_complexities))
    print("  median: %.1f" % statistics.median(all_complexities))
    print("  max:    %d" % max(all_complexities))
    print("  industry average band cited in SKILL.md: ~10-15 per function")
    over_15 = [c for c in all_complexities if c > 15]
    print("  functions over 15: %d (%.1f%% of %d)"
          % (len(over_15), 100.0 * len(over_15) / len(all_complexities),
             len(all_complexities)))
    print()
    print("  Top 15 most complex functions found:")
    for c, rel, name in top_functions[:15]:
        print("    %4d  %s :: %s" % (c, rel, name))
    print()
    print("DISCLOSED LIMIT, NOT PAPERED OVER: regex+brace-matching, not a "
          "real AST parser. Arrow functions are not counted at all -- this "
          "is a real, structural undercount of the true function population, "
          "not a claim of exhaustive coverage. A nested function's decision "
          "points are double-counted into its enclosing function too (the "
          "blind lock's own known-limit case demonstrates this), so any "
          "single function's number here is an upper bound on its true "
          "complexity, not an exact one.")
    print("NO TECHNICAL DEBT RATIO IS REPORTED -- that needs a real cost "
          "model this tool does not have. Fabricating a percentage would be "
          "exactly the kind of fabricated-KPI this platform's own Guardian "
          "check 0b exists to catch.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
