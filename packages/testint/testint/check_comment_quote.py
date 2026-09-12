r"""Does a test's assertion match the target's COMMENTS instead of its code?

    python -m testint.check_comment_quote --config testint.config.json

Exit 0 clean, 1 on an undeclared comment-only assertion, 3 could-not-run.

── THE FAILURE ───────────────────────────────────────────────────────────────
A test reads a source file and searches it for a literal. If that literal exists
ONLY inside the file's comments, the test is asserting something about prose.

Twice in one day, in the codebase this came from, hours apart:

  * a test looked for `'Prompt injection: Active'` to prove a hardcoded claim
    had been removed. The fix's new header QUOTES all four dead literals to
    record what they were -- so the test failed a CORRECT file.
  * a test counted `eval(` to prove a file had none. The new CSP comment says
    "this file contains zero eval()" -- so it counted its own documentation.

Both went red, so both were found within the hour.

**THE OTHER DIRECTION IS THE DANGEROUS ONE AND NOTHING WOULD CATCH IT.** An
assertion of PRESENCE -- *the guard is still there* -- goes GREEN when the only
surviving mention of the thing is a comment describing the feature that was
deleted. A test passing off a comment is a check that has stopped checking, and
it will never tell you.

── WHAT IT REPORTS ───────────────────────────────────────────────────────────
  COMMENT-ONLY, undeclared   the literal exists in the target ONLY in comments
  COMMENT-ONLY, declared     the same, listed in the allow file with a reason
  BOTH code and comment      it exists in both -- a COUNT here is inflated, and
                             an assertion on a count is reading documentation
                             as data even though it is not wholly wrong
  SKIPPED                    a search this tool could not read (a variable
                             needle, a concatenation, a regex). COUNTED AND
                             PRINTED, never silent -- a checker that quietly
                             narrows its own subject is the defect being hunted.

── WHAT IT CANNOT DO ─────────────────────────────────────────────────────────
It reads literal searches against a variable bound to the raw file, in the
languages `assertions.py` knows. It cannot follow a needle through a variable,
and it does not know whether an assertion is of presence or absence -- the two
have opposite consequences and only a human can say which was meant. It points
at the line; you read it.
"""
import io
import os
import re
import sys

from . import assertions, comments
from .config import ConfigError, load


def _paths_in(expr):
    """Every quoted fragment in a read call, longest first.

    Longest first because `path.join(__dirname, '..', 'src/app.js')` should
    resolve on `src/app.js` rather than on `..`.
    """
    return sorted(re.findall(r"['\"]([^'\"]+)['\"]", expr), key=len, reverse=True)


CONST_RE = re.compile(
    r"^\s*(?:const|let|var)?\s*([A-Za-z_]\w*)\s*=\s*([^\n;]+)", re.M)


def constants(src):
    """Module-level `NAME = <expr>` bindings, for one level of indirection.

    WHY THIS EXISTS, AND THE NUMBER THAT JUSTIFIES IT. Without it the read call
    `fs.readFileSync(HTML, 'utf8')` is unresolvable, because the path lives in
    a constant defined earlier -- and that is not a rare style, it is the
    dominant one. Measured on a real repo before this was added: **178 of 384
    assertions (46%) were skipped**, and the commonest cause by far was a bare
    identifier.

    ONE LEVEL ONLY, deliberately. Chasing a variable through reassignment and
    function scope is a dataflow problem, and a half-right dataflow analysis
    that resolves the WRONG file produces a confident report about a file the
    test never read -- strictly worse than saying "could not tell". What cannot
    be resolved in one hop stays SKIPPED and stays COUNTED.
    """
    out = {}
    for m in CONST_RE.finditer(src):
        name, val = m.group(1), m.group(2).strip()
        if name not in out:
            out[name] = val
    return out


def resolve_target(expr, cfg, consts=None):
    """Which source file a read call names, or None.

    Matched against the configured sources by SUFFIX, so a test may name the
    path however it likes. Ambiguity returns None rather than a guess: two
    sources ending the same way is exactly the case where picking one produces
    a confident report about the wrong file.
    """
    srcs = cfg.sources()
    # One hop: a read call naming a bare identifier is retried with that
    # identifier's own definition substituted in.
    if consts and not _paths_in(expr):
        for ident in re.findall(r"[A-Za-z_]\w*", expr):
            if ident in consts:
                expr = expr + ' ' + consts[ident]
    for frag in _paths_in(expr):
        frag = frag.replace('\\', '/').lstrip('./')
        if not frag or '/' not in frag and '.' not in frag:
            continue
        hits = [s for s in srcs if s.replace(os.sep, '/').endswith(frag)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            return None
    return None


def bindings(src, profile):
    """{variable: read-expression} for every raw-file read in a test."""
    out = {}
    for m in re.finditer(profile['bind'], src):
        groups = [g for g in m.groups() if g is not None]
        if len(groups) >= 2:
            out[groups[0]] = groups[1]
    # THE TWO-HOP FORM. `with open(EXPR) as F:` ... `VAR = F.read()` is the
    # dominant idiom in real Python test suites -- 750 occurrences against ZERO
    # of the one-liner in 400 files of CPython's own tests -- and missing it is
    # what made this check inspect nothing at all on its first outside corpus.
    pair = profile.get('bind_with')
    if pair:
        open_re, read_re = pair
        for m in re.finditer(open_re, src):
            expr, handle = m.group(1), m.group(2)
            for r in re.finditer(read_re % re.escape(handle), src):
                out.setdefault(r.group(1), expr)
    return out


def searches(src, profile, var):
    """Every (literal, offset) this test searches `var` for."""
    found = []
    for tmpl in profile['search']:
        for m in re.finditer(tmpl % re.escape(var), src):
            lit = m.group(m.lastindex) if m.lastindex else None
            # The literal is the last capturing group in every template; the
            # quote character is the group before it where one exists.
            groups = [g for g in m.groups() if g is not None]
            if not groups:
                continue
            lit = groups[-1] if len(groups[-1]) else (groups[0] if groups else None)
            if lit:
                found.append((lit, m.start()))
    return found


def classify(literal, target_src, target_path):
    """'comment-only', 'both', 'code-only' or 'absent' for a literal."""
    if literal not in target_src:
        return 'absent'
    try:
        code = comments.strip(target_src, path=target_path)
    except comments.UnsupportedLanguage:
        return 'unreadable'
    in_code = literal in code
    # Strip preserves length, so anything the raw file has that the stripped
    # copy does not was inside a comment.
    return 'both' if in_code else 'comment-only'


def run(cfg):
    allow = cfg.allow()
    rows, skipped, unreadable = [], 0, []
    inspected = 0
    tests = cfg.tests()
    if not tests:
        return None, 'no test files matched the config -- nothing was inspected'
    if not cfg.sources():
        return None, 'no source files matched the config -- every target would be unresolvable'

    for t in tests:
        prof = assertions.profile_for(t)
        if not prof:
            unreadable.append(cfg.rel(t))
            continue
        src = io.open(t, encoding='utf-8', errors='replace').read()
        binds = bindings(src, prof)
        consts = constants(src)
        for var, expr in binds.items():
            target = resolve_target(expr, cfg, consts)
            for lit, off in searches(src, prof, var):
                inspected += 1
                if target is None:
                    skipped += 1
                    continue
                tsrc = io.open(target, encoding='utf-8', errors='replace').read()
                verdict = classify(lit, tsrc, target)
                if verdict in ('absent', 'code-only', 'unreadable'):
                    continue
                line = src[:off].count('\n') + 1
                key = (cfg.rel(t), lit)
                rows.append({
                    'test': cfg.rel(t), 'line': line, 'literal': lit,
                    'target': cfg.rel(target), 'verdict': verdict,
                    'declared': allow.get(key),
                })
    return {'rows': rows, 'skipped': skipped, 'inspected': inspected,
            'unreadable': unreadable, 'tests': len(tests)}, None


def main(argv):
    # A REPORT THAT CRASHES ON ITS OWN FINDINGS IS A REPORT THAT SAYS NOTHING.
    # The first run against a real repo died with UnicodeEncodeError on a cp1252
    # console while printing finding 2 of 7 -- after the summary had already
    # printed, so the exit code was right and the detail was gone.
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                    # noqa: BLE001
        pass
    cfgpath = 'testint.config.json'
    if '--config' in argv:
        cfgpath = argv[argv.index('--config') + 1]
    try:
        cfg = load(cfgpath)
        result, why = run(cfg)
    except ConfigError as e:
        print('COULD NOT RUN: %s' % e)
        return 3
    if result is None:
        print('COULD NOT RUN: %s' % why)
        print('A check with nothing to look at has not passed.')
        return 3

    # ── ZERO *RESOLVED* IS NOT CLEAN, AND THIS TOOL LEARNED IT TWICE ────────
    # First it inspected 0 assertions across 1,131 foreign test files and
    # printed a clean line. That was fixed. The very next run inspected 21 and
    # SKIPPED all 21 -- so nothing was classified, and it printed a clean line
    # again. `inspected` counts ATTEMPTS; only `inspected - skipped` counts
    # answers, and a guard on the wrong one of those two is no guard.
    # Run against 1,131 real test files from a codebase nobody here wrote, it
    # inspected 0 assertions and printed "No undeclared comment-only assertion"
    # with exit 0. That is the exact false-clean this suite is sold against,
    # committed by the suite itself, and found only by pointing it at foreign
    # code. A check that inspected nothing has not passed.
    resolved = result['inspected'] - result['skipped']
    if resolved == 0:
        print('COULD NOT RUN: %d test file(s) matched, %d assertion(s) found, and '
              'NOT ONE had a resolvable target.'
              % (result['tests'], result['inspected']))
        if result['unreadable']:
            print('  %d of them are in a language this tool cannot parse.'
                  % len(result['unreadable']))
        print('  Either these tests do not read source files, or they read them '
              'in a form')
        print('  `assertions.py` does not know, or the files they read are not in '
              '`sources`.')
        print('  NOTHING WAS CLASSIFIED. A clean line here would be a lie about '
              'coverage.')
        return 3

    rows = result['rows']
    undeclared = [r for r in rows if r['verdict'] == 'comment-only' and not r['declared']]
    declared = [r for r in rows if r['verdict'] == 'comment-only' and r['declared']]
    both = [r for r in rows if r['verdict'] == 'both']

    print('COMMENT-QUOTE CHECK -- report only, nothing was written')
    print('  test files              : %d' % result['tests'])
    print('  assertions inspected    : %d' % result['inspected'])
    print('  COMMENT-ONLY, undeclared: %d  (the assertion is testing a comment)'
          % len(undeclared))
    print('  COMMENT-ONLY, declared  : %d  (deliberate -- see the allow file)'
          % len(declared))
    print('  BOTH code and comment   : %d  (a COUNT here is inflated)' % len(both))
    if result['skipped']:
        print('  SKIPPED                 : %d  (target unresolvable -- NOT a pass,'
              ' see below)' % result['skipped'])
    if result['unreadable']:
        print('  UNREADABLE LANGUAGE     : %d test file(s) in a language this '
              'tool cannot parse:' % len(result['unreadable']))
        for u in result['unreadable'][:8]:
            print('      %s' % u)
    print('')
    for r in undeclared + both:
        print('  %-52s %s' % (r['test'], r['verdict'].upper()))
        print('      %r in %s at line %d' % (r['literal'][:70], r['target'], r['line']))
    if not undeclared:
        print('  No undeclared comment-only assertion.')
    print('')
    print('An assertion of PRESENCE that matches only a comment passes while '
          'checking nothing.')
    print('That direction is silent; this tool is how it gets seen.')
    return 1 if undeclared else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
