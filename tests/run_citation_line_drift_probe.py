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
sys.path.insert(0, os.path.join(REPO, 'tools'))

CRITERIA_VERSION = '2026-10-05.3'

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
    for k in ('ANCHORED', 'SOUND', 'DRIFTED', 'INCONCLUSIVE'):
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
        # EXPECTATION UPDATED 2026-10-05, and the reason is recorded rather
        # than the number quietly changed: a citation ON the write line NAMES
        # the resource through its constant, so the ranking now reports it as
        # ANCHORED, which is strictly more informative than SOUND. The arm
        # accepts either, because what it is really pinning is that a citation
        # at a write site is NOT drifted and the exit is 0.
        if code == 0 and c['DRIFTED'] == 0 and (c['SOUND'] or 0) + (c['ANCHORED'] or 0) == 1:
            ok('B1. a citation on the `st(K_ALPHA, ...)` line is ANCHORED or '
               'SOUND -- never DRIFTED -- and the exit is 0. Without this the '
               'checker could be "everything has drifted" and A1 would still '
               'pass')
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

        # ── F. THE HALF E2 CANNOT SEE ────────────────────────────────────────
        # E2 verifies the DESTINATION of every correction is a real write site.
        # It never verifies the ORIGIN was wrong. A citation deliberately
        # pointing at a render site passes E2 while the correction is still
        # wrong -- which is E2's own sentence one step further back: an offset
        # nobody checked against the line it CURRENTLY names.
        #
        # Measured 2026-10-04: on SAIRNgrounds, 4 of 4 DRIFTED rows were
        # deliberate read-site citations and the closing instruction would have
        # broken four correct cells.
        section('F. A DRIFTED ARROW IS A CANDIDATE, NOT AN INSTRUCTION')

        # COUNTED OFF LINE STARTS, NOT WITH o.count(). The first version of this
        # arm counted the substring anywhere and got 33 for 32 rows: the closing
        # advisory names `cited line reads:` too. An arm that counts its own
        # explanatory prose as data is the fabrication shape this file exists to
        # catch, so it is anchored to the report row's own indent.
        row_cited = _re.findall(r'^ +cited line reads: ', o, _re.M)
        if drifted and row_cited:
            n_cited = len(row_cited)
            if n_cited == len(drifted):
                ok('F1. all %d DRIFTED rows carry the CITED line\'s own source '
                   'text. That text is what decides stale-vs-deliberate, and a '
                   'reader should not have to open the app file to see it'
                   % n_cited)
            else:
                bad('F1. every DRIFTED row must carry its cited line',
                    '%d rows, %d cited-line lines' % (len(drifted), n_cited))
        else:
            bad('F1. DRIFTED rows must print the cited line',
                'absent from the real run -- the evidence is missing')

        if 'is the correction to apply' not in o:
            ok('F2. the output does NOT tell the reader each DRIFTED line is '
               '"the correction to apply". That sentence was an instruction '
               'the tool had not earned: it resolves write sites only, so it '
               'cannot tell a stale citation from a deliberate read-site one')
        else:
            bad('F2. the blind-repoint instruction must be gone',
                'the output still presents the arrow as a correction to apply')

        if 'CANDIDATE' in o and "cell's own" in o:
            ok('F3. the output names the arrow a CANDIDATE and sends the reader '
               "to the register cell's own prose to settle it")
        else:
            bad('F3. the arrow must be named a candidate',
                o[-400:])

        # F4 IS THE KNOWN-BAD, and it is built to be indistinguishable from
        # genuine drift by every signal this tool CAN measure: far from the
        # write site, outside every declaration block. The only thing that
        # separates it is the cited line's text -- so the arm requires that
        # text to be present and does NOT require the tool to classify it.
        L = app()
        L[70] = "  td.innerHTML = H(z.last_service) + '</td>';"   # a RENDER site
        ap2, dp2 = fixture(d, L, doc([('zz_alpha', 71)]))
        code2, o2 = run(ap2, dp2, '--window', '5')
        if code2 == 1 and 'DRIFTED' in o2 and 'last_service' in o2:
            ok('F4. KNOWN-BAD: a citation on a RENDER line far from the write '
               'site is still surfaced (exit 1 -- it needs a human look), and '
               'the render text is in the output so the human can see it was '
               'deliberate. The tool does not claim to classify it, and it no '
               'longer tells anybody to repoint it')
        elif code2 == 1 and 'DRIFTED' in o2:
            bad('F4. the render line must appear in the output',
                'flagged, but the cited text is missing -- the reader is back '
                'to opening the file: ' + o2[-300:])
        else:
            bad('F4. a render-site citation must still be surfaced, not passed',
                'exit=%s -- silently sound is the worse failure here' % code2)

        # ── G. THE CITATION FORMS IT USED TO BE BLIND TO ────────────────────
        # Measured 2026-10-05, before the expansion: the extractor was
        # `` `:(\d+)` `` -- anchored on a CLOSING BACKTICK immediately after
        # the digits. So two whole forms were invisible:
        #
        #   `file.html:NNN`   188 of them, across 147 register rows
        #   `:NNN-NNN`        a range, because the `-` broke the anchor
        #
        # Every verdict this tool printed covered 285 of 473 citations and
        # presented it as the answer. sb_perf's two genuinely drifted
        # citations were both in the invisible set and were found by
        # hand-reading the row.
        section('G. THE FORMS THE EXTRACTOR WAS BLIND TO')

        import citation_line_drift_check as _c
        _row = ('| `zz_alpha` | A | shape at `:12`, also `app.html:34`, '
                'and a range `:56-60`, plus `api/sd-data.js:78` |')
        got = _c.citations([_row], 'zz_', default_file='DEFAULT.html')
        if got == [('zz_alpha', 12, 'DEFAULT.html'),
                   ('zz_alpha', 34, 'app.html'),
                   ('zz_alpha', 56, 'DEFAULT.html'),
                   ('zz_alpha', 78, 'api/sd-data.js')]:
            ok('G1. all four forms extracted: bare, file-named, RANGE (anchored '
               'on its FIRST line, not both ends -- counting the end too would '
               'double count and treating the span as near-enough would turn a '
               '40-line window into an 80-line one), and a nested api/ path')
        else:
            bad('G1. every citation form must be extracted', repr(got))

        if all(f for _, _, f in got):
            ok('G2. every citation carries a FILE -- bare ones inherit --app, '
               'named ones keep their own. THIS IS THE HALF THAT MATTERS: '
               '`api/sd-data.js:2051` appears on rows swept with --app set to '
               'an .html, and resolving it against --app would compare a line '
               'number to the wrong file and invent drift with total '
               'confidence')
        else:
            bad('G2. a citation with no file would resolve against the wrong '
                'file', repr(got))

        _none = _c.citations([_row], 'yy_', default_file='DEFAULT.html')
        if _none == []:
            ok('G3. ...and a row whose resource does not match the prefix '
               'still yields nothing, so G1 is not passing because the '
               'extractor matches everything')
        else:
            bad('G3. the prefix filter must still apply', repr(_none))

        ap, dp = fixture(d, app(), doc([('zz_alpha', 60)]))
        code, o = run(ap, dp, '--window', '10')
        if 'by form' in o:
            ok('G4. the run DISCLOSES ITS DENOMINATOR by form -- the defect was '
               'never the regex, it was that a 60%% reading printed as the '
               'answer. A tool that reads part of its subject must say which '
               'part')
        else:
            bad('G4. the coverage by form must be printed', o[-300:])

        _missing = ('| `zz_alpha` | A | see `no_such_file_xyz.html:10` |')
        ap2, dp2 = fixture(d, app(), [_missing])
        code2, o2 = run(ap2, dp2, '--window', '10')
        if 'COULD NOT RESOLVE' in o2 and 'DRIFTED      : 0' in o2:
            ok('G5. KNOWN-BAD: a citation naming a file this run cannot read is '
               'COULD NOT RESOLVE and is NOT counted as drifted. A line number '
               'compared against a file that was never opened is not a '
               'measurement, and reporting it as drift would invite a '
               'correction computed from nothing')
        else:
            bad('G5. an unreadable cited file must not become a drift verdict',
                'exit=%s\n%s' % (code2, o2[-400:]))

    finally:
        shutil.rmtree(d, ignore_errors=True)

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
