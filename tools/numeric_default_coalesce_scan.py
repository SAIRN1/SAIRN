"""Where does a getter replace a typed number with a default BEFORE validation?

Run:  python tools/numeric_default_coalesce_scan.py             # whole repo
      python tools/numeric_default_coalesce_scan.py --file F    # one file
      python tools/numeric_default_coalesce_scan.py --by-owner  # grouped

── THE DEFECT THIS IS THE CLASS OF ─────────────────────────────────────────
2026-09-29, sairnbiz.html:4959 read

    return {fy:c.fy||d.fy, ot:c.ot||d.ot, terms:c.terms||d.terms};

with `d.ot === 40`. `0` and `''` are falsy in JavaScript, so a user who typed 0
-- or cleared the field -- had their value replaced by 40 BEFORE sbOtThreshold()
ever saw it. The validator's `n<=0` branch was unreachable for exactly those two
inputs, and the note whose whole purpose is to say "your setting was rejected"
compared 40 against 40 and said nothing. Neither figure was wrong; the silence
was, on a money setting.

WHAT MADE IT SURVIVE FOUR TEST ARMS IS THE LAYER. Arms B3/B4/B6/B7 drove
sbOtThreshold() with a raw value and all four passed. The substitution happens
one layer ABOVE where every arm entered. So the class is not "a falsy coalesce"
-- it is "a getter that substitutes a default before validation can see the
input", and the only way to see it is to enter at the getter.

── THE DISCRIMINATION, AND WHY IT IS NARROW ON PURPOSE ─────────────────────
sairnbiz.html alone carries 13 sites of the shape `x || N`. TWELVE ARE
HARMLESS: their default is 0, so a typed 0 becomes 0 and nothing is lost. If
this tool flagged all 13 the one that matters would be buried, and a scanner
that cries wolf is a scanner somebody switches off. The rule:

  FLAG   `||` / `or` whose default is a NON-ZERO numeric literal. A typed 0
         silently becomes a DIFFERENT number.
  CLEAR  default 0 or 0.0 -- no information is lost.
  CLEAR  a string default. '' really does mean unset for a fiscal-year name;
         there is no rejectable empty string there. sbCfg keeps `||` on `fy`
         and `terms` deliberately for that reason.
  CLEAR  `??` with ANY default. It substitutes on null/undefined only, which is
         the correct operator -- flagging it would flag the fix.
  FLAG   `if (!x)` immediately followed by a numeric assignment to the same x.
         Same substitution, different spelling.

── COMMENTS AND STRING LITERALS ARE STRIPPED FIRST ─────────────────────────
Seventh instance of the standing class on this platform: a predicate satisfied
by prose rather than by behaviour. The header of the FIXED sbCfg quotes the
broken line verbatim -- `This read ot: c.ot||d.ot` -- so a text scanner would
report the fix as the defect. Comments AND string literals are removed before
anything is matched, which is the correct direction here: unlike the purge
gate, a numeric default is never DELIVERED as a string constant.

── WHAT IT CANNOT DO, STATED RATHER THAN IMPLIED ───────────────────────────
It does not know whether a flagged site is reachable, whether the field is
user-typed, or whether a validator exists downstream. It finds the SHAPE and
says where; deciding whether a typed 0 is legitimate or rejectable at that site
is a judgment call per site, and the report says so instead of pretending to a
verdict. Every finding is printed -- there is no top-N and no sampling.
"""
import argparse
import io
import os
import re
import sys

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_EXT = ('.html', '.js', '.py')
# `archive/` holds verbatim dumps of abandoned branches -- code no user
# reaches. Excluded, and the exclusion is PRINTED in every report rather than
# implied, because a silent exclusion reads as "covered everything".
SKIP_DIRS = ('__pycache__', 'node_modules', '.git', 'graphify-out', 'archive')

# A numeric literal that is not zero. `0`, `0.0`, `00` are excluded; `40`,
# `1.5`, `168`, `1e3` are not.
NONZERO_NUM = re.compile(r'^(?!0+(\.0+)?$)\d+(\.\d+)?([eE][+-]?\d+)?$')

# left || DEFAULT   and   left or DEFAULT
JS_COALESCE = re.compile(r'([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*'
                         r'(?:\[[^\]\n]{1,40}\])?)\s*\|\|\s*'
                         r'([A-Za-z_$][\w$.]*|\d[\w.eE+-]*)')
PY_COALESCE = re.compile(r'([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)*'
                         r'(?:\([^()\n]{0,60}\))?)\s+or\s+'
                         r'([A-Za-z_][\w.]*|\d[\w.eE+-]*)')

# if (!x) ... x = <number>
JS_IFNOT = re.compile(r'if\s*\(\s*!\s*([A-Za-z_$][\w$.]*)\s*\)')
PY_IFNOT = re.compile(r'if\s+not\s+([A-Za-z_][\w.]*)\s*:')


def strip_noncode(src, ext):
    """Remove comments, THEN string literals, preserving line numbering.

    THE ORDER IS THE WHOLE POINT, AND THE FIRST VERSION HAD IT WRONG. A single
    pass that handles comments and strings together mis-aligns on an ODD
    BACKTICK INSIDE A COMMENT, and stonedesk.html has them. Line 31807 reads:

        // `(x.hrs||0)*(x.rate||28)` appeared at six sites: the payroll KPI,

    A backtick opened on an earlier comment line ran on as a template literal
    straight through this line's `//`, blanked it, closed at the first backtick
    here, and left `(x.rate||28)` looking like live code. The scanner then
    reported a COMMENT as a defect -- the exact class it exists to avoid,
    arriving through the stripper instead of through the predicate. Two real
    findings on stonedesk.html were this, and nothing else would have told me.

    So comments are removed first, line-oriented, regardless of string state.
    That over-strips a `//` inside a URL (`"https://x"` keeps `"https:`), and
    over-stripping can only ever hide a match inside a string literal, which
    this tool does not want anyway. Line count is preserved exactly, so every
    reported line number still points at the real line.
    """
    n = len(src)
    py = ext == '.py'
    out = list(src)
    nl = '\n'

    def blank(buf, a, b):
        for k in range(a, min(b, n)):
            if buf[k] != nl:
                buf[k] = ' '

    # ── pass 1a: block comments ────────────────────────────────────────────
    if not py:
        i = 0
        while i < n:
            if src.startswith('/*', i):
                j = src.find('*/', i + 2)
                j = n if j < 0 else j + 2
                blank(out, i, j)
                i = j
                continue
            i += 1

    # ── pass 1b: line comments, unconditionally ────────────────────────────
    lines = ''.join(out).split(nl)
    marker = '#' if py else '//'
    for idx, line in enumerate(lines):
        c = line.find(marker)
        if c >= 0:
            lines[idx] = line[:c] + ' ' * (len(line) - c)
    txt = nl.join(lines)

    # ── pass 2: string literals ────────────────────────────────────────────
    out = list(txt)
    i = 0
    while i < n:
        c = txt[i]
        if py and (txt.startswith('"""', i) or txt.startswith("'''", i)):
            q = txt[i:i + 3]
            j = txt.find(q, i + 3)
            j = n if j < 0 else j + 3
            blank(out, i, j)
            i = j
            continue
        if c == '"' or c == "'" or c == '`':
            j = i + 1
            while j < n:
                if txt[j] == '\\':
                    j += 2
                    continue
                if txt[j] == c:
                    j += 1
                    break
                if txt[j] == nl and c != '`':
                    break
                j += 1
            blank(out, i, j)
            i = j
            continue
        i += 1
    return ''.join(out)


def _literal_kind(text):
    t = text.strip().rstrip(',').strip()
    if NONZERO_NUM.match(t):
        return 'nonzero-number'
    if re.match(r'^0+(\.0+)?$', t):
        return 'zero'
    if t[:1] in ('"', "'", '`'):
        return 'string'
    return 'unknown'


def default_kind(token, ext, joined):
    """'nonzero-number' | 'zero' | 'string' | 'unknown' for the default side.

    A NAMED default such as `d.ot` is resolved ONLY from an object-literal
    declaration of `d` itself -- `var d={fy:'January',ot:40,terms:'Net 30'}` --
    and only when there is exactly one such declaration in the file.

    THE FIRST VERSION SEARCHED THE WHOLE FILE FOR `ot:` AND THAT WAS WRONG in
    the way this whole platform keeps being wrong. On sairnbiz.html it resolved
    a default of `e.rate` by finding an unrelated `rate:` in a different object
    a thousand lines away, and then printed "replaced by e.rate" -- a number it
    had not actually derived, attached to the wrong object. 329 findings became
    mostly noise on the strength of it. A whole-file field search is the same
    substring class as a whole-file guard match.

    Unresolvable is reported as 'unknown' and lands in its own section. It is
    NOT flagged: a finding whose default could not be read is a lead, not a
    defect, and mixing the two is how a count stops meaning anything.
    """
    t = token.strip()
    k = _literal_kind(t)
    if k != 'unknown':
        return k
    m = re.match(r'^([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)$', t)
    if not m:
        return 'unknown'
    obj, field = m.group(1), m.group(2)
    decls = re.findall(
        r'\b(?:var|let|const)\s+%s\s*=\s*\{([^{}]*)\}' % re.escape(obj), joined)
    if len(decls) != 1:
        return 'unknown'
    fm = re.search(r'\b%s\s*:\s*([^,}\n]+)' % re.escape(field), decls[0])
    if not fm:
        return 'unknown'
    return _literal_kind(fm.group(1))


# ── CONFIG SCOPE, AND WHY THE RAW COUNT IS NOT THE ANSWER ──────────────────
# The unrestricted scan finds 297 sites across fifteen apps and MOST OF THEM
# ARE FINE: `|| 1` appears 53 times (a quantity or a page number), `|| 640` and
# `|| 480` are canvas dimensions, `|| 3000` is a toast duration. Passing 0 to a
# toast really does mean "use the normal duration"; there is no validator to
# starve and no user to mislead.
#
# The defect shape needs a SECOND property that none of those have: the value
# came out of a persisted settings store, and something downstream is supposed
# to validate it and tell the user when it was rejected. That is what made
# sbCfg().ot expensive and `d||3000` harmless.
#
# So --config-only restricts to sites whose ENCLOSING FUNCTION also reads a
# settings store. The enclosing function is found by brace matching over the
# comment-and-string-stripped source -- not by a fixed window, which is the
# other class this repo keeps paying for.
CONFIG_READ = re.compile(r'\bld\s*\(|localStorage|getItem\s*\(|'
                         r'\b\w*[Cc]fg\s*\(|\b\w*[Ss]ettings\b|'
                         r'json\.load|\.get\s*\(\s*[\'"]')


def function_spans(stripped, ext):
    """[(start, end, text)] for every function body, by brace matching.

    Exact rather than windowed: a body ends where its own opening brace closes.
    An unbalanced file yields fewer spans and that is reported by the caller as
    a reduced denominator, never as a clean result.
    """
    spans = []
    if ext == '.py':
        # def NAME(...): ... until the next line at the same or lower indent.
        lines = stripped.split('\n')
        offs, pos = [], 0
        for ln in lines:
            offs.append(pos)
            pos += len(ln) + 1
        for i, ln in enumerate(lines):
            m = re.match(r'^(\s*)def\s+\w+', ln)
            if not m:
                continue
            indent = len(m.group(1))
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                j += 1
            end = offs[j] if j < len(lines) else len(stripped)
            spans.append((offs[i], end, stripped[offs[i]:end]))
        return spans
    for m in re.finditer(r'\bfunction\b', stripped):
        b = stripped.find('{', m.end())
        if b < 0:
            continue
        depth, k = 0, b
        while k < len(stripped):
            if stripped[k] == '{':
                depth += 1
            elif stripped[k] == '}':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth != 0:
            continue
        spans.append((m.start(), k + 1, stripped[m.start():k + 1]))
    return spans


def config_scoped_offsets(stripped, ext):
    """The set of byte ranges that sit inside a function that reads settings."""
    ranges = []
    for start, end, text in function_spans(stripped, ext):
        if CONFIG_READ.search(text):
            ranges.append((start, end))
    return ranges


def scan_text(src, ext, config_only=False):
    """(findings, unresolved). Each entry is (lineno, kind, text, why)."""
    stripped = strip_noncode(src, ext)
    lines = stripped.split('\n')
    joined = '\n'.join(lines)
    raw = src.split('\n')
    findings, unresolved = [], []
    coalesce = PY_COALESCE if ext == '.py' else JS_COALESCE
    ifnot = PY_IFNOT if ext == '.py' else JS_IFNOT

    cfg_ranges = config_scoped_offsets(joined, ext) if config_only else None
    line_offsets, _p = [], 0
    for ln in lines:
        line_offsets.append(_p)
        _p += len(ln) + 1

    def in_config_scope(idx):
        if cfg_ranges is None:
            return True
        off = line_offsets[idx]
        return any(s <= off < e for s, e in cfg_ranges)

    for idx, line in enumerate(lines):
        lineno = idx + 1
        if not in_config_scope(idx):
            continue
        for m in coalesce.finditer(line):
            left, right = m.group(1), m.group(2)
            kind = default_kind(right, ext, joined)
            if kind == 'unknown':
                unresolved.append((lineno, 'DEFAULT-NOT-RESOLVED',
                                   raw[idx].strip()[:140],
                                   'the default `%s` on `%s` could not be read '
                                   'from a single object-literal declaration, '
                                   'so its value is unknown and this is a lead, '
                                   'not a finding' % (right, left)))
                continue
            if kind != 'nonzero-number':
                continue
            findings.append((lineno, 'FALSY-COALESCE',
                             raw[idx].strip()[:140],
                             'a typed 0 (and, in JS, an empty string) on `%s` '
                             'is replaced by %s before anything validates it'
                             % (left, right)))
        # if (!x) followed within three lines by a numeric assignment to x
        for m in ifnot.finditer(line):
            var = m.group(1)
            window = lines[idx:idx + 4]
            assign = re.compile(r'\b%s\s*=\s*(\d[\w.eE+-]*)'
                                % re.escape(var.split('.')[-1]))
            hit = None
            for w in window:
                a = assign.search(w)
                if a and NONZERO_NUM.match(a.group(1)):
                    hit = a.group(1)
                    break
            if hit:
                findings.append((lineno, 'IF-NOT-ON-A-NUMBER',
                                 raw[idx].strip()[:140],
                                 '`!%s` is true for 0, so a typed 0 is '
                                 'replaced by %s' % (var, hit)))
    return findings, unresolved


def scan_file(path, config_only=False):
    ext = os.path.splitext(path)[1].lower()
    try:
        src = io.open(path, encoding='utf-8', errors='replace').read()
    except OSError as e:
        return None, None, str(e)
    f, u = scan_text(src, ext, config_only)
    return f, u, None


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1].lower() in SCAN_EXT:
                yield os.path.join(dirpath, fn)


OWNERS = [
    # Prefix -> the session that holds it, for routing. Read off the clone
    # registry in CLAUDE.md; a path matching nothing is reported as UNASSIGNED
    # rather than guessed at.
    ('.claude/skills/sairn-hover-auditor/', 'hover (audit role -- NOT a build agent)'),
]


def owner_of(rel):
    for prefix, who in OWNERS:
        if rel.startswith(prefix):
            return who
    return 'UNASSIGNED -- route by the file, not by a guess'


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--file', help='scan one file instead of the repo')
    ap.add_argument('--root', default=REPO)
    ap.add_argument('--by-owner', action='store_true')
    ap.add_argument('--config-only', action='store_true',
                    help='only sites whose enclosing function reads a settings '
                         'store -- the shape that actually misled a user')
    ap.add_argument('--leads', action='store_true',
                    help='also print the sites whose default could not be read')
    a = ap.parse_args(argv)

    targets = [a.file] if a.file else list(walk(a.root))
    if not targets:
        print('COULD NOT RUN -- nothing to scan under %s' % a.root)
        return EXIT_COULD_NOT_RUN

    total = 0
    unres_total = 0
    unreadable = []
    per_file, per_file_unres = [], []
    for path in targets:
        findings, unres, err = scan_file(path, a.config_only)
        if err:
            unreadable.append((path, err))
            continue
        if findings:
            per_file.append((path, findings))
            total += len(findings)
        if unres:
            per_file_unres.append((path, unres))
            unres_total += len(unres)

    print('NUMERIC-DEFAULT COALESCE SCAN%s'
          % ('  [--config-only: enclosing function reads a settings store]'
             if a.config_only else ''))
    print('files scanned : %d  (%s)' % (len(targets), ', '.join(SCAN_EXT)))
    print('skipped dirs  : %s' % ', '.join(SKIP_DIRS))
    print('findings      : %d   -- every one printed, no top-N and no sampling'
          % total)
    print('leads         : %d   -- default not resolvable to a literal; NOT '
          'counted as findings' % unres_total)
    if unreadable:
        print('UNREADABLE    : %d -- NOT scanned, and not a pass' % len(unreadable))
        for p, e in unreadable:
            print('   %s  %s' % (p, e))
    print('')
    for path, findings in per_file:
        rel = os.path.relpath(path, a.root).replace('\\', '/')
        head = rel
        if a.by_owner:
            head = '%s   [owner: %s]' % (rel, owner_of(rel))
        print(head)
        for lineno, kind, text, why in findings:
            print('  :%-6d %-20s %s' % (lineno, kind, why))
            print('           %s' % text)
        print('')
    if a.leads:
        print('── LEADS: default could not be resolved to a literal ─────────')
        for path, unres in per_file_unres:
            rel = os.path.relpath(path, a.root).replace('\\', '/')
            print('%s  (%d)' % (rel, len(unres)))
            for lineno, kind, text, why in unres:
                print('  :%-6d %s' % (lineno, why))
        print('')
    elif unres_total:
        print('%d lead(s) not printed. Re-run with --leads to see them; they are'
              % unres_total)
        print('disclosed here rather than dropped, because a silent truncation')
        print('reads as "covered everything".')
        print('')
    if unreadable:
        return EXIT_COULD_NOT_RUN
    if total:
        print('A FINDING IS A SHAPE, NOT A VERDICT. Whether a typed 0 is')
        print('legitimate or rejectable at a given site is a judgment call per')
        print('site; this says where the substitution happens before validation.')
        return EXIT_FINDING
    print('OK -- no getter substitutes a non-zero numeric default ahead of its')
    print('own validation in the files scanned.')
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
