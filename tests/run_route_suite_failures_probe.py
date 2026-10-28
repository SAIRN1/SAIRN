#!/usr/bin/env python
"""The control for tools/route_suite_failures.py -- BOTH directions.

    python tests/run_route_suite_failures_probe.py

Exit 0 all arms pass, 1 any arm fails. Writes only to a temp directory; the
tool's bare run writes nothing and --out is never passed here.

The arms are M18 (2026-10-28). Two not-run shapes were read as nothing:
  * a triage row whose verdict was not REAL -- the default triage's 7
    COULD-NOT-RUN suites -- left the population with no count and no name;
  * a claim file that would not parse was `continue`d, so that session's
    declared paths routed as UNOWNED.
Each is planted on a built fixture; the CONTROL is a well-formed fixture that
must still route cleanly, so the arms are not satisfied by a tool that refuses
everything. Needs node (the registry is loaded through it) -- if node is
absent the tool exits 2 and every routing arm here reports FAIL, not skipped.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

CONTROLS_FOR = ['tools/route_suite_failures.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import route_suite_failures as R                                # noqa: E402

bad = 0


def arm(label, cond, detail=''):
    global bad
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         %s' % str(detail)[-400:]))
    if not cond:
        bad += 1


def call(fn, *a, **kw):
    """(return value, SystemExit code or None, captured stdout)."""
    buf = io.StringIO()
    rv = code = None
    with contextlib.redirect_stdout(buf):
        try:
            rv = fn(*a, **kw)
        except SystemExit as e:
            code = e.code
    return rv, code, buf.getvalue()


HDR = 'kind\ttest\tverdict\trc\tseconds\tdirtied\tsuite_reason\n'


def triage(tmp, rows):
    p = os.path.join(tmp, 'triage.tsv')
    with open(p, 'w', encoding='utf-8', newline='') as fh:
        fh.write(HDR)
        for test, verdict in rows:
            fh.write('py\t%s\t%s\t1\t0.1\t\t\n' % (test, verdict))
    return p


def main():
    print('ROUTE SUITE FAILURES -- probe')
    tmp = tempfile.mkdtemp(prefix='rsf-probe-')
    try:
        # ── claim files ──────────────────────────────────────────────────
        cdir = os.path.join(tmp, '.claude', 'claims')
        os.makedirs(cdir)
        with open(os.path.join(cdir, 'good.json'), 'w', encoding='utf-8') as fh:
            json.dump({'session': 'good', 'claims': []}, fh)
        _, code, out = call(R.load_claim_files, repo=tmp)
        arm('CONTROL: a directory of well-formed claim files loads without '
            'refusing', code is None, (code, out))
        with open(os.path.join(cdir, 'broken.json'), 'w', encoding='utf-8') as fh:
            fh.write('{"session": "broken", "claims": [')
        _, code, out = call(R.load_claim_files, repo=tmp)
        arm('an UNPARSEABLE claim file exits 2 COULD NOT RUN rather than being '
            'skipped', code == 2, (code, out))
        arm('...and the refusal NAMES the file', 'broken.json' in out, out)

        # ── triage verdicts ──────────────────────────────────────────────
        real, cnr, art = ('tests/zz_rsf_probe_real.py',
                          'tests/zz_rsf_probe_cnr.py',
                          'tests/zz_rsf_probe_artifact.py')
        p = triage(tmp, [(real, 'REAL')])
        rv, code, out = call(R.build, p)
        arm('CONTROL: a REAL-only triage builds and routes its one row',
            code is None and rv and [o['suite'] for o in rv[0]] == [real],
            (code, out[-300:]))

        p = triage(tmp, [(real, 'REAL'), (cnr, 'COULD-NOT-RUN'),
                         (art, 'ARTIFACT')])
        rv, code, out = call(R.build, p)
        suites = [o['suite'] for o in rv[0]] if rv else []
        arm('a COULD-NOT-RUN row is ROUTED, not dropped from the population',
            cnr in suites, (code, suites))
        arm('...while an ARTIFACT row is not routed', art not in suites, suites)
        rc, code, out = call(R.main, ['--triage', p])
        arm('the report prints a count per verdict, including COULD-NOT-RUN',
            rc == 0 and 'COULD-NOT-RUN 1' in out and 'ARTIFACT 1' in out
            and 'REAL 1' in out, (rc, code, out[:600]))
        arm('...and NAMES each COULD-NOT-RUN suite', '? %s' % cnr in out,
            out[:600])

        p = triage(tmp, [(real, 'REAL'), (cnr, 'WEIRD-VERDICT')])
        _, code, out = call(R.build, p)
        arm('a verdict the tool does not know exits 2 rather than vanishing',
            code == 2 and 'WEIRD-VERDICT' in out, (code, out[-300:]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
