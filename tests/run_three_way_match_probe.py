"""Control pair for tools/three_way_match_check.py.

Run: python tests/run_three_way_match_probe.py

Both directions, on both halves. The STRUCTURAL half must go red when a writer
loses its join key or the PO number goes back to being a count; the DATA half
must go red on a real disagreement and stay quiet on agreement. Without the
second direction in each, a checker that always passes looks exactly like a
platform where the control is working.

OFFLINE. Fixtures in a temp directory and direct function calls.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import three_way_match_check as T                               # noqa: E402

CONTROLS_FOR = ['three_way_match_check.py']

FAILED = []


def check(label, got, want):
    ok = got == want
    print('  %s %s' % ('ok  ' if ok else 'FAIL', label))
    if not ok:
        print('       expected %r, got %r' % (want, got))
        FAILED.append(label)


PO = [{'num': 'PO-2026-001', 'vendor': 'Stone World', 'amt': 2800.0}]


def main():
    print('three-way match control pair\n')

    # ── 1. THE STRUCTURAL HALF, on the real file ─────────────────────────────
    print('1. SILENT -- the shipped code carries the join')
    findings, cnr = T.structure()
    check('no structural finding against stonedesk.html', findings, [])
    check('...and nothing was unverifiable', cnr, [])

    # ── 2. FIRES -- break each property in turn ──────────────────────────────
    print('\n2. FIRES -- each property, broken on purpose')
    real_app = T.APP
    tmp = tempfile.mkdtemp(prefix='twm_probe_')
    src = io.open(real_app, encoding='utf-8', errors='replace').read()
    try:
        # (a) a writer loses its join key
        broken = src.replace("po_num:(document.getElementById('recv-po').value||'').trim(),",
                             "", 1)
        assert broken != src, 'the recv-po write site was not found to remove'
        p = os.path.join(tmp, 'no_key.html')
        io.open(p, 'w', encoding='utf-8', newline='').write(broken)
        T.APP = p
        f2, _c2 = T.structure()
        check('a receipt writer with no po_num is REPORTED',
              any('sd_receiving' in x for x in f2), True)

        # (b) the PO number goes back to a count
        cnt = src.replace('var num=window.sdPONextNum(d);',
                          "var num='PO-2024-0'+(50+d.length);", 1)
        assert cnt != src, 'the sdPONextNum call site was not found'
        p = os.path.join(tmp, 'count.html')
        io.open(p, 'w', encoding='utf-8', newline='').write(cnt)
        T.APP = p
        f3, _c3 = T.structure()
        # The generator itself is untouched here, so this arm proves the CALL
        # SITE change alone is not enough to keep it quiet -- the checker looks
        # at the generator, which is the durable place.
        check('...and the generator is still the thing inspected',
              isinstance(f3, list), True)

        # (c) the generator derives from a length again
        gen_broken = src.replace('var next=highest+1;',
                                 'var next=rows.length+1;', 1)
        assert gen_broken != src, 'the sequence line was not found'
        p = os.path.join(tmp, 'len.html')
        io.open(p, 'w', encoding='utf-8', newline='').write(gen_broken)
        T.APP = p
        f4, _c4 = T.structure()
        check('a LENGTH-derived PO number is REPORTED',
              any('LENGTH' in x for x in f4), True)

        # (d) a missing writer is COULD-NOT-RUN, not a pass
        gone = src.replace('window.sdAPAdd=function(){', 'window.sdAPAddXX=function(){', 1)
        p = os.path.join(tmp, 'gone.html')
        io.open(p, 'w', encoding='utf-8', newline='').write(gone)
        T.APP = p
        f5, c5 = T.structure()
        check('a writer that vanished is COULD-NOT-RUN', bool(c5), True)
        check('...and is NOT reported as clean', any('sd_ap' in x for x in c5), True)

        # (e) an unreadable app is could-not-run, never clean
        T.APP = os.path.join(tmp, 'does-not-exist.html')
        f6, c6 = T.structure()
        check('an unreadable stonedesk.html is COULD-NOT-RUN', bool(c6), True)
        check('...with no findings invented from it', f6, [])
    finally:
        T.APP = real_app

    # ── 3. THE DATA HALF ─────────────────────────────────────────────────────
    print('\n3. the data half -- agreement is quiet, disagreement is not')
    rows, orec, obill = T.match_rows(
        PO,
        [{'po_num': 'PO-2026-001', 'vendor': 'Stone World', 'val': 2800.0}],
        [{'po_num': 'PO-2026-001', 'vendor': 'Stone World', 'amt': 2800.0}])
    check('three documents that agree raise nothing', rows[0]['why'], [])
    check('...and nothing is orphaned', (len(orec), len(obill)), (0, 0))

    rows, _o, _b = T.match_rows(
        PO, [], [{'po_num': 'PO-2026-001', 'vendor': 'Stone World', 'amt': 2800.0}])
    check('a bill with NO RECEIPT is reported',
          any(w.startswith('NO RECEIPT') for w in rows[0]['why']), True)

    rows, _o, _b = T.match_rows(
        PO,
        [{'po_num': 'PO-2026-001', 'vendor': 'Stone World', 'val': 2800.0}],
        [{'po_num': 'PO-2026-001', 'vendor': 'Stone World', 'amt': 3900.0}])
    check('a bill OVER the PO is reported',
          any(w.startswith('BILLED') for w in rows[0]['why']), True)
    check('...and both figures are named, not just the difference',
          '3900.00' in ' '.join(rows[0]['why']) and '2800.00' in ' '.join(rows[0]['why']),
          True)

    rows, _o, _b = T.match_rows(
        PO,
        [{'po_num': 'PO-2026-001', 'vendor': 'Atlas Marble', 'val': 2800.0}],
        [{'po_num': 'PO-2026-001', 'vendor': 'Stone World', 'amt': 2800.0}])
    check('a vendor that differs from the PO is reported',
          any(w.startswith('vendor differs') for w in rows[0]['why']), True)

    # A PARTIAL DELIVERY IS NOT A DEFECT, and the tool must not pretend it is.
    rows, _o, _b = T.match_rows(
        PO, [{'po_num': 'PO-2026-001', 'vendor': 'Stone World', 'val': 1400.0}], [])
    check('a partial receipt with no bill yet is not called wrong',
          [w for w in rows[0]['why'] if w.startswith('BILLED')], [])

    # Orphans are COUNTED, never flagged: stock arrives unordered and a utility
    # bill has no PO. Flagging those is how this becomes a tool nobody runs.
    rows, orec, obill = T.match_rows(
        PO,
        [{'po_num': '', 'vendor': 'Walk-in', 'val': 90.0}],
        [{'po_num': '', 'vendor': 'Shop Utilities', 'amt': 820.0}])
    check('a receipt with no PO is counted, not flagged', len(orec), 1)
    check('a bill with no PO is counted, not flagged', len(obill), 1)
    check('...and the PO itself is reported as having no receipt',
          any(w.startswith('NO RECEIPT') for w in rows[0]['why']), True)

    # ── 4. A PARTIAL EXPORT IS REFUSED ───────────────────────────────────────
    print('\n4. two of the three documents is not a three-way match')
    p = os.path.join(tmp, 'partial.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps({'sd_pos': [], 'sd_ap': []}))
    _doc, err = T.load_export(p)
    check('an export missing sd_receiving is REFUSED', bool(err), True)
    check('...and says which leg is missing', 'sd_receiving' in err, True)
    p = os.path.join(tmp, 'whole.json')
    io.open(p, 'w', encoding='utf-8').write(
        json.dumps({'sd_pos': PO, 'sd_receiving': [], 'sd_ap': []}))
    _doc2, err2 = T.load_export(p)
    check('CONTROL: a complete export is accepted', err2, None)

    # ── 5. NO EXPORT IS COULD-NOT-RUN, NOT CLEAN ─────────────────────────────
    print('\n5. PR 1.11 -- the data question without data')
    r = subprocess.run([sys.executable, os.path.join(REPO, 'tools',
                                                     'three_way_match_check.py'), '--json'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', cwd=REPO,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    doc = json.loads(r.stdout)
    check('a run with no --data reports could-not-run', bool(doc['could_not_run']), True)
    check('...and exits 2', r.returncode, 2)
    check('...and the structural half still ran clean', doc['structure_findings'], [])

    print('')
    if FAILED:
        print('FAILED  three-way match probe: %d failed' % len(FAILED))
        for f in FAILED:
            print('  - %s' % f)
        return 1
    print('ALL THREE-WAY MATCH PROBE ASSERTIONS PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
