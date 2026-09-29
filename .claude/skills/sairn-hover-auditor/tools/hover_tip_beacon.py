#!/usr/bin/env python
"""
hover_tip_beacon.py -- a passive, second signal for the self-log's integrity,
distinct from the hash chain. Built 2026-09-15, on Michael's direct request.

WHY THIS IS A SECOND MECHANISM, NOT A SECOND COPY OF --verify.

--verify (hover_log.py) is ACTIVE: it replays the whole chain, from GENESIS,
every time, and only reports tampering to whoever remembers to run it. A
physical tamper seal does not have that requirement -- it is broken the
moment tampering happens and stays visibly broken to anyone who simply looks,
with no recomputation. This tool is the closest analog available for a text
log: a small, separate, human-readable file that states a checkpoint claim in
plain words, so a MISMATCH is visible on casual inspection without running
the chain verifier at all -- and a spot-check against one checkpointed line is
O(1), not the O(n) full replay --verify does.

WHAT IT DOES NOT REPLACE. This is not a substitute for --verify, which is
still the only thing that proves the WHOLE chain is intact. This is a cheap,
passive tripwire that makes staleness or a checkpoint-line mismatch visible
without anyone having to think to run the expensive check -- the two are
complementary, the same way a tamper seal and a periodic full audit both
exist on the same real container without either replacing the other.

Run:
  python hover_tip_beacon.py --publish             write/refresh the beacon
  python hover_tip_beacon.py --publish --anchor    also emit the EXTERNAL
                                                    anchor payload (below)
  python hover_tip_beacon.py --check               passive check, exit 0/1/2
  python hover_tip_beacon.py --selftest            negative controls, must fail before trusted

EXTERNAL ANCHOR (--anchor), added 2026-09-28, Michael's approved design.

WHY THE BEACON ABOVE IS NOT ENOUGH, STATED PLAINLY. hover_log.py --verify
recomputes the WHOLE chain from the log's own bytes, and this beacon file is
a second FILE next to it -- same directory, same filesystem, same writer
(io.open() a few lines up is its only output). A hash chain is
TAMPER-EVIDENT against someone who edits without recomputing; it is NOT
tamper-PROOF against someone who edits AND recomputes AND republishes this
beacon, because all three of those are one actor with the same access. That
gap was confirmed empty on audit 2026-09-27 (H1 log #555) -- no external
anchor existed anywhere in this role's tooling.

WHAT --anchor DOES, AND WHY IT CANNOT DO MORE FROM INSIDE THIS SCRIPT. This
script is a plain subprocess with no MCP tool access, so it cannot itself
send an email -- only the live session driving it can, through the Gmail
connector. --anchor's job is therefore narrow and honest: compute the
four-field payload (seq, hash, total_entries, timestamp) and print it on
its own line, prefixed `ANCHOR_PAYLOAD: `, as a single-line JSON blob. THE
SESSION THEN SENDS IT. This script never claims to have anchored anything
by itself -- printing the payload is as far as a subprocess can go, and the
docstring says so rather than implying automation that is not there.

THE HONEST LIMIT ON CADENCE, disclosed rather than promised away: the Gmail
connector is session-interactive. A headless or cron run of --anchor still
prints the payload (so nothing is silently dropped), but nothing sends it
until a live session with that connector reads the output and acts. The
cadence is therefore "every live session that runs --publish --anchor",
not "guaranteed periodic" -- the beacon's own 15-entry staleness alarm
already bounds how far the log can drift between anchors a reader would
notice, so a missed cadence degrades gracefully rather than silently.

HOW A DISAGREEMENT IS PROVEN, LATER: any received anchor email pins one
REAL (seq, hash) pair to an independent timestamp (Gmail's received time,
outside this machine's write path). To check for a rewrite, take that
(seq, hash) and compare it against what `hover_log.py --verify`'s live
recompute says entry `seq` currently hashes to. A match proves the chain
has not been rewritten between the anchor's date and now; a mismatch
proves it has, and bounds WHEN.

FALLBACK, NAMED AND DELIBERATELY SECONDARY (not yet wired -- git-based,
does not need a live connector): append the same line to a small
`TIP-ANCHOR` file in `.claude/skills/sairn-hover-auditor/` and push it --
origin's history and every other clone's copy sit outside this one
machine's exclusive write path, which is weaker than an independent
mailbox (the same git identity could still force-push over it) but does
not depend on any session having a connector live. Left for a future queue
item; --anchor's job today is the approved email path only.
"""

import io
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hover_log import LOG_PATH, GENESIS, digest_of, read_all  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BEACON_PATH = os.path.join(HERE, 'TIP-BEACON.md')

# A beacon older than this many entries behind the real tip is STALE. Chosen
# to be smaller than a typical session's own entry count (this session alone
# produced 100+), so staleness is caught within roughly one working session,
# not left for someone to notice weeks later.
STALE_AFTER_ENTRIES = 15

EXIT_OK = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2


def render(seq, ts, entry_hash, total_entries, published_at):
    return (
        '# Hover-auditor self-log tip beacon\n\n'
        'A PASSIVE second signal, distinct from `hover_log.py --verify`. '
        'This file states a checkpoint claim in plain text -- if the number '
        'below does not match the log entry it names, or if this file looks '
        'old next to how many entries the log now has, that is visible by '
        'READING, with no script required. Full account: hover_tip_beacon.py.\n\n'
        '```\n'
        'checkpoint_seq   : %d\n'
        'checkpoint_ts    : %s\n'
        'checkpoint_hash  : %s\n'
        'total_entries_at_publish : %d\n'
        'beacon_published_at      : %s\n'
        '```\n\n'
        'To spot-check by eye: open hover-audit-log.jsonl, find the line whose '
        '"seq" is %d, and confirm its own "hash" field reads exactly '
        '`%s`. A different value there is tampering visible without running '
        'anything. A HUGE gap between total_entries_at_publish and the real '
        'current line count is staleness -- this beacon has not been refreshed '
        'in a while and should not be trusted as current.\n'
        % (seq, ts, entry_hash, total_entries, published_at, seq, entry_hash)
    )


def anchor_payload(tip, total_entries, now):
    """The exact four fields the external anchor carries, and nothing else
    -- locked shape so a downstream reader (the session sending the email,
    or a future --verify-anchor) has a stable contract rather than parsing
    prose. seq/hash are what --verify recomputes against later; count and
    timestamp are for a human glancing at the email."""
    return {
        'seq': tip['seq'],
        'tip_hash': tip['hash'],
        'total_entries': total_entries,
        'anchored_at': now,
    }


def cmd_publish(argv):
    try:
        entries = read_all()
    except ValueError as e:
        print('COULD NOT RUN: log does not parse -- %s' % e)
        return EXIT_COULD_NOT_RUN
    if not entries:
        print('COULD NOT RUN: log is empty, nothing to checkpoint')
        return EXIT_COULD_NOT_RUN
    tip = entries[-1]
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    text = render(tip['seq'], tip['ts'], tip['hash'], len(entries), now)
    io.open(BEACON_PATH, 'w', encoding='utf-8', newline='\n').write(text)
    print('published: seq=%d hash=%s total=%d' % (tip['seq'], tip['hash'], len(entries)))
    if '--anchor' in argv:
        payload = anchor_payload(tip, len(entries), now)
        # ONE line, machine-parseable, so the driving session does not have
        # to re-derive the payload from the prose above it.
        print('ANCHOR_PAYLOAD: ' + json.dumps(payload, sort_keys=True))
        print('ANCHOR NOT YET SENT -- this script has no mail access. The '
              'live session must read the ANCHOR_PAYLOAD line above and '
              'send it via the Gmail connector to be a real external anchor.')
    return EXIT_OK


def _parse_beacon(text):
    """Pull the four checkpoint fields back out of the rendered beacon.
    Deliberately reads the fenced block by KEY, not by fixed line number --
    a beacon whose prose around the block changed should not silently
    misparse into the wrong field."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        for key in ('checkpoint_seq', 'checkpoint_ts', 'checkpoint_hash',
                    'total_entries_at_publish', 'beacon_published_at'):
            prefix = key + ' '
            if line.startswith(prefix) and ':' in line:
                out[key] = line.split(':', 1)[1].strip()
    return out


def cmd_check(argv):
    if not os.path.isfile(BEACON_PATH):
        print('COULD NOT RUN: no beacon published yet -- run --publish first')
        return EXIT_COULD_NOT_RUN
    beacon_text = io.open(BEACON_PATH, encoding='utf-8').read()
    fields = _parse_beacon(beacon_text)
    required = ('checkpoint_seq', 'checkpoint_hash', 'total_entries_at_publish')
    missing = [k for k in required if k not in fields]
    if missing:
        print('COULD NOT RUN: beacon is unparsable -- missing %s. A beacon '
              'that cannot be read is not a passing check.' % missing)
        return EXIT_COULD_NOT_RUN

    try:
        entries = read_all()
    except ValueError as e:
        print('COULD NOT RUN: log does not parse -- %s' % e)
        return EXIT_COULD_NOT_RUN

    checkpoint_seq = int(fields['checkpoint_seq'])
    by_seq = dict((e['seq'], e) for e in entries)
    if checkpoint_seq not in by_seq:
        print('FINDING: beacon checkpoints seq %d, which no longer exists in '
              'the log at all.' % checkpoint_seq)
        return EXIT_FINDING

    live_hash = by_seq[checkpoint_seq]['hash']
    if live_hash != fields['checkpoint_hash']:
        print('FINDING: MISMATCH at seq %d. beacon says hash=%s, log line '
              'currently reads hash=%s. This is the tamper-seal-broken case.'
              % (checkpoint_seq, fields['checkpoint_hash'], live_hash))
        return EXIT_FINDING

    gap = len(entries) - int(fields['total_entries_at_publish'])
    if gap > STALE_AFTER_ENTRIES:
        print('FINDING: STALE. beacon published at %d entries; log now has '
              '%d (%d entries behind, over the %d threshold). Not tampering '
              '-- the beacon simply has not been refreshed.'
              % (int(fields['total_entries_at_publish']), len(entries), gap,
                 STALE_AFTER_ENTRIES))
        return EXIT_FINDING

    print('OK: checkpoint seq %d matches the live log; beacon is %d '
          'entries behind the current tip (within the %d-entry staleness '
          'bound).' % (checkpoint_seq, gap, STALE_AFTER_ENTRIES))
    return EXIT_OK


def cmd_selftest(argv):
    """A checker that has never been shown to fail is not yet a checker.
    Real negative controls against a scratch beacon + scratch log, never the
    real files."""
    import tempfile
    import shutil

    scratch = tempfile.mkdtemp(prefix='beacon_selftest_')
    try:
        global BEACON_PATH, LOG_PATH
        real_beacon, real_log = BEACON_PATH, LOG_PATH
        BEACON_PATH = os.path.join(scratch, 'TIP-BEACON.md')
        LOG_PATH = os.path.join(scratch, 'log.jsonl')

        import hover_log
        hover_log.LOG_PATH = LOG_PATH

        def write_log(rows):
            with io.open(LOG_PATH, 'w', encoding='utf-8') as f:
                for r in rows:
                    f.write(json.dumps(r) + '\n')

        def entry(seq, prev):
            body = {'seq': seq, 'ts': '2026-01-01T00:00:00Z', 'type': 'note',
                     'target': 'self', 'summary': 'x', 'severity': '',
                     'ref': '', 'vector': '', 'retrospective': False,
                     'prev_hash': prev}
            h = digest_of(prev, body)
            body['hash'] = h
            return body

        ok = 0
        fail = 0

        def check(name, cond):
            nonlocal ok, fail
            if cond:
                ok += 1
                print('  ok   ' + name)
            else:
                fail += 1
                print('  FAIL ' + name)

        # 1. Clean publish/check round-trips OK.
        e1 = entry(1, GENESIS)
        write_log([e1])
        rc = cmd_publish([])
        check('a clean single-entry log publishes OK', rc == EXIT_OK)
        rc = cmd_check([])
        check('...and immediately checks OK', rc == EXIT_OK)

        # 2. TAMPER: flip the checkpointed entry's hash in the log after publish.
        tampered = dict(e1)
        tampered['hash'] = 'not-the-real-hash'
        write_log([tampered])
        rc = cmd_check([])
        check('TEETH: a tampered checkpoint line is caught as MISMATCH, not OK',
              rc == EXIT_FINDING)
        write_log([e1])  # restore
        rc = cmd_check([])
        check('...and checking OK again after restore', rc == EXIT_OK)

        # 3. STALE: grow the log far past the beacon without republishing.
        rows = [e1]
        prev = e1['hash']
        for i in range(2, STALE_AFTER_ENTRIES + 5):
            e = entry(i, prev)
            rows.append(e)
            prev = e['hash']
        write_log(rows)
        rc = cmd_check([])
        check('TEETH: a beacon left far behind the real tip reports STALE',
              rc == EXIT_FINDING)

        # 3b. --anchor: locked payload shape, printed not sent (fixture,
        # 2026-09-28). Captures stdout rather than re-deriving the parse.
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_publish(['--anchor'])
        out = buf.getvalue()
        check('--anchor still returns OK (printing a payload is not a '
              'failure mode)', rc == EXIT_OK)
        check('--anchor emits exactly one ANCHOR_PAYLOAD line',
              out.count('ANCHOR_PAYLOAD: ') == 1)
        line = next(l for l in out.splitlines() if l.startswith('ANCHOR_PAYLOAD: '))
        payload = json.loads(line[len('ANCHOR_PAYLOAD: '):])
        check('payload carries exactly the four locked fields, no more no less',
              set(payload.keys()) == {'seq', 'tip_hash', 'total_entries', 'anchored_at'})
        check('payload seq/hash match the CURRENT tip, not a stale one',
              payload['seq'] == rows[-1]['seq'] and payload['tip_hash'] == rows[-1]['hash'])
        check('TEETH: --anchor NEVER claims to have sent anything -- the '
              "honest 'ANCHOR NOT YET SENT' line is always present",
              'ANCHOR NOT YET SENT' in out)
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            cmd_publish([])  # plain publish must NOT print a payload
        check('plain --publish (no --anchor) prints no ANCHOR_PAYLOAD line',
              'ANCHOR_PAYLOAD' not in buf2.getvalue())

        # 4. COULD-NOT-RUN, not a silent pass: no beacon at all.
        os.remove(BEACON_PATH)
        rc = cmd_check([])
        check('no beacon published yet -> COULD NOT RUN, never OK',
              rc == EXIT_COULD_NOT_RUN)

        # 5. COULD-NOT-RUN on an unparsable beacon (not silently OK).
        io.open(BEACON_PATH, 'w', encoding='utf-8').write('garbage, no fields here')
        rc = cmd_check([])
        check('an unparsable beacon -> COULD NOT RUN, never OK',
              rc == EXIT_COULD_NOT_RUN)

        print('')
        print('%d ok, %d failed' % (ok, fail))
        return EXIT_FINDING if fail else EXIT_OK
    finally:
        BEACON_PATH, LOG_PATH = real_beacon, real_log
        hover_log.LOG_PATH = real_log
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv):
    if '--publish' in argv:
        return cmd_publish(argv)
    if '--check' in argv:
        return cmd_check(argv)
    if '--selftest' in argv:
        return cmd_selftest(argv)
    print('usage: hover_tip_beacon.py --publish | --check | --selftest')
    return EXIT_COULD_NOT_RUN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
