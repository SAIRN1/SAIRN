"""tools/hover_process_pass_freshness.py must FAIL on a late auditor.

Run: python tests/hover_process_pass_freshness_probe.py

A CHECK THAT HAS ONLY EVER RUN AGAINST A HEALTHY SUBJECT HAS NOT BEEN SEEN TO
WORK. This one runs, today, against a log whose last process pass is under an
hour old -- which is exactly the state in which a broken staleness check and a
working one are indistinguishable.

So every verdict is driven against a SYNTHETIC log built here, with its own
valid hash chain, written from the canonicalisation rule rather than borrowed
from the tool under test where that is possible. The four states are:

  FRESH        -> 0
  WARN         -> 0, and it says so (early notice is not a finding)
  STALE        -> 1
  COULD NOT RUN-> 2, for a missing log, a broken chain, and a log with no
                  flagged entry at all

THE THIRD STATE IS THE ONE THIS PROBE EXISTS FOR. A staleness check that
answers "fresh" when it cannot read the log is worse than no check: it converts
an absent auditor into a positive statement. Three separate arms drive that.

AND ONE ARM IS ABOUT WHAT IT REFUSES TO DO. A log whose newest entry is recent
but whose newest FLAGGED entry is old must read STALE -- the auditor writing
ordinary audit entries is not the auditor running a process pass, and a check
that took the newest entry of any kind would report a busy auditor as compliant
while the machinery pass had not happened for days.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOL = os.path.join(REPO, 'tools', 'hover_process_pass_freshness.py')
GENESIS = 'genesis:hover-auditor-self-log:v1'

FAILURES = []
TEMPS = []


def arm(name, ok, detail=''):
    print(('  ok   ' if ok else '  FAIL ') + name)
    if not ok:
        print('         ' + str(detail)[:300])
        FAILURES.append(name)
    return bool(ok)


def canonical(value):
    """Written from the rule. A paste would agree with the tool even when the
    tool is wrong, which is the whole reason the audit tool says it wrote its
    own rather than copying hover_log.py's."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return json.dumps(value)
    if isinstance(value, list):
        return '[' + ','.join(canonical(v) for v in value) + ']'
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k) + ':' + canonical(value[k])
                              for k in sorted(value)) + '}'
    raise TypeError(repr(value))


def chain(entries):
    """Attach prev_hash/hash so the log verifies."""
    out, prev = [], GENESIS
    for e in entries:
        body = dict(e)
        body['prev_hash'] = prev
        h = hashlib.sha256()
        h.update((prev + '\n').encode('utf-8'))
        h.update((canonical(body) + '\n').encode('utf-8'))
        d = h.hexdigest()
        body['hash'] = d
        out.append(body)
        prev = d
    return out


def stamp(hours_ago):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ',
                         time.gmtime(time.time() - hours_ago * 3600))


def write_log(entries):
    tmp = tempfile.mkdtemp(prefix='hpf-')
    TEMPS.append(tmp)
    p = os.path.join(tmp, 'hover-audit-log.jsonl')
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        for r in entries:
            f.write(json.dumps(r) + '\n')
    return p


def run(log_path, *extra):
    env = dict(os.environ)
    if log_path is None:
        env['SAIRN_HOVER_LOG'] = os.path.join(TEMPS[0] if TEMPS else '.', 'nope.jsonl')
    else:
        env['SAIRN_HOVER_LOG'] = log_path
    r = subprocess.run([sys.executable, TOOL] + list(extra), cwd=REPO, env=env,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def entry(seq, hours_ago, pp, summary='x'):
    return {'seq': seq, 'ts': stamp(hours_ago), 'type': 'check',
            'process_pass': pp, 'summary': summary, 'target': '', 'ref': '',
            'severity': '', 'vector': '', 'retrospective': False,
            'eqa_checkpoint': False, 'same_target_reason': ''}


def main():
    try:
        print('hover process-pass freshness -- every verdict driven\n')

        # The tool's own criteria lock comes first: if that is red, nothing
        # below means anything.
        rc, out = run(write_log(chain([entry(1, 1, True)])), '--selftest')
        arm('the tool\'s own --selftest passes before any verdict is driven',
            rc == 0, 'exit %d\n%s' % (rc, out[-300:]))

        # 1. FRESH
        p = write_log(chain([entry(1, 100, False), entry(2, 2, True)]))
        rc, out = run(p)
        arm('a process pass 2h old is OK (exit 0)', rc == 0 and 'OK:' in out,
            'exit %d\n%s' % (rc, out[-300:]))

        # 2. WARN -- past the warn bound, inside the fail bound
        p = write_log(chain([entry(1, 40, True)]))
        rc, out = run(p)
        arm('40h is a WARN and still exit 0 -- an irregular cadence is not a '
            'finding', rc == 0 and 'WARN:' in out, 'exit %d\n%s' % (rc, out[-300:]))

        # 3. STALE
        p = write_log(chain([entry(1, 60, True)]))
        rc, out = run(p)
        arm('60h is STALE (exit 1)', rc == 1 and 'STALE:' in out,
            'exit %d\n%s' % (rc, out[-300:]))
        arm('...and the message says what a process pass IS, so the reader '
            'knows what is missing', 'all four build agents' in out, out[-300:])

        # 4. THE ARM THIS EXISTS FOR: busy auditor, no process pass.
        p = write_log(chain([entry(1, 60, True), entry(2, 30, False),
                             entry(3, 1, False), entry(4, 0.2, False)]))
        rc, out = run(p)
        arm('a BUSY auditor with no recent process pass is STALE -- the newest '
            'entry is 0.2h old and the newest FLAGGED one is 60h old',
            rc == 1 and 'STALE:' in out, 'exit %d\n%s' % (rc, out[-400:]))

        # 5. COULD NOT RUN -- missing log
        rc, out = run(None)
        arm('a MISSING log is exit 2, not fresh and not stale',
            rc == 2 and 'COULD NOT RUN' in out, 'exit %d\n%s' % (rc, out[-300:]))

        # 6. COULD NOT RUN -- broken chain
        rows = chain([entry(1, 5, True)])
        rows[0]['summary'] = 'edited after the fact'
        p = write_log(rows)
        rc, out = run(p)
        arm('a log whose HASH CHAIN does not verify is exit 2 -- a timestamp '
            'from an unverified chain is the subject vouching for itself',
            rc == 2 and 'CHAIN' in out.upper(), 'exit %d\n%s' % (rc, out[-300:]))

        # 7. COULD NOT RUN -- no flagged entry at all
        p = write_log(chain([entry(1, 2, False, 'PROCESS PASS in the prose only')]))
        rc, out = run(p)
        arm('a log with NO flagged entry is exit 2, and the prose saying '
            '"PROCESS PASS" does not count', rc == 2,
            'exit %d\n%s' % (rc, out[-300:]))
        arm('...and it says WHY it will not read the prose',
            'load-bearing' in out, out[-300:])

        # 8. CONTROL: the bounds are arguments, so the verdict follows them.
        p = write_log(chain([entry(1, 60, True)]))
        rc, out = run(p, '--fail-hours', '72')
        arm('CONTROL: the same 60h log passes at --fail-hours 72, so the '
            'verdict is driven by the bound and not by something else',
            rc == 0, 'exit %d\n%s' % (rc, out[-300:]))
    finally:
        for t in TEMPS:
            shutil.rmtree(t, ignore_errors=True)

    print('')
    if FAILURES:
        print('%d ARM(S) FAILED' % len(FAILURES))
        return 1
    print('ALL ARMS PASS -- fresh, warn, stale, busy-but-stale, and three '
          'separate COULD NOT RUN states are each driven.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
