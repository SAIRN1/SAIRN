#!/usr/bin/env python
"""tests/run_claim_doc_freshness_probe.py -- the control on
tools/sairn_claim_doc_freshness.py, fixtures FIRST, real data LAST.

    python tests/run_claim_doc_freshness_probe.py

Exit 0 all arms pass, 1 an arm failed.

Cross-domain discipline 1: a check's criteria are locked against SYNTHETIC
fixtures before it touches real data, and both directions are driven -- a
checker that says OK to everything passes a positive-only fixture set, and one
that drifts everything passes a negative-only one. BOTH STREAMS are read on
every run: a control that reads stdout alone has already misreported itself
three separate times on this platform.
"""
import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'sairn_claim_doc_freshness.py')

FAILED = []


def run(args):
    r = subprocess.run([sys.executable, TOOL] + args, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def arm(name, ok, detail=''):
    print('  %-4s %s' % ('ok' if ok else 'FAIL', name))
    if not ok:
        if detail:
            print('       %s' % detail)
        FAILED.append(name)


# ── FIXTURES. A minimal tool-source carrying every anchor, and a CLAUDE.md
# carrying the matching statements. Synthetic names on purpose: a fixture that
# quotes real code is unreadable from a quotation of it.
TOOL_SRC = '\n'.join([
    "# CLAUDE.md already said \"read all four SAIRN-ACTIVE-WORK files before starting\"",
    "STALE_HOURS = float(os.environ.get('SAIRN_CLAIM_STALE_HOURS', '4'))",
    "# tools/sairn_status.py is already outside git, already written locally,",
    "# claims now carry `FILES: <paths>` in the task text.",
    ''])

CLAUDE_MD = '\n'.join([
    '2. **Read all four `SAIRN-ACTIVE-WORK-*.md` files** for the app.',
    '| Hank | `Documents\\SAIRN-hank` | `SAIRN-ACTIVE-WORK-hank.md` | `.claude/claims/hank.json` | build |',
    '| CC | `Documents\\SAIRN-cc` | `SAIRN-ACTIVE-WORK-cc.md` | `.claude/claims/cc.json` | build |',
    '| Cody | `Documents\\SAIRN-cody` | `SAIRN-ACTIVE-WORK-cody.md` | `.claude/claims/cody.json` | build |',
    '| Fourth | `Documents\\SAIRN-fourth` | `SAIRN-ACTIVE-WORK-fourth.md` | `.claude/claims/fourth.json` | build |',
    '- **Claims:** one file per clone. Expire after 4 hours.',
    ''])

CLAIM_JSON = ('{"claims": [{"status": "active", "task": '
              '"a task FILES: docs/x.md tools/y.py"}]}')


def main():
    print('CLAIM-DOC FRESHNESS PROBE -- fixtures first, real repo last\n')
    with tempfile.TemporaryDirectory() as td:
        tsrc = os.path.join(td, 'tool.py')
        cmd_ = os.path.join(td, 'CLAUDE.md')
        cdir = os.path.join(td, 'claims')
        outside = os.path.join(td, 'registry')
        inside = os.path.join(td, 'repo-root', 'registry')
        os.makedirs(cdir)
        os.makedirs(outside)
        os.makedirs(inside)
        io.open(tsrc, 'w', encoding='utf-8').write(TOOL_SRC)
        io.open(cmd_, 'w', encoding='utf-8').write(CLAUDE_MD)
        io.open(os.path.join(cdir, 'cc.json'), 'w', encoding='utf-8').write(CLAIM_JSON)
        base = ['--tool-src', tsrc, '--claude-md', cmd_, '--claims-dir', cdir,
                '--status-dir', outside, '--repo', os.path.join(td, 'repo-root')]

        print('POSITIVE -- clean fixtures verify')
        code, out = run(base)
        arm('clean fixtures -> exit 0, four OK rows',
            code == 0 and out.count(' OK ') >= 4, 'exit %d\n%s' % (code, out[-400:]))

        print('\nNEGATIVE -- each drift direction is caught, one at a time')
        # ── EVERY MUTATION ASSERTS ITS ANCHOR IS UNIQUE FIRST ─────────────
        # (2026-09-25, after tools/sabotage_control_check.py reported this
        # file as the platform's ONE unguarded control.) These mutate an
        # in-memory FIXTURE rather than a tracked file, so a rename cannot
        # reach them -- but the quiet failure is the same either way: an
        # anchor that stops matching leaves the "mutated" text identical to
        # the clean one, the checker correctly reports OK, and the NEGATIVE
        # arm reads that as a pass. A count catches both a miss and a
        # multi-match; presence catches only the miss.
        assert CLAUDE_MD.count('Expire after 4 hours') == 1,             'fixture anchor not unique -- the drift arm would mutate nothing'
        drifted = CLAUDE_MD.replace('Expire after 4 hours', 'Expire after 6 hours')
        assert drifted != CLAUDE_MD, 'the sabotage did not apply'
        io.open(cmd_, 'w', encoding='utf-8').write(drifted)
        code, out = run(base)
        arm('CLAUDE.md hours moved 4 -> 6: expiry-hours DRIFTED, exit 1',
            code == 1 and 'DRIFTED' in out and 'expiry-hours' in out,
            'exit %d\n%s' % (code, out[-400:]))
        io.open(cmd_, 'w', encoding='utf-8').write(CLAUDE_MD)

        assert CLAUDE_MD.count('| Fourth |') == 1,             'fixture anchor not unique -- the fifth-clone arm would mutate nothing'
        fifth = CLAUDE_MD.replace(
            '| Fourth |',
            '| Fifth | `Documents\\SAIRN-fifth` | `SAIRN-ACTIVE-WORK-fifth.md` |'
            ' `.claude/claims/fifth.json` | build |\n| Fourth |')
        assert fifth != CLAUDE_MD, 'the sabotage did not apply'
        io.open(cmd_, 'w', encoding='utf-8').write(fifth)
        code, out = run(base)
        arm('a FIFTH build clone appears: "four" goes stale in both docs, caught',
            code == 1 and 'active-work-instruction' in out and 'DRIFTED' in out,
            'exit %d\n%s' % (code, out[-400:]))
        io.open(cmd_, 'w', encoding='utf-8').write(CLAUDE_MD)

        assert TOOL_SRC.count('read all four SAIRN-ACTIVE-WORK files') == 1,             'fixture anchor not unique -- the reworded-anchor arm would mutate nothing'
        reworded = TOOL_SRC.replace('read all four SAIRN-ACTIVE-WORK files',
                                    'read every SAIRN-ACTIVE-WORK file')
        assert reworded != TOOL_SRC, 'the sabotage did not apply'
        io.open(tsrc, 'w', encoding='utf-8').write(reworded)
        code, out = run(base)
        arm('a reworded anchor is ANCHOR-GONE, not silently skipped',
            code == 1 and 'ANCHOR-GONE' in out,
            'exit %d\n%s' % (code, out[-400:]))
        io.open(tsrc, 'w', encoding='utf-8').write(TOOL_SRC)

        code, out = run(['--tool-src', tsrc, '--claude-md', cmd_,
                         '--claims-dir', cdir, '--status-dir', inside,
                         '--repo', os.path.join(td, 'repo-root')])
        arm('the registry resolving INSIDE the repo is DRIFTED',
            code == 1 and 'registry-outside-git' in out and 'DRIFTED' in out,
            'exit %d\n%s' % (code, out[-400:]))

        io.open(os.path.join(cdir, 'cc.json'), 'w', encoding='utf-8').write(
            '{"claims": [{"status": "active", "task": "a task naming no file set"}]}')
        code, out = run(base)
        arm('active claims with NO FILES: convention is DRIFTED',
            code == 1 and 'files-convention' in out and 'DRIFTED' in out,
            'exit %d\n%s' % (code, out[-400:]))
        io.open(os.path.join(cdir, 'cc.json'), 'w', encoding='utf-8').write(CLAIM_JSON)

        print('\nTHIRD STATE -- could-not-check is not a pass')
        code, out = run(['--tool-src', tsrc,
                         '--claude-md', os.path.join(td, 'gone.md'),
                         '--claims-dir', cdir, '--status-dir', outside,
                         '--repo', os.path.join(td, 'repo-root')])
        arm('a missing CLAUDE.md answers COULD NOT RUN and exit 2',
            code == 2 and 'COULD NOT RUN' in out, 'exit %d\n%s' % (code, out[-300:]))

        empty = os.path.join(td, 'claims-empty')
        os.makedirs(empty)
        code, out = run(['--tool-src', tsrc, '--claude-md', cmd_,
                         '--claims-dir', empty, '--status-dir', outside,
                         '--repo', os.path.join(td, 'repo-root')])
        arm('no active claims -> COULD-NOT-CHECK and exit 2, never OK',
            code == 2 and 'COULD-NOT-CHECK' in out and 'NOT A CLEAN BILL' in out,
            'exit %d\n%s' % (code, out[-300:]))

        print('\nCONTROL ON THE CONTROL -- restored fixtures are clean again')
        code, out = run(base)
        arm('after every mutation was reverted, clean fixtures still exit 0',
            code == 0, 'exit %d\n%s' % (code, out[-300:]))

    print('\nREAL DATA -- the actual repo, only after the criteria are locked')
    code, out = run([])
    arm('the real repo verifies today (exit 0) -- a non-zero here is a FINDING, '
        'not a probe bug', code == 0, 'exit %d\n%s' % (code, out))
    if code == 0:
        for ln in out.splitlines():
            if ln.strip().startswith(('OK', 'DRIFTED', 'COULD')):
                print('       %s' % ln.strip())

    print('')
    if FAILED:
        print('%d arm(s) FAILED: %s' % (len(FAILED), ', '.join(FAILED)))
        return 1
    print('all arms pass -- both directions driven, third state kept apart, '
          'real repo read last')
    return 0


if __name__ == '__main__':
    sys.exit(main())
