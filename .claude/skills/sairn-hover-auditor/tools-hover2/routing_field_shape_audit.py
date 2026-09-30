#!/usr/bin/env python
"""routing_field_shape_audit.py -- catch a free-text routing/list field in any
auditor tool that accepts a MALFORMED TOKEN at write time.

WHY THIS EXISTS. hover_log.py's --routable option split a comma string and
dropped empty tokens with `if x.strip()`, and stored uppercase or
space-containing names verbatim (H1-found, 2026-09-30). Any of those reaches
tools/hover_routing_gap_check.py unusable -- an empty token as a phantom, an
uppercase one as a name no lowercase register row can match. The fix was a
shape gate at the parse site; THIS tool is the standing check that no other
auditor tool has the same unguarded shape.

WHAT IT FLAGS. A site that builds a list by splitting a comma string and
filtering empties -- `[x.strip() for x in S.split(',') if x.strip()]` or a
`for ... in S.split(',')` loop -- with NO token-shape validation in the same
function (no regex `.match(`, no `.islower()/.isupper()`, no `raise` that
names the token). It is a HEURISTIC and REPORT-ONLY: it names candidates for
a human read, never edits and never blocks. A guarded site (a regex or an
explicit refusal near the split) is NOT flagged.

WHAT IT IS NOT. It does not prove a field is a routing field; it proves a
split-and-filter shape exists without a nearby validator, which is the shape
the real defect had. A split that feeds something other than a resource name
(a list of file paths, say) is a false positive and is meant to be read, not
trusted -- which is why this reports and does not gate on its own verdict.

    python routing_field_shape_audit.py            # scan this directory
    python routing_field_shape_audit.py --json
    python routing_field_shape_audit.py --selftest # blind-locked fixtures
"""
import io
import os
import re
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))

# A split of a comma string, either as a comprehension or a for-loop.
_SPLIT_RE = re.compile(r"\.split\(\s*['\"],['\"]\s*\)")
# Signals that a token is being handled safely nearby -- EITHER a write-time
# shape refusal (regex match + raise) OR a read-time NORMALISATION (.lower()),
# which is the correct handling for a comparison split and is not the defect.
# The real defect was a WRITE-time store with neither.
_GUARD_RE = re.compile(
    r"\.match\(|re\.match|re\.fullmatch|\.islower\(\)|\.isupper\(\)|"
    r"_RE\.|isidentifier\(\)|not\s+\w*_?TOKEN_RE|raise\s+ValueError|"
    r"\.lower\(\)|\.upper\(\)|_RE\b")
WINDOW = 20  # lines around the split searched for a guard (a raise can sit
             # well below the split, as hover_log.py's own fix does)
# Signals the split's TOKENS become STORED data (a write-time routing field) --
# the only shape whose malformed token actually persists. A split that feeds a
# lookup or a comparison (.get(), ` in `, ==, a local counter) is READ-SIDE and
# is NOT this tool's subject: a bad token there just fails to match, it is not
# stored. defect_density_weighting.py:186 (target.split(',') -> resource_to_app
# .get(tok)) is the read-side case this distinction clears.
_WRITE_RE = re.compile(
    r"append_entry|\broutable|body\s*\[|entry\s*\[|setItem|localStorage|"
    r"json\.dump|\bst\(|\bsave\w*\(|\.store\b|\.append\(\s*tok")


def _funcname(lines, idx):
    for j in range(idx, -1, -1):
        m = re.match(r'\s*def\s+(\w+)', lines[j])
        if m:
            return m.group(1)
    return '<module>'


def scan_source(src):
    """Return a list of {line, func, text, guarded} for each comma-split site.
    Pure -- takes source text, so a fixture can drive it without a file."""
    lines = src.splitlines()
    hits = []
    for i, line in enumerate(lines):
        if line.strip().startswith('#'):
            continue
        if not _SPLIT_RE.search(line):
            continue
        lo, hi = max(0, i - WINDOW), min(len(lines), i + WINDOW + 1)
        window = '\n'.join(lines[lo:hi])
        guarded = bool(_GUARD_RE.search(window))
        write_side = bool(_WRITE_RE.search(window))
        hits.append({'line': i + 1, 'func': _funcname(lines, i),
                     'text': line.strip()[:100], 'guarded': guarded,
                     'write_side': write_side})
    return hits


def scan_dir(here=HERE):
    findings = []
    for fn in sorted(os.listdir(here)):
        if not fn.endswith('.py') or fn == os.path.basename(__file__):
            continue
        try:
            src = io.open(os.path.join(here, fn), encoding='utf-8',
                          errors='replace').read()
        except OSError:
            continue
        for h in scan_source(src):
            # Only an UNGUARDED, WRITE-SIDE split is this tool's subject: a
            # read-side split (lookup/compare) storing nothing is not a
            # write-time routing field, so a bad token there cannot persist.
            if not h['guarded'] and h['write_side']:
                findings.append(dict(file=fn, **h))
    return findings


# ── FIXTURES, blind-locked: written and asserted before the real scan ──────
# A WRITE-side unguarded split: the tokens are STORED (body['routable']), so a
# malformed one persists. This is the tool's true positive.
_VULN = '''
def append_entry(routable):
    names = [x.strip() for x in routable.split(',') if x.strip()]
    body = {}
    body['routable'] = names
    return body
'''
# A READ-side split: the tokens feed a lookup and a local counter, nothing is
# stored. A bad token just fails to map. This is defect_density_weighting.py:186
# and it must NOT be flagged.
_READ_LOOKUP = '''
def density(entries, resource_to_app):
    finding_count = {}
    for e in entries:
        for tok in (p.strip() for p in e['target'].split(',')):
            app = resource_to_app.get(tok)
            if app:
                finding_count[app] = finding_count.get(app, 0) + 1
    return finding_count
'''
_GUARDED = '''
def append_entry(routable):
    out = []
    for tok in routable.split(','):
        tok = tok.strip()
        if not TOKEN_RE.match(tok):
            raise ValueError('bad token %r' % tok)
        out.append(tok)
    body = {}
    body['routable'] = out
    return body
'''


def selftest():
    bad = []

    def ck(name, cond):
        print(('  ok   ' if cond else '  FAIL ') + name)
        if not cond:
            bad.append(name)

    vuln = scan_source(_VULN)
    ck('the VULNERABLE shape (unguarded split whose tokens are STORED) is '
       'flagged -- unguarded and write-side',
       len(vuln) == 1 and vuln[0]['guarded'] is False
       and vuln[0]['write_side'] is True)
    read = scan_source(_READ_LOOKUP)
    ck('KNOWN-BAD CONTROL: a READ-SIDE split (feeds a .get() lookup and a '
       'local counter, stores nothing) is detected as read-side and NOT '
       'reported (the defect_density_weighting.py:186 shape)',
       len(read) == 1 and read[0]['write_side'] is False)
    guarded = scan_source(_GUARDED)
    ck('KNOWN-BAD CONTROL: the GUARDED write-side shape (a TOKEN_RE.match + '
       'raise near the split) is guarded True',
       len(guarded) == 1 and guarded[0]['guarded'] is True)
    ck('a source with no comma-split at all yields nothing',
       scan_source('def f():\n    return 1\n') == [])
    # The real fix must clear its own scanner: hover_log.py's parse site is
    # now guarded, so it must NOT appear in a live scan of this directory.
    live = scan_dir()
    hl = [f for f in live if f['file'] == 'hover_log.py']
    ck('the now-fixed hover_log.py --routable parse site is NOT reported '
       '(the fix clears this scanner)', hl == [])
    if bad:
        print('%d of 5 selftest arm(s) failed' % len(bad))
        return 1
    print('OK -- 5 arms passed')
    return 0


def main(argv):
    if '--selftest' in argv:
        return selftest()
    findings = scan_dir()
    if '--json' in argv:
        print(json.dumps(findings, indent=2))
        return 1 if findings else 0
    print('ROUTING-FIELD SHAPE AUDIT -- report only, nothing changed')
    print('  scanned: %s' % HERE)
    if not findings:
        print('  clean: no unguarded comma-split routing/list site found')
        return 0
    print('  %d UNGUARDED comma-split site(s) -- read each; a routing/resource'
          ' field here accepts a malformed token at write time:' % len(findings))
    for f in findings:
        print('  ! %s:%d  %s()  %s' % (f['file'], f['line'], f['func'], f['text']))
    print('\n  HEURISTIC and REPORT-ONLY: a split that feeds file paths rather '
          'than resource names is a false positive, meant to be read not '
          'trusted. This tool never edits and never blocks.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
