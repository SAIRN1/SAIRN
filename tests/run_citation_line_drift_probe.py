#!/usr/bin/env python
"""Control for tools/citation_line_drift_check.py, written before it was trusted.

# REQUIREMENT: a `:NNNN` line citation is SOUND only when it is near a real WRITE
#   site for that resource. A citation landing in a DECLARATION BLOCK -- a sync
#   list or a storage-constant block, each of which names every resource -- must
#   not be credited, and a resource with no resolvable write site must be
#   INCONCLUSIVE rather than DRIFTED.

WHY THE KNOWN-BAD IS THE DECLARATION BLOCK. The first detector asked "does the
resource name appear within 40 lines of the cited number" and answered yes almost
everywhere, because sairnfreedom.html carries two blocks that name EVERY resource
within a few lines of each other:

    var SF_SYNCED=[ 'sf_accounts', 'sf_bottle_fills', ... ]
    K_ACCOUNTS='sf_accounts', K_SESSIONS='sf_sessions', ...

A citation into either is "sound" for all 36 resources at once, and the offsets it
computed were measured from the first textual occurrence of the name, which is
inside the sync list -- the same line for every row. Arm A1 reproduces exactly
that and requires the DRIFTED verdict.

Run:  python tests/run_citation_line_drift_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(REPO, 'tools', 'citation_line_drift_check.py')

CRITERIA_VERSION = '2026-09-30.1'

_pass = _fail = 0


def ok(n):
    global _pass
    _pass += 1
    sys.stdout.write('  ok   %s\n' % n)


def bad(n, why):
    global _fail
    _fail += 1
    sys.stdout.write('  FAIL %s\n       %s\n' % (n, why))


def section(t):
    sys.stdout.write('\n%s\n' % t)


def counts(o):
    """{verdict: n} from the summary block.

    THE SUBSTRING TEST WAS WRONG AND THE FIRST RUN CAUGHT IT: the summary always
    prints `DRIFTED      : 0`, so `'DRIFTED' not in o` is false even when nothing
    drifted. An arm that can never pass is as useless as one that can never fail.
    """
    import re as _re
    out = {}
    for k in ('SOUND', 'DRIFTED', 'INCONCLUSIVE'):
        m = _re.search(r'^  %s\s*:\s*(\d+)' % k, o, _re.M)
        out[k] = int(m.group(1)) if m else None
    return out


def fixture(d, app_lines, doc_lines):
    ap = os.path.join(d, 'app.html')
    dp = os.path.join(d, 'tiers.md')
    io.open(ap, 'w', encoding='utf-8', newline='\n').write('\n'.join(app_lines))
    io.open(dp, 'w', encoding='utf-8', newline='\n').write('\n'.join(doc_lines))
    return ap, dp


def run(ap, dp, *extra):
    r = subprocess.run([sys.executable, CHECK, '--app', ap, '--prefix', 'zz_',
                        '--doc', dp] + list(extra),
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=180)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# A miniature of the real app: a sync list, a storage-constant block, and two
# genuine write sites a long way further down.
def app(with_writes=True):
    L = []
    L.append('<script>')                                     # 1
    L.append("var ZZ_SYNCED=['zz_alpha','zz_beta','zz_gamma'];")   # 2  DECLARATION
    L.append("K_ALPHA='zz_alpha', K_BETA='zz_beta', K_GAMMA='zz_gamma';")  # 3  DECLARATION
    for i in range(4, 60):
        L.append('  // filler %d' % i)
    if with_writes:
        L.append('  st(K_ALPHA, list);')                     # 60  WRITE
        L.append('  // more')                                # 61
        L.append('  st(K_BETA, list);')                       # 62  WRITE
    else:
        L.append('  // no write for anything')
        L.append('  // more')
        L.append('  // still none')
    for i in range(63, 80):
        L.append('  // tail %d' % i)
    return L


def doc(cites):
    L = ['| resource | tier |', '|---|---|']
    for name, n in cites:
        L.append('| `%s` | A | see `:%d` |' % (name, n))
    return L


def main():
    if not os.path.isfile(CHECK):
        sys.stderr.write('tools/citation_line_drift_check.py is missing -- '
                         'COULD NOT RUN, which is not a pass.\n')
        return 2
    sys.stdout.write('CITATION LINE DRIFT CONTROL -- criteria %s\n'
                     % CRITERIA_VERSION)
    d = tempfile.mkdtemp(prefix='citedrift_')
    try:
        section('A. THE KNOWN-BAD: a citation into a DECLARATION BLOCK')

        ap, dp = fixture(d, app(), doc([('zz_alpha', 2)]))
        code, o = run(ap, dp, '--window', '10')
        if code == 1 and 'DRIFTED' in o and 'zz_alpha' in o:
            ok('A1. KNOWN-BAD: a citation pointing at line 2 -- inside the sync '
               'list -- is DRIFTED, not sound. The first detector called this '
               'sound, and it would have called it sound for every resource, '
               'because that one line names them all')
        else:
            bad('A1. a declaration-block citation must be DRIFTED',
                'exit=%s\n%s' % (code, o[-700:]))

        if 'INSIDE a declaration block' in o:
            ok('A1b. ...and the report SAYS the cited line is inside a '
               'declaration block, so the reader learns why the old answer was '
               'wrong rather than just getting a different number')
        else:
            bad('A1b. the report must name the declaration-block cause', o[-400:])

        ap, dp = fixture(d, app(), doc([('zz_beta', 3)]))
        code, o = run(ap, dp, '--window', '10')
        if code == 1 and 'DRIFTED' in o:
            ok('A2. KNOWN-BAD, the SECOND block: the storage-constant line names '
               'every resource too, and it is what the naive detector actually '
               'landed on for sairnfreedom')
        else:
            bad('A2. the constant block must not be credited either',
                'exit=%s\n%s' % (code, o[-500:]))

        section('B. THE SILENT HALF: a citation AT a write site is SOUND')

        ap, dp = fixture(d, app(), doc([('zz_alpha', 60)]))
        code, o = run(ap, dp, '--window', '10')
        c = counts(o)
        if code == 0 and c['SOUND'] == 1 and c['DRIFTED'] == 0:
            ok('B1. a citation on the `st(K_ALPHA, ...)` line is SOUND and the '
               'exit is 0. Without this the checker could be "everything has '
               'drifted" and A1 would still pass')
        else:
            bad('B1. a citation at a write site must be SOUND',
                'exit=%s\n%s' % (code, o[-500:]))

        ap, dp = fixture(d, app(), doc([('zz_alpha', 57)]))
        code, o = run(ap, dp, '--window', '10')
        if code == 0 and 'SOUND' in o:
            ok('B2. ...and one WITHIN the window of it is sound too, so the '
               'window is honoured rather than requiring an exact line')
        else:
            bad('B2. a citation inside the window must be SOUND', 'exit=%s' % code)

        ap, dp = fixture(d, app(), doc([('zz_alpha', 40)]))
        code, o = run(ap, dp, '--window', '10')
        if code == 1:
            ok('B3. and one OUTSIDE the window drifts, so B2 is not passing '
               'because the window is effectively infinite')
        else:
            bad('B3. a citation outside the window must drift', 'exit=%s' % code)

        section('C. INCONCLUSIVE IS ITS OWN VERDICT')

        ap, dp = fixture(d, app(with_writes=False), doc([('zz_alpha', 2)]))
        code, o = run(ap, dp, '--window', '10')
        c = counts(o)
        if c['INCONCLUSIVE'] == 1 and c['DRIFTED'] == 0 and c['SOUND'] == 0:
            ok('C1. a resource whose constant is declared but never written with '
               'st() is INCONCLUSIVE, not DRIFTED. There is no line for the '
               'citation to point AT, and calling it drifted would invite a '
               'correction to a line that is also wrong')
        else:
            bad('C1. no write site must be INCONCLUSIVE',
                'exit=%s\n%s' % (code, o[-500:]))

        ap, dp = fixture(d, app(), doc([('zz_delta', 60)]))
        code, o = run(ap, dp, '--window', '10')
        if 'INCONCLUSIVE' in o:
            ok('C2. a resource with no storage constant at all is INCONCLUSIVE '
               'and says which of the two reasons applies')
        else:
            bad('C2. an unmapped resource must be INCONCLUSIVE', o[-400:])

        section('D. COULD NOT RUN, and it is never a pass')

        ap, dp = fixture(d, app(), doc([]))
        code, o = run(ap, dp)
        if code == 2:
            ok('D1. a document with NO citation matching the prefix is exit 2. '
               '"No drift" over an empty population is a measurement that did '
               'not happen')
        else:
            bad('D1. an empty population must exit 2', 'exit=%s' % code)

        noK = [l for l in app() if not l.startswith("K_ALPHA=")]
        ap, dp = fixture(d, noK, doc([('zz_alpha', 60)]))
        code, o = run(ap, dp)
        if code == 2 and 'COULD NOT RUN' in o:
            ok('D2. an app with no storage-constant block is exit 2 -- every '
               'verdict would be INCONCLUSIVE, and that is a fact about this '
               'tool\'s assumptions rather than about the citations')
        else:
            bad('D2. a missing constant block must exit 2',
                'exit=%s\n%s' % (code, o[-400:]))

        code, o = run(os.path.join(d, 'nope.html'), dp)
        if code == 2:
            ok('D3. an unreadable app file is exit 2')
        else:
            bad('D3. a missing app file must exit 2', 'exit=%s' % code)

        section('E. THE REAL RUN, and the anchor it rests on')

        r = subprocess.run([sys.executable, CHECK, '--app', 'sairnfreedom.html',
                            '--prefix', 'sf_'], cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=180)
        o = r.stdout or ''
        if 'citations found' in o and 'declaration spans' in o:
            ok('E1. it runs against the real pair and reports the spans it '
               'excluded, so a reader can check the exclusion rather than trust '
               'it')
        else:
            bad('E1. the real run must report its declaration spans',
                o[-400:] + (r.stderr or '')[-300:])

        # EVERY DRIFTED TARGET IS RE-READ FROM THE FILE. A corrected offset that
        # nobody checked against the line it now names is the same class of claim
        # as the one being corrected.
        import re as _re
        lines = io.open(os.path.join(REPO, 'sairnfreedom.html'),
                        encoding='utf-8', errors='replace').read().split('\n')
        src = '\n'.join(lines)
        cmap = {}
        for c, res in _re.findall(r"\b([A-Z][A-Z0-9_]*)\s*=\s*'(sf_[a-z_]+)'", src):
            cmap.setdefault(res, []).append(c)
        drifted = list(_re.finditer(r'DRIFTED\s+(\S+)\s+:(\d+)\s+-> :(\d+)', o))
        unverified = []
        for m in drifted:
            res, new = m.group(1), int(m.group(3))
            target = lines[new - 1] if 0 < new <= len(lines) else ''
            if not any(_re.search(r'\bst\(\s*%s\b' % c, target)
                       for c in cmap.get(res, [])):
                unverified.append('%s -> :%d  %s' % (res, new, target.strip()[:60]))
        if drifted and not unverified:
            ok('E2. all %d corrected targets re-read from the file and every one '
               'is an `st(K_..., ...)` write for the resource it was corrected '
               'for. An offset nobody checked against the line it now names is '
               'the same kind of claim as the one being corrected'
               % len(drifted))
        elif not drifted:
            bad('E2. the real run found NO drift',
                'either the document was corrected or the detector stopped '
                'matching -- re-derive before believing it')
        else:
            bad('E2. every corrected target must be a real write site',
                '\n       '.join(unverified[:6]))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
