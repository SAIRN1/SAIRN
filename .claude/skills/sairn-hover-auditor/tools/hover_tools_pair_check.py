#!/usr/bin/env python
r"""hover_tools_pair_check.py -- does any hover tool exist in BOTH the external
working directory (.claude/projects/.../hover-audit-log/) and the tracked tools
directory with DIFFERENT content, or only in the external one.

WHY THIS EXISTS (b84, Michael's decision). #1626 was found by hand in b71, b82
and b83 and cost a whole batch to reconcile: citation_class_check.py had
forked (661 lines of classifier only outside git, an abbreviation fix only
inside it), hover_completeness_probe.py was two different programs under one
name, two copies were stale, and hover_cold_scan_pool.py had a fix that lived
nowhere in git for 22 days. hover_external_unindexed_check.py cannot see any of
that: it asks whether a BASENAME is tracked, and every one of these was.

WHAT IT REPORTS, per name (extensions .py and .js):
  IDENTICAL         byte for byte. Fine.
  CRLF-ONLY         equal after normalising line endings. NOT drift (CLAUDE.md:
                    a CRLF-versus-LF difference is not drift); counted only.
  DIFFERS           real content difference. DRIFT. Prints which side has lines
                    the other lacks, so the dangerous direction (code that
                    exists only outside git) is visible at once.
  ONLY-EXTERNAL     in the external directory, nowhere in the tracked one.
                    DRIFT, unless EXEMPT below carries a reason for that name.
  ONLY-TRACKED      tracked and absent externally. Fine: the external directory
                    is a working copy, not an inventory.

EXIT: 0 no drift. 1 drift. 2 COULD NOT RUN (a directory is missing or
unreadable). A missing directory is never folded into "no drift": a check whose
inputs are absent reports nothing, and that must not read as a pass.

EXEMPT is a short named list with a reason on each entry, in this file, not a
glob. An exemption added without a reason is a skip added without a sentence.

Read-only. Writes nothing. No network. No subprocess.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRACKED_DIR = HERE
EXTERNAL_DIR = os.path.join(os.path.expanduser('~'), '.claude', 'projects',
                            'C--Users-marsh-Documents-SAIRN-hover',
                            'hover-audit-log')
EXTENSIONS = ('.py', '.js')
EXEMPT = {
    '.mirror-askpass.py': 'six-line credential helper that only names the local '
                          'mirror token path; kept out of git on purpose',
}


def _read(path):
    with open(path, 'rb') as f:
        return f.read()


def _norm(b):
    return b.replace(b'\r\n', b'\n')


def _names(d):
    return {n for n in os.listdir(d)
            if n.lower().endswith(EXTENSIONS) and os.path.isfile(os.path.join(d, n))}


def compare(tracked_dir, external_dir):
    """(rows, error). rows = [(name, verdict, detail)]; error = text or None."""
    for label, d in (('tracked', tracked_dir), ('external', external_dir)):
        if not os.path.isdir(d):
            return None, 'the %s directory does not exist: %s' % (label, d)
    try:
        tn, en = _names(tracked_dir), _names(external_dir)
    except OSError as e:
        return None, 'could not list a directory: %s' % e
    rows = []
    for name in sorted(tn | en):
        tp, ep = os.path.join(tracked_dir, name), os.path.join(external_dir, name)
        if name in en and name not in tn:
            if name in EXEMPT:
                rows.append((name, 'EXEMPT', EXEMPT[name]))
            else:
                rows.append((name, 'ONLY-EXTERNAL',
                             '%d lines exist nowhere in git' % len(_norm(_read(ep)).splitlines())))
            continue
        if name in tn and name not in en:
            rows.append((name, 'ONLY-TRACKED', ''))
            continue
        try:
            tb, eb = _read(tp), _read(ep)
        except OSError as e:
            return None, 'could not read %s: %s' % (name, e)
        if tb == eb:
            rows.append((name, 'IDENTICAL', ''))
        elif _norm(tb) == _norm(eb):
            rows.append((name, 'CRLF-ONLY', ''))
        else:
            tl, el = set(_norm(tb).splitlines()), set(_norm(eb).splitlines())
            rows.append((name, 'DIFFERS',
                         '%d line(s) only in the external copy, %d line(s) only in the tracked copy'
                         % (len(el - tl), len(tl - el))))
    return rows, None


DRIFT = ('DIFFERS', 'ONLY-EXTERNAL')


def drift(rows):
    return [r for r in rows if r[1] in DRIFT]


def report(tracked_dir=TRACKED_DIR, external_dir=EXTERNAL_DIR):
    """dict for hover_self_health: ran, FAIL_drift, drift, counts, reason."""
    rows, err = compare(tracked_dir, external_dir)
    if err:
        return {'ran': False, 'reason': err, 'FAIL_drift': False, 'drift': [], 'counts': {}}
    counts = {}
    for _n, v, _d in rows:
        counts[v] = counts.get(v, 0) + 1
    d = drift(rows)
    return {'ran': True, 'reason': '', 'FAIL_drift': bool(d), 'counts': counts,
            'drift': [{'name': n, 'verdict': v, 'detail': x} for n, v, x in d]}


def _fixtures():
    import tempfile
    ok = [0]
    bad = [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    def mk(root, tree):
        os.makedirs(root, exist_ok=True)
        for n, b in tree.items():
            with open(os.path.join(root, n), 'wb') as f:
                f.write(b)

    base = tempfile.mkdtemp(prefix='pair_fx_')
    t, e = os.path.join(base, 't'), os.path.join(base, 'e')
    mk(t, {'same.py': b'a = 1\n', 'crlf.py': b'x = 1\ny = 2\n', 'forked.py': b'a\nb\nc\n',
           'tonly.py': b'z\n', 'note.md': b'ignored\n'})
    mk(e, {'same.py': b'a = 1\n', 'crlf.py': b'x = 1\r\ny = 2\r\n', 'forked.py': b'a\nB\nc\nnew\n',
           'eonly.py': b'only here\nand here\n', '.mirror-askpass.py': b'print(1)\n',
           'other.txt': b'ignored\n'})
    rows, err = compare(t, e)
    v = {n: x for n, x, _d in rows}
    ck('no error on two real directories', err is None)
    ck('byte-identical is IDENTICAL', v.get('same.py') == 'IDENTICAL')
    ck('CRLF-only difference is CRLF-ONLY and is NOT drift',
       v.get('crlf.py') == 'CRLF-ONLY' and 'crlf.py' not in [r[0] for r in drift(rows)])
    ck('a real content difference is DIFFERS', v.get('forked.py') == 'DIFFERS')
    ck('DIFFERS says which side holds lines the other lacks',
       [d for n, x, d in rows if n == 'forked.py'] == ['2 line(s) only in the external copy, 1 line(s) only in the tracked copy'])
    ck('an external-only tool is ONLY-EXTERNAL and is drift',
       v.get('eonly.py') == 'ONLY-EXTERNAL' and 'eonly.py' in [r[0] for r in drift(rows)])
    ck('an exempt name is EXEMPT with its reason and is NOT drift',
       v.get('.mirror-askpass.py') == 'EXEMPT' and '.mirror-askpass.py' not in [r[0] for r in drift(rows)])
    ck('a tracked-only tool is ONLY-TRACKED and is NOT drift',
       v.get('tonly.py') == 'ONLY-TRACKED' and 'tonly.py' not in [r[0] for r in drift(rows)])
    ck('non-tool extensions are not looked at', 'note.md' not in v and 'other.txt' not in v)
    ck('report() sets FAIL_drift with the drifting names',
       report(t, e)['FAIL_drift'] and {x['name'] for x in report(t, e)['drift']} == {'forked.py', 'eonly.py'})
    rows2, err2 = compare(t, os.path.join(base, 'missing'))
    ck('a missing directory is COULD NOT RUN, never a clean pass',
       rows2 is None and 'does not exist' in err2 and report(t, os.path.join(base, 'missing'))['ran'] is False
       and report(t, os.path.join(base, 'missing'))['FAIL_drift'] is False)
    # known-bad control: a checker that only compares file SIZES for shared names
    # and never looks at external-only names must miss the planted cases.
    def broken(td, ed):
        out = []
        for n in sorted(_names(td) & _names(ed)):
            if len(_read(os.path.join(td, n))) != len(_read(os.path.join(ed, n))):
                out.append(n)
        return out
    mk(t, {'same_len.py': b'abcd\n'})
    mk(e, {'same_len.py': b'abXd\n'})
    ck('KNOWN-BAD CONTROL: a size-only, shared-names-only checker MISSES the same-length edit and the external-only tool',
       'same_len.py' not in broken(t, e) and 'eonly.py' not in broken(t, e))
    rows3, _ = compare(t, e)
    ck('...and the real check catches both', {r[0] for r in drift(rows3)} >= {'same_len.py', 'eonly.py'})
    # the real pair, today: the dispatch must run and never raise
    real = report()
    ck('the real directories can be compared (ran is True, or a stated reason)',
       real['ran'] is True or bool(real['reason']))
    print()
    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


def main(argv):
    if '--selftest' in argv:
        return 0 if _fixtures() else 1
    tracked, external = TRACKED_DIR, EXTERNAL_DIR
    if '--tracked' in argv:
        tracked = argv[argv.index('--tracked') + 1]
    if '--operational' in argv:
        external = argv[argv.index('--operational') + 1]
    rows, err = compare(tracked, external)
    if err:
        print('COULD NOT RUN: %s' % err)
        return 2
    counts = {}
    for _n, v, _d in rows:
        counts[v] = counts.get(v, 0) + 1
    d = drift(rows)
    print('HOVER TOOL PAIRS -- tracked %s vs external %s' % (tracked, external))
    print('  %s' % ', '.join('%s %d' % (k, counts[k]) for k in sorted(counts)))
    for n, v, x in rows:
        if v in DRIFT:
            print('  DRIFT %-14s %s  %s' % (v, n, x))
    if d:
        print('DRIFT: %d tool(s). Reconcile before editing either copy; copying over can destroy the other side.' % len(d))
        return 1
    print('NO DRIFT. (CRLF-only and tracked-only names are not drift; this is not a statement that either copy is correct.)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
