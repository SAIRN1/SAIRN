# Routed to cc — the branch census, SEVEN rules, and this SUPERSEDES the b26 routing

**Written 2026-10-16 by fourth, batch b27 (resume).**

**THIS REPLACES `docs/2026-10-15-fourth-b26-branch-census-routed-to-cc.md`.**
That document is still correct about why the census must be installed and is
now WRONG about the census itself: it carries three rules, this carries seven,
and the version it carries reports **26 identifiers UNRESOLVED** where this one
reports **0** and reports a **SESSION** branch as **CALLER**. If both documents
are open, install from THIS one and treat the b26 file as the account of how
R1–R3 were paid for. Do not merge them by hand.

`tools/` is cc's by the directory rule, so this is routed rather than written
there. **The full source is carried inline below on purpose:** four previous
versions of this census each lived in a session scratchpad, each was rebuilt
from scratch by the next batch, and each rebuild re-introduced a bug the
previous one had fixed. A routing note that points at a scratchpad path is a
fifth rebuild waiting to happen.

## What to do with it

1. Install as `tools/branch_census.py`, **unchanged except for `REPO`**, which
   is an absolute path in the file below and must become a repo-root
   derivation. Everything else is criteria-locked; editing a rule without
   re-running `--selftest` is the thing the selftest exists to stop.
2. Run `python tools/branch_census.py --selftest`. It must print
   **26/26 fixtures classify correctly**. A non-zero exit is a refusal to
   report a census at all, by design — `--selftest` failing means the census
   is NOT a number with a caveat, it is exit 2 COULD NOT RUN.
3. Run `--ablate`. Every one of the seven rules must come back load-bearing on
   at least one fixture. The run on 2026-10-16 gave R1:1, R2:1, R3:11, R4:3,
   R5:3, R6:2, R7:1 fixture(s) changed. **A rule that changes nothing is a
   finding about the fixtures, not a pass**, and the tool prints that sentence
   itself rather than leaving it to be remembered.
4. Run `--why` after any census whose UNRESOLVED count is not 0. It names, per
   line, the identifier that stalled the walk and the reason, and it
   cross-checks its own answers against `origin()` — a divergence is exit 2 and
   printed as `MIRROR DIVERGED`, never a quiet re-classification.

## The figures this version produces, at `api/sd-data.js` 18,867 lines

| shape | total | write-guarded | GET CALLER | SESSION | UNRESOLVED | SERVER-ONLY | UNCLASSIFIED |
|---|---|---|---|---|---|---|---|
| `A-helper` | 88 | 88 | 0 | 0 | 0 | 0 | 0 |
| `B-inline-503` | 70 | **22** | **35** | 1 | **0** | 10 | 2 |
| `C-200-empty` | 151 | 0 | **34** | 2 | **0** | 115 | 0 |
| `other` | 23 | 1 (`:15150`) | 10 | 0 | **0** | 12 | 0 |

**Against b26's published figures: class B CALLER 32 → 35, class C CALLER
16 → 34, and 26 UNRESOLVED → 0.** The 22 write-guarded branches did not move,
which is the methodology working rather than luck — R5, R6 and R7 only touch
the origin walk, and the write/GET split is R1's.

**0 UNRESOLVED is not the third state being retired.** Three fixtures still
produce it — a name declared nowhere, a function with no call sites, a call
with fewer arguments than the position — so the mechanism can still say it and
0 is a measured answer rather than a collapsed one.

## And one of these rules fixed an OVER-report, which is why the spot check ran both ways

`R7` was adopted to close the last UNRESOLVED line (`:6023`,
`const month = new Date().toISOString().slice(0, 7)` — the walk was tracing the
keyword `new` and the property names `toISOString` and `slice`). Spot-checking
the newly-resolved lines in the **opposite** direction then found
`api/sd-data.js:13364`, which interpolates `enc(String(session.employee_id))`:
`url_idents` had its own name filter, did not strip property names, pulled
`employee_id` out as if it were a variable, resolved that elsewhere in the file
and reported the branch **CALLER** when its only caller-facing name is a
SESSION root. `url_idents` now shares `trace_names` with the rest of the walk.

**Every under-report had already gone to zero at that point, so the only
direction left that could find anything was the over-reporting one.** A census
that had only been checked for things it missed would have shipped this.

## Full source — `tools/branch_census.py`

```python
"""BRANCH CENSUS for api/sd-data.js -- the span is bounded MECHANICALLY, a
caller value is followed through assignments AND across call sites, and the
walk's own blind spots are rules with fixtures rather than a residue.

WHY THIS FILE EXISTS, in five measured failures of its own predecessors:

  b23 (branch_census_b23.py) read `method:` and the URL out of a window that ran
      from the fetch assignment until braces balanced OR 14 lines, whichever
      came first. Its CALLER test was a REGEX OVER THAT BLOB, so a caller value
      arriving through an earlier variable was invisible and 33 GETs were
      reported SERVER-ONLY by the `else` branch of a three-way. CALLER was a
      LOWER BOUND and the report said so, which is better than not saying it and
      is still a number nobody can use.
  b24 (pick_branches_b24.py) used a FIXED 14-line window for `method:` with no
      brace check at all. Three pre-write GETs are followed inside 14 lines by
      the real upsert, so it reported 25 write-guarded branches where there are
      22, and the b24 handoff attributed the difference to the file having moved.
  b25 proved the file had NOT moved -- identical blob sha across 36 commits --
      and fixed the span by bounding it at the next `await fetch(`. That fix
      lived in a one-off script with no fixtures, so nothing stopped the next
      census from re-introducing either bug.
  b26 locked R1-R3 as fixtures and reported 26 identifiers UNRESOLVED, naming
      the parameter case as the reason. That reason was right for 3 of the 26.
  b27 added R4 (parameters across call sites) and the population fell 26 -> 20.
      NINETEEN of the twenty were in class C and R4 had not touched one of them,
      so a bucket nobody could take apart was still being published. The
      `--why` mode exists because of that: it names, per line, the identifier
      that stalled the walk. It answered `resource` sixteen times -- and
      api/sd-data.js:748 declares `const resource = body && body.resource;`,
      one line, 14,000 lines above its last reader. R5, R6 and R7 are the three
      separate reasons that one-line declaration was unreachable.

THE SEVEN RULES THIS FILE LOCKS -- COUNT THE `  R<n> ` LINES BELOW RATHER THAN
TRUSTING THIS WORD, each with fixtures in BOTH directions:

  R1 SPAN-BOUNDED-AT-THE-NEXT-FETCH. The window for reading a fetch's own
     options ends at the next `await fetch(`, never at a line count.
  R2 GUARD-TO-FETCH BINDING IS NEAREST-BACKWARD AND STOPS AT A FETCH OF ANOTHER
     VARIABLE. A guard is attached to the fetch that assigned ITS OWN variable.
  R3 A CALLER VALUE IS FOLLOWED THROUGH ASSIGNMENTS, transitively, and an
     identifier whose origin CANNOT BE RESOLVED IS ITS OWN THIRD STATE. It is
     never folded into SERVER-ONLY, which is what made CALLER a lower bound.
  R4 A PARAMETER IS RESOLVED ACROSS ITS CALL SITES, unioned UNSAFE-WINS.
  R5 THE DECLARATION LOOKBACK IS BOUNDED BY SCOPE, NOT BY A LINE COUNT, and a
     parameter SHADOWS an outer declaration of the same name.
  R6 A ROOT IS NEVER DISCARDED AS URL NOISE. `body` was in CALLER_ROOTS and in
     NOISE at the same time, and NOISE was filtered first.
  R7 A JS KEYWORD AND A PROPERTY NAME AFTER A DOT ARE NOT IDENTIFIERS. This one
     fired in BOTH directions: it closed the last UNRESOLVED line, and it also
     removed an OVER-report, because reading `employee_id` out of
     `session.employee_id` had made a SESSION branch read CALLER.

CRITERIA ARE LOCKED BEFORE THE REAL FILE IS READ: --selftest runs the fixtures
and a non-zero exit from it is a refusal to report a census at all.

  python branch_census.py --selftest     fixtures only, both directions
  python branch_census.py --ablate       per-RULE, per-FIXTURE contribution
  python branch_census.py --why          per-LINE reason for every UNRESOLVED
  python branch_census.py                the census (selftest first)

ON "0 UNRESOLVED": the third state is still reachable and still tested -- a name
declared nowhere, a function with no call sites, and a call with fewer arguments
than the position each still report UNRESOLVED as fixtures. Zero is a measured
result from a mechanism that can still say it, not the state being retired.
"""
import io
import os
import re
import sys

CRITERIA_VERSION = '2026-10-16.b27r.1'
REPO = r'C:\Users\marsh\Documents\SAIRN-fourth'
SRC = os.path.join(REPO, 'api', 'sd-data.js')

BOTH = re.compile(r'(\w+)\.status\s*===\s*404\s*\|\|\s*\1\.status\s*===\s*400')
METHOD = re.compile(r"method:\s*'(POST|PATCH|DELETE|PUT)'")
FETCH_ANY = re.compile(r'await\s+fetch\s*\(')
IDENT = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')

# Identifiers that are the SERVER's own by construction. Anything derived from
# these is server-only however many hops away it is.
SERVER_ROOTS = frozenset([
    'licHash', 'lh', 'APP', 'app', 'nowISO', 'enc', 'rest', 'headers',
    'String', 'Number', 'JSON', 'Math', 'Object', 'Array', 'Date', 'Boolean',
])
CALLER_ROOTS = frozenset(['payload', 'body', 'req', 'q', 'query'])
SESSION_ROOTS = frozenset(['session', 'lawSess', 'sess', 'sfSess', 'senSess',
                           'alfSess', 'svSess', 'legSess'])
# Words that appear inside a URL string but are not identifiers to trace.
NOISE = frozenset(['select', 'eq', 'order', 'limit', 'and', 'or', 'not',
                   'on_conflict', 'desc', 'asc', 'is', 'in', 'true', 'false',
                   'null', 'headers', 'method', 'Prefer', 'body'])

# ── R6 (b27 resume). A ROOT IS NEVER DISCARDED AS NOISE ──────────────────────
# `body` is in CALLER_ROOTS *and* in NOISE, and NOISE was filtered first, so
# every walk that reached `body` dropped it before the root lookup could answer
# CALLER. api/sd-data.js:748 is `const resource = body && body.resource;`, so
# `resource` -- the identifier that stalled 16 of the 19 class-C UNRESOLVED
# lines -- could never resolve, however wide the lookback window was made.
# `headers` is in SERVER_ROOTS and NOISE for the same reason and had the same
# treatment; it was invisible because dropping the only name on a right-hand
# side falls through to "assigned from a literal" -> SERVER, which happened to
# be the right answer for the wrong reason.
#
# NOISE exists for words that appear inside a URL *string* -- `select`, `eq`,
# `order`. A name this census has already declared to be a root is not one of
# those, and three of the eleven NOISE words are roots.
ROOTS = CALLER_ROOTS | SESSION_ROOTS | SERVER_ROOTS

# ── R7 (b27 resume). A JAVASCRIPT KEYWORD IS NOT AN IDENTIFIER ───────────────
# The IDENT regex is `[A-Za-z_$][A-Za-z0-9_$]*`, which matches `new`, `await`
# and `typeof` exactly as readily as a variable name. The LAST remaining
# UNRESOLVED line in api/sd-data.js is :6023, whose only traced names come from
#     const month = new Date().toISOString().slice(0, 7);
# `Date` is a SERVER_ROOT and answers SERVER; `new` is a keyword that resolves
# to nothing, so the right-hand side was MIXED and the branch was reported as
# a third state. Nothing about that line is unresolvable -- the walk was
# tracing a keyword.
#
# THIS IS DELIBERATELY NOT FOLDED INTO NOISE. NOISE is a list of words that
# appear inside a URL string; these are grammar. Keeping them apart is what
# lets --ablate say which of the two bought the resolution.
KEYWORDS = frozenset([
    'new', 'await', 'typeof', 'instanceof', 'void', 'delete', 'return',
    'function', 'async', 'of', 'this', 'undefined', 'NaN', 'Infinity',
])


def keep(n, rules):
    """R6: a root survives the NOISE filter. R7: a keyword is never traced."""
    if getattr(rules, 'r7', True) and n in KEYWORDS:
        return False
    if getattr(rules, 'r6', True) and n in ROOTS:
        return True
    return n not in NOISE


# R7's other half, and the half that actually closed :6023. `new` was only the
# first of FOUR names the walk pulled out of
#     const month = new Date().toISOString().slice(0, 7);
# -- the other three were `Date` (a root, fine), `toISOString` and `slice`,
# which are PROPERTY NAMES on a member expression and are declared nowhere, so
# the right-hand side stayed MIXED even once the keyword was dropped. A name
# after a dot is not a variable this census can trace and never was; the same
# strip is what makes `body.resource` answer from `body` alone.
DOTTED = re.compile(r'\.\s*[A-Za-z_$][\w$]*')


def trace_names(expr, rules):
    """The identifiers in `expr` whose ORIGIN is worth walking."""
    if getattr(rules, 'r7', True):
        expr = DOTTED.sub(' ', expr)
    return [n for n in IDENT.findall(expr) if keep(n, rules)]


# ── RULE TOGGLES, so --ablate can remove ONE and measure what it alone buys ──
class Rules(object):
    def __init__(self, r1=True, r2=True, r3=True, r4=True, r5=True,
                 r6=True, r7=True):
        self.r1 = r1   # span bounded at the next fetch
        self.r2 = r2   # guard-to-fetch binding stops at another variable's fetch
        self.r3 = r3   # follow a caller value through assignments
        self.r4 = r4   # resolve a PARAMETER across its call sites (b27)
        self.r6 = r6   # a ROOT is never discarded as URL noise (b27 resume)
        self.r7 = r7   # a JS KEYWORD is not an identifier (b27 resume)
        self.r5 = r5   # the declaration lookback is bounded by SCOPE, not by a
        #                line count, and a parameter SHADOWS an outer
        #                declaration (b27 resume)


def find_assignment(lines, idx, var, rules):
    """Nearest backward `const/let/var <var> = await fetch(`.

    R2: the walk stops if it meets `await fetch(` assigned to a DIFFERENT
    variable first -- that fetch's guard is not this one's.
    """
    assign = re.compile(r'\b(?:const|let|var)\s+' + re.escape(var)
                        + r'\s*=\s*await\s+fetch\s*\(')
    other = re.compile(r'\b(?:const|let|var)\s+(?!' + re.escape(var)
                       + r'\b)[A-Za-z_$][\w$]*\s*=\s*await\s+fetch\s*\(')
    for j in range(idx, max(0, idx - 60), -1):
        if assign.search(lines[j]):
            return j
        if rules.r2 and other.search(lines[j]):
            return None
    return None


def span(lines, start, guard_idx, rules):
    """The lines belonging to the fetch assigned at `start`.

    R1: ends at the next `await fetch(` or at the guard, whichever is first.
    Without R1 it is a flat 14-line window, which is the b24 bug.
    """
    if not rules.r1:
        return lines[start:min(len(lines), start + 14)]
    end = guard_idx
    for j in range(start + 1, guard_idx):
        if FETCH_ANY.search(lines[j]):
            end = j
            break
    return lines[start:max(end, start + 1)]


def url_idents(blob, rules=None):
    """Identifiers interpolated into the URL expression of a rest(...) call.

    ── R7's THIRD SITE, AND IT WAS AN OVER-REPORT. 2026-10-16, b27 resume ────
    This function had its OWN name filter -- NOISE plus `enc`/`String`/
    `encodeURIComponent` -- and did not strip property names. So
    api/sd-data.js:13364 interpolates `enc(String(session.employee_id))`, the
    walk pulled out `employee_id` as if it were a variable, resolved THAT
    somewhere else in the file, and the branch was reported CALLER when its
    only caller-facing name is a SESSION root. Found by spot-checking the
    newly-resolved lines in the OVER-reporting direction, which is the only
    direction that finds this: every under-report had already gone to zero.

    It now shares `trace_names`, so R6 and R7 apply here identically. `enc` and
    `String` are SERVER_ROOTS and so resolve to SERVER rather than being
    dropped, which is the same verdict by a stated route.
    """
    m = re.search(r'rest\s*\(', blob)
    if not m:
        return []
    i = m.end()
    depth = 1
    out = []
    while i < len(blob) and depth > 0:
        c = blob[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        i += 1
    expr = blob[m.end():i - 1]
    # drop string literals -- a URL's own text is not an identifier
    expr = re.sub(r"'[^']*'", " ", expr)
    expr = re.sub(r'"[^"]*"', " ", expr)
    for name in trace_names(expr, rules or Rules()):
        if name == 'encodeURIComponent':
            continue
        out.append(name)
    return out


# ── R4, THE INTER-PROCEDURAL HALF (b27) ──────────────────────────────────────
# b26 reported 26 identifiers UNRESOLVED and named the reason: `origin()` is
# intra-procedural, so a FUNCTION PARAMETER has no `const <name> =` to find.
# One of the 26 was resolved BY HAND -- api/sd-data.js:10556's `jobId` is a
# parameter of `rfJobGate`, whose call sites at :10612 and :10746 both pass
# `payload.job_id` -- which proved the third state was right and that the
# population was not empty. THIS CLOSES IT MECHANICALLY.
#
# A PARAMETER IS RESOLVED BY UNIONING ITS CALL SITES, and the union is
# DELIBERATELY UNSAFE-WINS: one call site passing a caller value makes the
# parameter CALLER even if nine others pass the server's own. A reachable path
# is reachable.
#
# WHEN IT STILL CANNOT TELL IT SAYS SO. No enclosing function, a parameter list
# it cannot parse, a function with NO call sites, or an argument whose own
# origin is unresolved -- each stays UNRESOLVED rather than defaulting to
# SERVER, which is the same third-state rule R3 exists for, one level out.


def _split_args(text):
    """Top-level comma split, so an argument containing (), [] or {} survives."""
    out, depth, cur = [], 0, ''
    for ch in text:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def enclosing_function(lines, idx):
    """-> (fname, [params], decl_idx) for the nearest function declaration at
    or above idx whose parameter list parses. Bounded to 400 lines."""
    pat = re.compile(
        r'(?:function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\))'
        r'|(?:(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?'
        r'(?:function\s*)?\(([^)]*)\)\s*(?:=>|\{))')
    for j in range(idx, max(0, idx - 400), -1):
        m = pat.search(lines[j])
        if not m:
            continue
        fname = m.group(1) or m.group(3)
        raw = m.group(2) if m.group(1) else m.group(4)
        if not fname:
            continue
        params = [x.strip() for x in _split_args(raw or '')]
        return fname, params, j
    return None, None, None


def origin_via_params(lines, name, from_idx, rules, hops, seen):
    """R4. UNRESOLVED unless a parameter can be tied to real call sites."""
    fname, params, decl = enclosing_function(lines, from_idx)
    if not fname or name not in params:
        return 'UNRESOLVED'
    pos = params.index(name)
    call = re.compile(r'(?<![\w$.])' + re.escape(fname) + r'\s*\(')
    verdicts = []
    for j, line in enumerate(lines):
        if j == decl or line.lstrip().startswith(('//', '*')):
            continue
        m = call.search(line)
        if not m:
            continue
        # the argument list, paren-balanced from the call
        i, depth, buf = m.end(), 1, ''
        while i < len(line) and depth > 0:
            if line[i] == '(':
                depth += 1
            elif line[i] == ')':
                depth -= 1
                if depth == 0:
                    break
            buf += line[i]
            i += 1
        if depth != 0:
            verdicts.append('UNRESOLVED')     # a call spanning lines: say so
            continue
        args = _split_args(buf)
        if pos >= len(args):
            verdicts.append('UNRESOLVED')     # called with fewer arguments
            continue
        arg = re.sub(r"'[^']*'", ' ', args[pos])
        arg = re.sub(r'"[^"]*"', ' ', arg)
        names = trace_names(arg, rules)
        if not names:
            verdicts.append('SERVER')         # a literal
            continue
        sub = [origin(lines, n, j, rules, hops + 1, set(seen)) for n in names]
        if 'CALLER' in sub:
            verdicts.append('CALLER')
        elif 'SESSION' in sub:
            verdicts.append('SESSION')
        elif all(v == 'SERVER' for v in sub):
            verdicts.append('SERVER')
        else:
            verdicts.append('UNRESOLVED')
    if not verdicts:
        return 'UNRESOLVED'                   # declared and never called
    # UNSAFE WINS. One reachable call site is enough.
    if 'CALLER' in verdicts:
        return 'CALLER'
    if 'SESSION' in verdicts:
        return 'SESSION'
    if all(v == 'SERVER' for v in verdicts):
        return 'SERVER'
    return 'UNRESOLVED'


def origin(lines, name, from_idx, rules, hops=0, seen=None):
    """CALLER / SESSION / SERVER / UNRESOLVED for one identifier.

    R3 is the transitive walk. With R3 off this only answers from the name
    itself, which is the b23 behaviour and is what makes CALLER a lower bound.
    """
    seen = seen or set()
    if name in seen or hops > 6:
        return 'UNRESOLVED'
    seen.add(name)
    if name in CALLER_ROOTS:
        return 'CALLER'
    if name in SESSION_ROOTS:
        return 'SESSION'
    if name in SERVER_ROOTS:
        return 'SERVER'
    if not rules.r3:
        return 'SERVER'          # the b23 `else` branch, kept so --ablate can measure it
    # ── R5. A PARAMETER SHADOWS ANY OUTER DECLARATION, so it is asked FIRST,
    #    before the lookback can walk past it into an unrelated binding. With
    #    R5 off the old order is restored and --ablate measures the difference.
    if rules.r5 and rules.r4:
        fn, ps, _d = enclosing_function(lines, from_idx)
        if fn and ps and name in ps:
            return origin_via_params(lines, name, from_idx, rules, hops,
                                     set(seen))
    assign = re.compile(r'\b(?:const|let|var)\s+' + re.escape(name)
                        + r'\s*=\s*(.+)$')
    # ── R5. THE LOOKBACK IS NOT 400 LINES. api/sd-data.js:748 declares
    #    `const resource = body && body.resource;` ONE TIME for a handler that
    #    runs to :18867, and `resource` was the stalling identifier on 16 of
    #    the 19 class-C UNRESOLVED lines. A 400-line cap made a CALLER value
    #    unreachable for 14,000 lines -- which is b23's 14-line window and
    #    b24's fixed window a third time, inside the rule built to kill them.
    lookback = 0 if rules.r5 else max(0, from_idx - 400)
    for j in range(from_idx, lookback - 1 if rules.r5 else lookback, -1):
        mm = assign.search(lines[j])
        if not mm:
            continue
        rhs = mm.group(1)
        rhs = re.sub(r"'[^']*'", " ", rhs)
        rhs = re.sub(r'"[^"]*"', " ", rhs)
        names = trace_names(rhs, rules)
        if not names:
            return 'SERVER'      # assigned from a literal
        verdicts = [origin(lines, n, j, rules, hops + 1, seen) for n in names]
        for want in ('CALLER', 'SESSION'):
            if want in verdicts:
                return want
        if all(v == 'SERVER' for v in verdicts):
            return 'SERVER'
        return 'UNRESOLVED'
    # NO ASSIGNMENT FOUND. b26 stopped here and said UNRESOLVED, naming the
    # parameter case as the reason. R4 now tries the call sites; with R4 off
    # this returns the b26 answer unchanged, which is what --ablate measures.
    if rules.r4:
        return origin_via_params(lines, name, from_idx, rules, hops, seen or set())
    return 'UNRESOLVED'


def census(text, rules=None):
    rules = rules or Rules()
    lines = text.split('\n')
    rows = []
    for i, l in enumerate(lines):
        if l.lstrip().startswith(('//', '*')):
            continue
        m = BOTH.search(l)
        if not m:
            continue
        var = m.group(1)
        win5 = ' '.join(lines[i:i + 5])
        if re.search(r'\bnotProvisioned\s*\(', win5):
            shape = 'A-helper'
        elif 'NOT_PROVISIONED' in win5:
            shape = 'B-inline-503'
        elif 'provisioned: false' in win5:
            shape = 'C-200-empty'
        else:
            shape = 'other'
        start = find_assignment(lines, i, var, rules)
        if start is None:
            rows.append({'line': i + 1, 'var': var, 'shape': shape,
                         'method': None, 'influence': None,
                         'state': 'UNCLASSIFIED'})
            continue
        blob = ' '.join(span(lines, start, i, rules))
        mm = METHOD.search(blob)
        method = mm.group(1) if mm else 'GET'
        names = url_idents(blob, rules)
        verdicts = [origin(lines, n, start, rules) for n in names]
        if 'CALLER' in verdicts:
            influence = 'CALLER'
        elif 'SESSION' in verdicts:
            influence = 'SESSION'
        elif 'UNRESOLVED' in verdicts:
            influence = 'UNRESOLVED'
        else:
            influence = 'SERVER-ONLY'
        rows.append({'line': i + 1, 'var': var, 'shape': shape,
                     'method': method, 'influence': influence,
                     'state': 'OK', 'fetch_line': start + 1,
                     'idents': names})
    return rows


# ═══════════════════════ FIXTURES, BOTH DIRECTIONS ═══════════════════════════
# Each fixture is (name, source, expected). Locked BEFORE the real file is read.
F = []

# THE REAL SHAPE at api/sd-data.js:5061-5072, which b24 typed as a POST: the
# pre-write GET, its own guard immediately after it, and the real upsert
# ELEVEN LINES LATER -- inside a flat 14-line window and outside a window
# bounded at the next fetch. The fixture is the shipped layout, not a
# convenient one: an earlier draft put the guard AFTER the upsert, which is a
# shape this file does not contain, and it failed for that reason.
F.append(('R1 a pre-write GET with the upsert 11 lines later is a GET', """
      const existingPhoto = await fetch(rest('grd_photos?license_hash=eq.' + enc(licHash)), { headers });
      if (existingPhoto.status === 404 || existingPhoto.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED' } });
        return;
      }
      const exRows = await existingPhoto.json();
      if (Array.isArray(exRows) && exRows.length) {
        res.status(409).json({ error: { code: 'ALREADY' } });
        return;
      }
      const row = { license_hash: licHash, data: storedBlob(payload, []) };
      const w = await fetch(rest('grd_photos?on_conflict=license_hash'), {
        method: 'POST',
        headers: headers
      });
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R1 the OPPOSITE: a real write branch is still a POST', """
      const w = await fetch(rest('alf_op_audits?on_conflict=license_hash'), {
        method: 'POST',
        headers: headers
      });
      if (w.status === 404 || w.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED' } });
      }
""", {'method': 'POST', 'influence': 'SERVER-ONLY'}))

F.append(('R2 a guard binds to ITS OWN variable, not the nearest fetch', """
      const a = await fetch(rest('t_a?license_hash=eq.' + enc(licHash)), { headers });
      const b = await fetch(rest('t_b?on_conflict=x'), { method: 'POST', headers: headers });
      if (a.status === 404 || a.status === 400) {
        res.status(503).json({ error: { code: 'NOT_PROVISIONED' } });
      }
""", {'method': 'UNCLASSIFIED'}))

F.append(('R3 a caller value arriving DIRECTLY is CALLER', """
      const r = await fetch(rest('t?license_hash=eq.' + enc(licHash) + '&id=eq.' + enc(payload.id)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R3 THE ONE b23 MISSED: a caller value through a VARIABLE is CALLER', """
      const jobId = payload.job_id;
      const r = await fetch(rest('t?license_hash=eq.' + enc(licHash) + '&job_id=eq.' + enc(jobId)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R3 TWO hops still reaches CALLER', """
      const raw = payload.job_id;
      const jobId = String(raw);
      const r = await fetch(rest('t?job_id=eq.' + enc(jobId)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R3 THE OPPOSITE: a server value through a variable stays SERVER-ONLY', """
      const own = enc(licHash);
      const r = await fetch(rest('t?license_hash=eq.' + own), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R3 a SESSION value is SESSION, not CALLER and not SERVER', """
      const r = await fetch(rest('t?emp=eq.' + enc(session.employee_id)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'SESSION'}))

F.append(('R3 THE THIRD STATE: an unresolvable identifier is UNRESOLVED, '
          'never SERVER-ONLY', """
      const r = await fetch(rest('t?x=eq.' + enc(mysteryFromAParameter)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
      }
""", {'method': 'GET', 'influence': 'UNRESOLVED'}))

F.append(('a commented-out guard is not a branch', """
      // if (r.status === 404 || r.status === 400) {
""", {'none': True}))


# ── R4 FIXTURES, BOTH DIRECTIONS (b27) ──────────────────────────────────────
# The dispatch asked for a fixture proving a RESOLUTION and a fixture proving
# the same case WOULD HAVE BEEN MISSED. The second is --ablate's job: with R4
# off, F-R4a must fall back to UNRESOLVED, and the ablation prints that it does.
# The over-report direction needs its own fixtures and gets three.

# THE REAL SHAPE at api/sd-data.js:10556, the one b26 resolved BY HAND.
F.append(('R4 a PARAMETER resolved to CALLER through its call site', """
      const rfJobGate = async (lh, hdrs, jobId, session, response) => {
        const jr = await fetch(rest('rf_jobs?license_hash=eq.' + enc(lh) + '&job_id=eq.' + enc(jobId)), { headers: hdrs });
        if (jr.status === 404 || jr.status === 400) {
          res.status(200).json({ ok: true, data: [], provisioned: false });
          return;
        }
      };
      const gate = await rfJobGate(licHash, headers, payload.job_id, session, res);
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R4 THE OVER-REPORT DIRECTION: every call site passes the server own '
          'licence hash, so SERVER-ONLY', """
      const ownGate = async (lh, hdrs) => {
        const r = await fetch(rest('t?license_hash=eq.' + enc(lh)), { headers: hdrs });
        if (r.status === 404 || r.status === 400) {
          res.status(200).json({ ok: true, data: [], provisioned: false });
          return;
        }
      };
      const g1 = await ownGate(licHash, headers);
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R4 CALL SITES DISAGREE -- UNSAFE WINS, one reachable path is enough',
          """
      const twoGate = async (lh, hdrs, who) => {
        const r = await fetch(rest('t?x=eq.' + enc(who)), { headers: hdrs });
        if (r.status === 404 || r.status === 400) {
          res.status(200).json({ ok: true, data: [], provisioned: false });
          return;
        }
      };
      const a1 = await twoGate(licHash, headers, licHash);
      const a2 = await twoGate(licHash, headers, payload.who);
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R4 A FUNCTION WITH NO CALL SITES STAYS UNRESOLVED, not SERVER', """
      const lonelyGate = async (lh, hdrs, thing) => {
        const r = await fetch(rest('t?x=eq.' + enc(thing)), { headers: hdrs });
        if (r.status === 404 || r.status === 400) {
          res.status(200).json({ ok: true, data: [], provisioned: false });
          return;
        }
      };
""", {'method': 'GET', 'influence': 'UNRESOLVED'}))

F.append(('R4 CALLED WITH FEWER ARGUMENTS than the position -- UNRESOLVED', """
      const shortGate = async (lh, hdrs, thing) => {
        const r = await fetch(rest('t?x=eq.' + enc(thing)), { headers: hdrs });
        if (r.status === 404 || r.status === 400) {
          res.status(200).json({ ok: true, data: [], provisioned: false });
          return;
        }
      };
      const s1 = await shortGate(licHash, headers);
""", {'method': 'GET', 'influence': 'UNRESOLVED'}))

# ── R5 FIXTURES (b27 resume) ────────────────────────────────────────────────
# THE REAL SHAPE: api/sd-data.js:748 is `const resource = body && body.resource;`
# and the guards that read it run as far as :18359. A 400-line lookback cannot
# see 14,000 lines, so `resource` -- a CALLER value with a one-line declaration
# -- was the stalling identifier on 16 of the 19 class-C UNRESOLVED lines. The
# first fixture is that shape at reduced scale; the rest are the directions it
# must NOT get wrong.
F.append(('R5 A DECLARATION FAR ABOVE THE 400-LINE CAP IS STILL FOUND -- the '
          'sd-data.js:748 `resource` shape', """
      const resource = body && body.resource;
""" + '      // filler\n' * 520 + """
      const r = await fetch(rest('t?sel=eq.' + enc(resource)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R5 THE OPPOSITE: a SERVER declaration far above stays SERVER-ONLY, '
          'so the widened window does not invent reachability', """
      const resource = licHash;
""" + '      // filler\n' * 520 + """
      const r = await fetch(rest('t?sel=eq.' + enc(resource)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R5 THE SHADOWING DIRECTION: a PARAMETER wins over an outer '
          'declaration of the same name, and is resolved by ITS call sites', """
      const thing = body && body.thing;
      const gate = async (lh, hdrs, thing) => {
        const r = await fetch(rest('t?x=eq.' + enc(thing)), { headers: hdrs });
        if (r.status === 404 || r.status === 400) {
          res.status(200).json({ ok: true, data: [], provisioned: false });
          return;
        }
      };
      const s1 = await gate(licHash, headers, nowISO);
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R6 A ROOT SURVIVES THE NOISE FILTER -- the sd-data.js:748 shape '
          '`const resource = body && body.resource`, where `body` is a '
          'CALLER_ROOT *and* a NOISE word', """
      const resource = body && body.resource;
      const r = await fetch(rest('t?sel=eq.' + enc(resource)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R6 THE OPPOSITE: rescuing roots does NOT turn a server right-hand '
          'side into a caller one -- `headers` is a root and a NOISE word too', """
      const resource = headers;
      const r = await fetch(rest('t?sel=eq.' + enc(resource)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R6 AND A REAL NOISE WORD IS STILL NOISE -- `on_conflict` is not a '
          'root and must not become a traceable name', """
      const resource = on_conflict;
      const r = await fetch(rest('t?sel=eq.' + enc(resource)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R7 A KEYWORD IS NOT TRACED -- the sd-data.js:6023 shape '
          '`const month = new Date().toISOString()`, whose only non-keyword '
          'name is a SERVER root', """
      const month = new Date().toISOString().slice(0, 7);
      const r = await fetch(rest('t?month=eq.' + enc(month)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'SERVER-ONLY'}))

F.append(('R7 THE OPPOSITE: dropping the keyword does NOT drop what the '
          'expression actually reads -- a caller value inside a `new` is '
          'still CALLER', """
      const month = new Date(payload.when).toISOString().slice(0, 7);
      const r = await fetch(rest('t?month=eq.' + enc(month)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R7 IN THE URL TOO -- the sd-data.js:13364 shape '
          '`enc(String(session.employee_id))` is SESSION, and reading the '
          'PROPERTY name as a variable is what made it read CALLER', """
      const ar = await fetch(rest('alf_clients?license_hash=eq.' + enc(licHash)
        + '&assigned_employee_id=eq.' + enc(String(session.employee_id))
        + '&select=client_id'), { headers });
      if (ar.status === 404 || ar.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'SESSION'}))

F.append(('R7 AND ITS MIRROR: the SAME shape with a caller object is still '
          'CALLER -- the strip removes the property, never the object', """
      const ar = await fetch(rest('alf_clients?license_hash=eq.' + enc(licHash)
        + '&assigned_employee_id=eq.' + enc(String(payload.employee_id))
        + '&select=client_id'), { headers });
      if (ar.status === 404 || ar.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'CALLER'}))

F.append(('R5 AND IT IS STILL A THIRD STATE: a name declared NOWHERE in the '
          'whole file stays UNRESOLVED, however wide the window', """
      const r = await fetch(rest('t?sel=eq.' + enc(neverDeclared)), { headers });
      if (r.status === 404 || r.status === 400) {
        res.status(200).json({ ok: true, data: [], provisioned: false });
        return;
      }
""", {'method': 'GET', 'influence': 'UNRESOLVED'}))


def selftest(verbose=True):
    bad = 0
    if verbose:
        print('FIXTURES -- criteria %s' % CRITERIA_VERSION)
    for name, src, want in F:
        rows = census(src)
        if want.get('none'):
            ok = (len(rows) == 0)
            got = '%d row(s)' % len(rows)
        elif not rows:
            ok, got = False, 'NO ROW FOUND'
        elif want.get('method') == 'UNCLASSIFIED':
            ok = rows[0]['state'] == 'UNCLASSIFIED'
            got = rows[0]['state']
        else:
            r = rows[0]
            ok = (r['state'] == 'OK' and r['method'] == want['method']
                  and r['influence'] == want['influence'])
            got = '%s/%s/%s' % (r['state'], r['method'], r['influence'])
        if not ok:
            bad += 1
        if verbose:
            print('  %-4s %-62s got %s' % ('ok' if ok else 'FAIL', name[:62], got))
    if verbose:
        print('  %d/%d fixtures classify correctly' % (len(F) - bad, len(F)))
    return bad


def ablate():
    """Per RULE, per ARM. Not per exit code -- an exit code hides which arm
    each rule was actually buying."""
    print('ABLATION -- one rule removed at a time, measured PER FIXTURE')
    print('criteria %s' % CRITERIA_VERSION)
    print('')
    base = {}
    for name, src, want in F:
        base[name] = census(src)
    for label, rules in (('R1 span-bounded-at-next-fetch', Rules(r1=False)),
                         ('R2 guard-binds-to-own-variable', Rules(r2=False)),
                         ('R3 follow-caller-through-assignments', Rules(r3=False)),
                         ('R4 resolve-a-parameter-across-call-sites', Rules(r4=False)),
                         ('R5 scope-bounded-lookback-and-param-shadowing', Rules(r5=False)),
                         ('R6 a-root-is-never-discarded-as-noise', Rules(r6=False)),
                         ('R7 a-js-keyword-is-not-an-identifier', Rules(r7=False))):
        broke = []
        for name, src, want in F:
            rows = census(src, rules)
            a, b = base[name], rows
            same = (len(a) == len(b)
                    and all(x.get('method') == y.get('method')
                            and x.get('influence') == y.get('influence')
                            and x.get('state') == y.get('state')
                            for x, y in zip(a, b)))
            if not same:
                got = (b[0]['state'] + '/' + str(b[0].get('method')) + '/'
                       + str(b[0].get('influence'))) if b else 'NO ROW'
                broke.append((name, got))
        print('  WITHOUT %-38s %d fixture(s) change' % (label, len(broke)))
        for n, g in broke:
            print('      %-60s -> %s' % (n[:60], g))
        if not broke:
            print('      NONE -- THIS RULE IS NOT LOAD-BEARING ON ANY FIXTURE,')
            print('      which is a finding about the fixtures, not a pass.')
    print('')


# ── --why: WHAT IS STILL UNRESOLVED, AND BY WHICH IDENTIFIER (b27 resume) ────
# R4 moved the UNRESOLVED population from 26 to 20 and the three that survive in
# class B/other were not the interesting half -- NINETEEN of the twenty are in
# class C and R4 did not touch any of them. A bucket of 20 that nobody can take
# apart is the same lower bound R3 was built to kill, one level further in, so
# this mode names PER LINE the identifier that stalled the walk and the reason
# it stalled.
#
# IT DOES NOT TOUCH `origin`. The classifier is criteria-locked and its fixtures
# pass; a diagnosis that changed the thing it is diagnosing would be worthless.
# `diagnose` MIRRORS origin's decision path and returns (verdict, reason), and
# the `--why` run asserts the mirrored verdict EQUALS origin's for every
# identifier it reports -- a divergence is printed as MIRROR DIVERGED and is a
# defect in this diagnostic, never a re-classification of the census.

REASONS = {
    'ROOT': 'a known root -- answered without a walk',
    'CYCLE': 'the walk revisited a name it had already taken (cycle) or passed '
             '6 hops',
    'MIXED-RHS': 'assigned from an expression mixing a SERVER name with one '
                 'this walk cannot trace',
    'NO-DECL-NO-FN': 'no declaration in the 400-line lookback AND no enclosing '
                     'function declaration parsed, so it is not even a '
                     'parameter candidate',
    'NOT-A-PARAM': 'no declaration in the 400-line lookback, and it is not in '
                   'the enclosing function\'s parameter list -- an outer-scope '
                   'or hoisted name',
    'PARAM-NO-CALLS': 'a parameter, but no call site of its function was found',
    'PARAM-MIXED': 'a parameter whose call sites do not agree and not one of '
                   'them reaches CALLER or SESSION',
}


def diagnose(lines, name, from_idx, rules, hops=0, seen=None):
    """Mirror of origin(), returning (verdict, reason_key, detail)."""
    seen = seen or set()
    if name in seen or hops > 6:
        return 'UNRESOLVED', 'CYCLE', name
    seen.add(name)
    if name in CALLER_ROOTS:
        return 'CALLER', 'ROOT', name
    if name in SESSION_ROOTS:
        return 'SESSION', 'ROOT', name
    if name in SERVER_ROOTS:
        return 'SERVER', 'ROOT', name
    if not rules.r3:
        return 'SERVER', 'ROOT', name
    if rules.r5 and rules.r4:
        fn0, ps0, _d0 = enclosing_function(lines, from_idx)
        if fn0 and ps0 and name in ps0:
            v0 = origin_via_params(lines, name, from_idx, rules, hops,
                                   set(seen))
            if v0 != 'UNRESOLVED':
                return v0, 'ROOT', name
            return ('UNRESOLVED', 'PARAM-MIXED',
                    '%s (param of %s, shadows any outer decl)' % (name, fn0))
    assign = re.compile(r'\b(?:const|let|var)\s+' + re.escape(name)
                        + r'\s*=\s*(.+)$')
    lookback = 0 if rules.r5 else max(0, from_idx - 400)
    for j in range(from_idx, lookback - 1 if rules.r5 else lookback, -1):
        mm = assign.search(lines[j])
        if not mm:
            continue
        rhs = re.sub(r'"[^"]*"', ' ', re.sub(r"'[^']*'", ' ', mm.group(1)))
        names = trace_names(rhs, rules)
        if not names:
            return 'SERVER', 'ROOT', name
        subs = [diagnose(lines, n, j, rules, hops + 1, seen) for n in names]
        vs = [s[0] for s in subs]
        for want in ('CALLER', 'SESSION'):
            if want in vs:
                return want, 'ROOT', name
        if all(v == 'SERVER' for v in vs):
            return 'SERVER', 'ROOT', name
        stalled = [s for s in subs if s[0] == 'UNRESOLVED']
        return ('UNRESOLVED', 'MIXED-RHS',
                '%s <- %s (%s at :%d)' % (name, stalled[0][2],
                                          stalled[0][1], j + 1))
    if not rules.r4:
        return 'UNRESOLVED', 'NOT-A-PARAM', name
    fname, params, decl = enclosing_function(lines, from_idx)
    if not fname:
        return 'UNRESOLVED', 'NO-DECL-NO-FN', name
    if name not in params:
        return 'UNRESOLVED', 'NOT-A-PARAM', '%s (in %s)' % (name, fname)
    v = origin_via_params(lines, name, from_idx, rules, hops, set(seen))
    if v != 'UNRESOLVED':
        return v, 'ROOT', name
    call = re.compile(r'(?<![\w$.])' + re.escape(fname) + r'\s*\(')
    sites = [j + 1 for j, l in enumerate(lines)
             if j != decl and not l.lstrip().startswith(('//', '*'))
             and call.search(l)]
    if not sites:
        return 'UNRESOLVED', 'PARAM-NO-CALLS', '%s (param of %s)' % (name, fname)
    return ('UNRESOLVED', 'PARAM-MIXED',
            '%s (param of %s, call sites %s)'
            % (name, fname, ', '.join(':%d' % s for s in sites[:6])))


def why(rows, lines, rules):
    unres = [r for r in rows
             if r['state'] == 'OK' and r['method'] == 'GET'
             and r['influence'] == 'UNRESOLVED']
    print('WHY THE REMAINING UNRESOLVED LINES ARE UNRESOLVED -- %d line(s)'
          % len(unres))
    print('criteria %s, mirrored from origin() and cross-checked against it'
          % CRITERIA_VERSION)
    print('')
    diverged = 0
    tally = {}
    for r in unres:
        print('  :%-6d %s' % (r['line'], r['shape']))
        for n in r['idents']:
            truth = origin(lines, n, r['fetch_line'] - 1, rules)
            v, key, detail = diagnose(lines, n, r['fetch_line'] - 1, rules)
            if v != truth:
                diverged += 1
                print('       MIRROR DIVERGED on %-18s origin=%s diagnose=%s'
                      % (n, truth, v))
                continue
            if v != 'UNRESOLVED':
                continue
            tally[key] = tally.get(key, 0) + 1
            print('       %-14s %s' % (key, detail[:96]))
            print('                      %s' % REASONS[key])
    print('')
    print('BY REASON:')
    for k in sorted(tally, key=lambda x: -tally[x]):
        print('  %-16s %d' % (k, tally[k]))
    print('')
    if diverged:
        print('COULD NOT RUN CLEANLY: the mirror diverged from origin() on %d'
              % diverged)
        print('identifier(s). The reasons above are NOT trustworthy; fix the')
        print('mirror before quoting any of them. Exit 2.')
        return 2
    print('MIRROR AGREED WITH origin() ON EVERY IDENTIFIER REPORTED, so each')
    print('reason above describes the decision the census actually made.')
    print('')
    print('NONE OF THIS RECLASSIFIES ANYTHING. A reason is not a resolution:')
    print('every line above is still UNRESOLVED and is still NOT SERVER-ONLY.')
    return 0


def main(argv):
    if '--selftest' in argv:
        return 1 if selftest() else 0
    if '--ablate' in argv:
        bad = selftest()
        print('')
        if bad:
            print('COULD NOT RUN: the fixtures failed, so an ablation over them')
            print('would measure a broken classifier. Nothing was ablated.')
            return 2
        ablate()
        return 0
    bad = selftest()
    print('')
    if bad:
        print('COULD NOT RUN: %d fixture(s) failed, so NO CENSUS IS REPORTED.' % bad)
        print('A classifier that cannot pass its own locked criteria produces a')
        print('number nobody can use. This is exit 2, not a census with a caveat.')
        return 2
    if not os.path.isfile(SRC):
        print('COULD NOT RUN: %s does not exist. Nothing was measured.' % SRC)
        return 2
    text = io.open(SRC, encoding='utf-8').read()
    lines = text.split('\n')
    rows = census(text)
    if '--why' in argv:
        return why(rows, lines, Rules())
    from collections import Counter
    print('SOURCE api/sd-data.js, %d lines (split on newline)' % len(lines))
    print('GUARDS MATCHING (\\w+).status === 404 || \\1.status === 400 : %d'
          % len(rows))
    print('')
    for k, v in sorted(Counter(r['shape'] for r in rows).items()):
        print('  shape %-14s %d' % (k, v))
    print('')
    for shape in ('B-inline-503', 'C-200-empty', 'A-helper', 'other'):
        sub = [r for r in rows if r['shape'] == shape]
        if not sub:
            continue
        wr = [r for r in sub if r['state'] == 'OK' and r['method'] != 'GET']
        gd = [r for r in sub if r['state'] == 'OK' and r['method'] == 'GET']
        unk = [r for r in sub if r['state'] != 'OK']
        print('%s -- %d branch(es)' % (shape, len(sub)))
        print('  WRITE-guarded (POST/PATCH/DELETE) -> can receive a 23xxx : %d'
              % len(wr))
        if wr:
            print('     lines: %s' % ', '.join(':%d' % r['line'] for r in wr))
        print('  GET-guarded                                             : %d'
              % len(gd))
        for kind in ('CALLER', 'SESSION', 'UNRESOLVED', 'SERVER-ONLY'):
            k = [r for r in gd if r['influence'] == kind]
            print('     URL influence %-12s : %d' % (kind, len(k)))
            if k and kind in ('CALLER', 'UNRESOLVED'):
                print('       lines: %s' % ', '.join(':%d' % r['line'] for r in k))
        print('  UNCLASSIFIED (no fetch bound to this guard)              : %d'
              % len(unk))
        if unk:
            print('     lines: %s' % ', '.join(':%d' % r['line'] for r in unk))
        print('')
    print('UNRESOLVED IS NOT SERVER-ONLY, and that is the whole point of R3:')
    print('an identifier this walk cannot trace is reported as its own state')
    print('rather than defaulting into "the caller cannot reach it", which is')
    print('what made the CALLER figure a lower bound in b23.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
```
