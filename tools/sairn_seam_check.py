#!/usr/bin/env python
"""tools/sairn_seam_check.py -- does the endpoint forward everything the engine reads?

WHY THIS EXISTS
---------------
On 2026-08-27 SAIRNlaw's deadline engine grew a `service_methods` input.
`api/legal-deadlines.js` was never updated, so the field was silently dropped
on every live request for five days. Florida returned answers FIVE DAYS LATE
on the shortest answer period in the engine, and Utah's rule became
unreachable entirely.

BOTH TEST SUITES WERE GREEN THROUGHOUT -- 14/14 on Florida, 59/59 on Utah --
because they call computeDeadline() directly and never traverse the endpoint.
High coverage, on the wrong side of the seam. A dropped field does not throw;
it arrives as `undefined`, the engine takes its default branch, and the
response looks entirely reasonable.

Hank fixed that one seam by hand in api/_lib/deadline-endpoint-inputs.test.js.
This generalises the pattern so the other seams on the platform get the same
guard without one hand-written file each.

WHAT IT CHECKS
--------------
For every endpoint in api/ that hands an OBJECT LITERAL to a function it
require()d from api/_lib/, it compares:

    keys the engine READS off its input parameter
    keys the endpoint SETS in the literal it passes

and reports anything read-but-never-forwarded. It does NOT test values, dates
or behaviour -- those are the engine suites' job, and they were already green
when the Florida bug shipped. It tests the CONTRACT BETWEEN THE TWO FILES,
which is what nothing was testing.

CALL SITES ARE RESOLVED THROUGH require(), NOT BY FUNCTION NAME. A name-only
scan pairs `api/sairndental/public-book.js` with `api/_lib/roofing-locations.js`
because both libs export a `stampLocation` -- a seam that does not exist.

DECLARING SERVER-SUPPLIED FIELDS
--------------------------------
Some inputs are filled from the database inside the endpoint rather than
forwarded from the request, so they are legitimately absent from the literal.
Declare them IN THE ENGINE FILE, next to the code they describe:

    // seam-check: server-supplied calendars, rules

A declaration that goes stale is visible in the diff of the file it guards,
which is the point of putting it there instead of in this tool.

HONEST LIMITS, REPORTED NOT HIDDEN
----------------------------------
This is static analysis of two JavaScript files with regular expressions. It
handles the common shape -- one object parameter, `param.field` reads, an
object literal at the call site. It CANNOT read:
  * a destructured parameter: function f({a, b})
  * a payload built up as a variable and then passed
  * a field reached dynamically: input[key]
Every such case is reported as UNANALYZABLE with the reason. It is never
silently skipped, because "the checker said nothing" and "the checker could
not look" must not be the same output. That distinction is the entire reason
the Florida bug survived five days.

EXIT CODES
----------
  0  every analysable seam forwards everything its engine reads
  1  at least one engine input is read but never forwarded  <- the defect
  2  nothing blocking, but at least one seam could not be analysed
"""

import os
import re
import sys
import glob
import json

SEP = chr(92)


def norm(p):
    return p.replace(SEP, '/')


def read(p):
    return open(p, encoding='utf-8', errors='replace').read()


def strip_comments(s):
    """Remove comments so a commented-out `input.foo` is not counted as a read.

    Same reason sairn_strict_args_check.py strips them: a comment quoting the
    old code is the false positive that bit the re-scan of a fix.
    """
    s = re.sub(r'/\*[\s\S]*?\*/', '', s)
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)
    return s


def discover_pairs(root='.'):
    """(endpoint, lib, fn) for every object-literal call into an api/_lib module."""
    endpoints = [norm(p) for p in glob.glob('api/*.js') + glob.glob('api/*/*.js')
                 if not p.endswith('.test.js') and '/_lib/' not in norm(p)]
    out = []
    for ep in sorted(endpoints):
        src = read(ep)
        reqs = {}
        for m in re.finditer(
                r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*require\(\s*[\'"]([^\'"]+)[\'"]\s*\)', src):
            alias, rel = m.group(1), m.group(2)
            if '_lib' in rel:
                reqs[alias] = norm(os.path.normpath(os.path.join(os.path.dirname(ep), rel)))
        for m in re.finditer(
                r'(?:const|let|var)\s*\{([^}]*)\}\s*=\s*require\(\s*[\'"]([^\'"]+)[\'"]\s*\)', src):
            names, rel = m.group(1), m.group(2)
            if '_lib' not in rel:
                continue
            lib = norm(os.path.normpath(os.path.join(os.path.dirname(ep), rel)))
            for n in re.findall(r'([A-Za-z_$][\w$]*)', names):
                reqs[n] = lib
        for alias, lib in reqs.items():
            if not lib.endswith('.js'):
                lib += '.js'
            if not os.path.isfile(lib):
                continue
            for m in re.finditer(re.escape(alias) + r'\.([A-Za-z_$][\w$]*)\s*\(\s*\{', src):
                out.append((ep, lib, m.group(1)))
            for m in re.finditer(r'(?<![.\w])' + re.escape(alias) + r'\s*\(\s*\{', src):
                out.append((ep, lib, alias))
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


# `if (x)` and `return (x)` look exactly like a call to a regex. Excluded so a
# control-flow keyword is never mistaken for a delegate.
KEYWORDS_NOT_CALLS = frozenset([
    'if', 'for', 'while', 'switch', 'catch', 'return', 'typeof', 'void',
    'delete', 'new', 'await', 'in', 'of', 'do', 'else', 'function',
])


def balanced(src, start, open_ch='{', close_ch='}'):
    """Substring from an opening brace to its match. None if unbalanced."""
    depth, i = 0, start
    while i < len(src):
        c = src[i]
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    return None


def engine_reads(lib_src, fn, _depth=0):
    """Field names the engine function reads off its single object parameter.

    Returns (reads, problem). `problem` is a human sentence when the shape is
    one this tool cannot read, and `reads` is then meaningless.

    `_depth` is internal: it bounds delegation-following to ONE level. Callers
    always leave it alone.
    """
    m = re.search(r'function\s+' + re.escape(fn) + r'\s*\(([^)]*)\)', lib_src)
    if not m:
        m = re.search(r'(?:const|let|var)\s+' + re.escape(fn) +
                      r'\s*=\s*(?:async\s*)?(?:function\s*)?\(([^)]*)\)', lib_src)
    if not m:
        return set(), 'no function declaration found for %s()' % fn
    params = m.group(1).strip()
    if params.startswith('{'):
        return set(), ('%s() destructures its parameter -- this tool reads '
                       '`param.field` accesses and cannot follow destructuring' % fn)
    if not params:
        return set(), '%s() takes no parameters' % fn
    pname = re.split(r'[,\s=]', params)[0]
    body_start = lib_src.find('{', m.end() - 1)
    body = balanced(lib_src, body_start)
    if body is None:
        return set(), 'could not find a balanced body for %s()' % fn
    reads = set(re.findall(r'(?<![.\w])' + re.escape(pname) + r'\.([A-Za-z_$][\w$]*)', body))

    # FOLLOW ONE LEVEL OF COPY. dnt-location.js does
    #     const out = Object.assign({}, payload || {});  ... out.location_id
    # so a naive scan sees zero reads off `payload` and calls the seam clean --
    # a vacuous pass. Reads through a single-level copy alias count as reads of
    # the input, because they are. Deeper aliasing is still not followed and
    # still reports CANNOT TELL rather than guessing.
    aliases = set()
    for m in re.finditer(
            r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*Object\.assign\(\s*\{\s*\}\s*,\s*'
            + re.escape(pname) + r'\b', body):
        aliases.add(m.group(1))
    for m in re.finditer(
            r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*\{\s*\.\.\.\s*' + re.escape(pname) + r'\b', body):
        aliases.add(m.group(1))
    # AND THE OR-DEFAULT ALIAS, which is this codebase's most common defensive
    # spelling and was not followed until 2026-09-04:
    #     const r = record || {};   ... r.dob, r.guardian
    # api/_lib/dental-guardian.js's guardianProblem() is written that way, and
    # the tool reported CANNOT TELL on it the moment the file was added --
    # a standing note on every push, which is the noise class that gets
    # scrolled past until a real finding hides in it.
    #
    # This can only ever ADD reads, so it can turn a CANNOT TELL into a real
    # verdict and can never turn a not-forwarded finding into a pass: more
    # reads means more inputs the endpoint is required to forward, not fewer.
    #
    # Fixed here rather than by rewriting guardianProblem() into a shape the
    # scanner likes -- the same rule this file already states about not
    # rewording a claim to slip past the overlap matcher: the fix belongs in
    # the tool, not in code bent around the tool.
    for m in re.finditer(
            r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*' + re.escape(pname)
            + r'\s*\|\|\s*(?:\{\s*\}|\[\s*\])', body):
        aliases.add(m.group(1))
    for a in aliases:
        reads |= set(re.findall(r'(?<![.\w])' + re.escape(a) + r'\.([A-Za-z_$][\w$]*)', body))

    # FOLLOW ONE LEVEL OF WHOLE-OBJECT DELEGATION. Added 2026-09-02, after this
    # tool reported CANNOT TELL on subcontractor-compliance.js's canAssign():
    #
    #     function canAssign(input) {
    #       input = input || {};
    #       const ev = evaluateSubcontractor(input);   // <- never reads a field
    #
    # That verdict was accurate and blind. Delegation is a normal pattern --
    # arguably cleaner than the copy-alias shape this tool ALREADY follows
    # above -- and the fields canAssign depends on are exactly the ones its
    # delegate reads. The alternative considered and rejected was restructuring
    # canAssign to read fields it does not need, purely to satisfy a scanner.
    # That is the same hollowing-out CLAUDE.md warns about when it says not to
    # reword a claim string to slip past the overlap matcher: the fix belongs
    # in the tool, not in code bent around the tool.
    #
    # STRICT ON PURPOSE -- one level, same file, WHOLE parameter only:
    #   * `other(pname)` with pname as the sole argument. A partial forward
    #     like `other(pname.sub)` is a different thing and is left alone.
    #   * one level, so a chain of three delegates still reports CANNOT TELL
    #     rather than being followed on a guess.
    #   * if the delegate is itself a shape this tool cannot read, that problem
    #     PROPAGATES. Inheriting a delegate's blindness as a clean pass would
    #     be exactly the vacuous pass the `if not reads` branch below exists to
    #     refuse -- the dnt-location.js lesson, one call deeper.
    if _depth == 0:
        for dm in re.finditer(r'(?<![.\w])([A-Za-z_$][\w$]*)\s*\(\s*'
                              + re.escape(pname) + r'\s*\)', body):
            callee = dm.group(1)
            if callee == fn or callee in KEYWORDS_NOT_CALLS:
                continue
            sub_reads, sub_problem = engine_reads(lib_src, callee, _depth=1)
            if sub_problem and sub_problem.startswith('no function declaration found'):
                continue  # not defined in this file -- not delegation we can follow
            if sub_problem:
                return reads | sub_reads, (
                    '%s() hands its whole input to %s(), whose own shape this tool '
                    'cannot read: %s' % (fn, callee, sub_problem))
            reads |= sub_reads

    dynamic = re.search(re.escape(pname) + r'\s*\[', body)
    problem = None
    if dynamic:
        problem = ('%s() also reads its input with a computed key (%s[...]), which '
                   'this tool cannot enumerate' % (fn, pname))
    if not reads:
        # A VACUOUS PASS IS NOT A PASS. dnt-location.js's stampLocation() does
        # `const out = Object.assign({}, payload); ... out.location_id` -- it
        # never touches `payload.field` at all, so this tool saw zero reads and
        # cheerfully reported every input forwarded. Zero reads means the shape
        # was not understood, not that the seam is safe.
        problem = ('%s() makes no direct `%s.field` reads -- it probably copies or '
                   'destructures its input first, so this tool cannot see what it '
                   'depends on' % (fn, pname))
    return reads, problem


# AN EXPLICIT DEFAULT IS NOT A MITIGATION, AND ASSUMING IT WAS BROKE THIS TOOL.
#
# A first version of this file demoted "not forwarded but read behind a
# default" to a note on a clean row. The regression probe then replanted the
# real 2026-08-27 defect -- `service_methods` removed from the endpoint -- and
# THE TOOL DID NOT CATCH IT, because the engine reads that field behind a
# guard. The tool had been made blind to the exact incident it exists for.
#
# The default is not what saves you; the default is what makes the failure
# SILENT. Florida's default branch was `applied_exclusivity_assumed`, which is
# a wrong legal date returned with total confidence for five days.
#
# So every unforwarded field is a finding and exits 1. The guard classification
# survives only as CONTEXT in the output -- it says what the field falls back
# to, never that the gap is acceptable.
GUARD_PATTERNS = [
    r'typeof\s+{p}\.{f}\s*===',
    r'{p}\.{f}\s*(?:!==|===)\s*(?:undefined|null)',
    r'{p}\.{f}\s*\|\|',
    r'{p}\.{f}\s*\?\?',
    r'Array\.isArray\(\s*{p}\.{f}\s*\)',
    r'{p}\.{f}\s+in\s+',
]


def guarded_fields(body, pname, fields):
    """Which of `fields` are read behind an explicit default/type guard."""
    out = set()
    for f in fields:
        for pat in GUARD_PATTERNS:
            if re.search(pat.format(p=re.escape(pname), f=re.escape(f)), body):
                out.add(f)
                break
    return out


def engine_body(lib_src, fn):
    m = re.search(r'function\s+' + re.escape(fn) + r'\s*\(([^)]*)\)', lib_src)
    if not m:
        return None, None
    params = m.group(1).strip()
    if not params or params.startswith('{'):
        return None, None
    pname = re.split(r'[,\s=]', params)[0]
    body = balanced(lib_src, lib_src.find('{', m.end() - 1))
    return body, pname


def payload_keys(ep_src, fn):
    """Top-level keys of the object literal passed to fn( { ... } )."""
    m = re.search(re.escape(fn) + r'\s*\(\s*\{', ep_src)
    if not m:
        return set(), 'no `%s({` call-site literal found' % fn
    lit = balanced(ep_src, ep_src.rfind('{', 0, m.end()))
    if lit is None:
        return set(), 'unbalanced object literal at the %s() call site' % fn
    inner = lit[1:-1]
    # Blank out nested braces/brackets/strings so only top-level keys remain.
    out, depth = [], 0
    for ch in inner:
        if ch in '{[(':
            depth += 1
        elif ch in '}])':
            depth -= 1
        out.append(ch if depth == 0 else ' ')
    flat = ''.join(out)
    keys = set(re.findall(r'(?:^|,)\s*([A-Za-z_$][\w$]*)\s*:', flat))
    keys |= set(re.findall(r'(?:^|,)\s*\.\.\.\s*([A-Za-z_$][\w$]*)', flat))
    shorthand = set(re.findall(r'(?:^|,)\s*([A-Za-z_$][\w$]*)\s*(?=[,}]|$)', flat))
    keys |= shorthand
    spread = '...' in flat
    return keys, ('the literal uses a spread, so its full key set is not static'
                  if spread else None)


def declared_server_supplied(lib_src):
    out = set()
    for m in re.finditer(r'//\s*seam-check:\s*server-supplied\s+([^\n]+)', lib_src):
        out |= {t.strip() for t in re.split(r'[,\s]+', m.group(1)) if t.strip()}
    return out


def main():
    as_json = '--json' in sys.argv
    findings, unanalyzable, clean = [], [], []

    for ep, lib, fn in discover_pairs():
        lib_src_raw = read(lib)
        lib_src = strip_comments(lib_src_raw)
        ep_src = strip_comments(read(ep))

        reads, rp = engine_reads(lib_src, fn)
        keys, kp = payload_keys(ep_src, fn)
        allowed = declared_server_supplied(lib_src_raw)

        if rp and not reads:
            unanalyzable.append((ep, lib, fn, rp))
            continue
        if kp and not keys:
            unanalyzable.append((ep, lib, fn, kp))
            continue

        missing = sorted(reads - keys - allowed)
        note = '; '.join(x for x in (rp, kp) if x)
        body, pname = engine_body(lib_src, fn)
        guarded = guarded_fields(body, pname, missing) if body else set()
        hard = [f for f in missing if f not in guarded]
        soft = [f for f in missing if f in guarded]
        if missing:
            findings.append((ep, lib, fn, hard, soft, note))
        else:
            clean.append((ep, lib, fn, len(reads), []))
        if note:
            unanalyzable.append((ep, lib, fn, note + ' (partial result reported anyway)'))

    if as_json:
        print(json.dumps({
            'findings': [{'endpoint': e, 'engine': l, 'fn': f,
                          'not_forwarded_unguarded': h, 'not_forwarded_guarded': s, 'note': n}
                         for e, l, f, h, s, n in findings],
            'unanalyzable': [{'endpoint': e, 'engine': l, 'fn': f, 'reason': r}
                             for e, l, f, r in unanalyzable],
            'clean': [{'endpoint': e, 'engine': l, 'fn': f, 'inputs_checked': c,
                       'not_forwarded_but_defaulted': s}
                      for e, l, f, c, s in clean],
        }, indent=2))
    else:
        print('SAIRN endpoint/engine seam check')
        print('=' * 72)
        for e, l, f, c, s in clean:
            extra = ('  [%s never forwarded, but read behind an explicit default]'
                     % ', '.join(s)) if s else ''
            print('  OK          %-30s -> %-30s %s(): %d inputs%s' % (e, l, f, c, extra))
        for e, l, f, r in unanalyzable:
            print('  CANNOT TELL %-30s -> %-30s %s' % (e, l, r))
        for e, l, f, h, s, n in findings:
            print('')
            print('  NOT FORWARDED  %s -> %s' % (e, l))
            print('     %s() reads these and the call site never sets them:' % f)
            for k in h:
                print('        %-24s (no default -- arrives undefined)' % k)
            for k in s:
                print('        %-24s (falls back to a default -- which is what makes it SILENT,' % k)
                print('        %-24s  not what makes it safe: see GUARD_PATTERNS)' % '')
            print('     A dropped field does not throw. It arrives undefined, the engine')
            print('     takes its default branch, and the response looks reasonable --')
            print('     which is how SAIRNlaw ran Florida five days late for five days.')
        print('')
        print('%d clean, %d not-forwarded, %d could-not-tell' %
              (len(clean), len(findings), len(unanalyzable)))
        if unanalyzable and not findings:
            print('')
            print('COULD NOT TELL IS NOT A PASS. Each line above names why, and a seam this')
            print('tool cannot read still needs a hand-written test like')
            print('api/_lib/deadline-endpoint-inputs.test.js.')

    if findings:
        return 1
    if unanalyzable:
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
