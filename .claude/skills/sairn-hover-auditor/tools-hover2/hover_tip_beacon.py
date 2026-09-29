#!/usr/bin/env python
"""hover_tip_beacon.py (hover2's own build) -- passive tamper seal for this
instance's self-log, implemented from hover_parity_specs.md #1 (H1,
2026-09-24), not from H1's source.

WHY A SECOND SIGNAL: hover_log.py --verify is the ACTIVE check -- O(n),
replays the chain, reports only when someone runs it. The beacon is the
passive tamper-seal analog (SKILL.md's weights-and-measures material: a
physical seal is visible broken WITHOUT anyone running a verifier): a small
human-readable file stating a checkpoint claim -- entry count, tip seq, tip
hash, published-at -- so mismatch or staleness shows on casual inspection,
O(1).

VERDICTS, three-plus-one, never two (spec's common contract):
  PASS (0)          checkpoint matches the log entry at that seq, growth
                    since publish < STALE_AFTER.
  MISMATCH (1)      the checkpointed (seq, hash) no longer matches the
                    log's actual entry at that seq -- the seal is broken;
                    possible rewrite of already-checkpointed history.
  STALE (1)         checkpoint still matches but the log has grown >=
                    STALE_AFTER entries past it. NOT tampering -- the
                    output says so; remedy is --verify then --publish,
                    never an alarm.
  COULD-NOT-RUN (2) beacon absent, log unreadable, or tip malformed.

STALE_AFTER = 15 -- REASONED, not measured (same starting number as H1's,
kept deliberately: divergence here would just make the two beacons age
differently for no informational gain); output states this on every run
until a real republish-gap history exists to calibrate from.

MUST NOT (spec): substitute for full chain verification, or auto-republish
on MISMATCH -- a broken seal must be seen by a human before it is re-armed.
--publish therefore REFUSES (exit 1) when --check currently says MISMATCH,
unless --force-after-verify is given, which exists for exactly one flow:
a human ran hover_log.py --verify, read the answer, and said so.

Run:
  python hover_tip_beacon.py --check              # default
  python hover_tip_beacon.py --publish
  python hover_tip_beacon.py --selftest           # negative controls
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'hover-audit-log.jsonl')
BEACON = os.path.join(HERE, 'TIP-BEACON.md')
STALE_AFTER = 15  # REASONED starting number, not yet calibrated -- see doc


def read_log(path):
    """-> (entries, err)"""
    try:
        entries = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries, None
    except (OSError, ValueError) as e:
        return None, str(e)


def tip_of(entries):
    """-> (count, seq, hash) or (None, None, None) if tip malformed."""
    if not entries:
        return None, None, None
    tip = entries[-1]
    if 'seq' not in tip or 'hash' not in tip:
        return None, None, None
    return len(entries), tip['seq'], tip['hash']


def parse_beacon(path):
    """-> (dict, err). The beacon is markdown for humans with one JSON line
    for machines -- the line starting 'CHECKPOINT: '."""
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.startswith('CHECKPOINT: '):
                    return json.loads(line[len('CHECKPOINT: '):]), None
        return None, 'no CHECKPOINT line found in %s' % path
    except (OSError, ValueError) as e:
        return None, str(e)


def check(log_path=LOG, beacon_path=BEACON, stale_after=STALE_AFTER,
          out=print):
    if not os.path.exists(beacon_path):
        out('COULD NOT RUN: no beacon at %s -- nothing has been published; '
            'run --publish after a clean --verify. (exit 2)' % beacon_path)
        return 2
    cp, err = parse_beacon(beacon_path)
    if cp is None:
        out('COULD NOT RUN: beacon unreadable (%s). (exit 2)' % err)
        return 2
    entries, err = read_log(log_path)
    if entries is None:
        out('COULD NOT RUN: log unreadable (%s) -- that is a third state, '
            'never a pass. (exit 2)' % err)
        return 2
    want_seq, want_hash = cp.get('seq'), cp.get('hash')
    at = [e for e in entries if e.get('seq') == want_seq]
    if not at or at[0].get('hash') != want_hash:
        out('MISMATCH: beacon checkpoints seq %s hash %s..., but the log\'s '
            'entry at that seq %s. THE SEAL IS BROKEN -- possible rewrite of '
            'already-checkpointed history. Run hover_log.py --verify and '
            'read it before touching anything. (exit 1)'
            % (want_seq, str(want_hash)[:16],
               'is absent' if not at else
               'carries hash %s...' % str(at[0].get('hash'))[:16]))
        return 1
    growth = len(entries) - cp.get('count', 0)
    if growth >= stale_after:
        out('STALE (not tampering, and the distinction matters): the seal '
            'still matches at seq %s, but the log has grown %d entries past '
            'it (bound %d, REASONED not measured). Remedy: hover_log.py '
            '--verify, then --publish. (exit 1)'
            % (want_seq, growth, stale_after))
        return 1
    out('PASS: seal intact at seq %s (%s...), log %d entries, %d past the '
        'checkpoint (bound %d, REASONED). This is the passive seal only -- '
        'it does not substitute for hover_log.py --verify.'
        % (want_seq, str(want_hash)[:16], len(entries), growth, stale_after))
    return 0


def publish(log_path=LOG, beacon_path=BEACON, force=False, out=print):
    entries, err = read_log(log_path)
    if entries is None:
        out('REFUSED TO PUBLISH: log unreadable (%s). (exit 2)' % err)
        return 2
    count, seq, tip_hash = tip_of(entries)
    if count is None:
        out('REFUSED TO PUBLISH: tip entry malformed or log empty. (exit 2)')
        return 2
    if os.path.exists(beacon_path) and not force:
        rc = check(log_path, beacon_path, out=lambda *_a: None)
        if rc == 1:
            cp, _ = parse_beacon(beacon_path)
            entries_now, _ = read_log(log_path)
            at = [e for e in entries_now if e.get('seq') == cp.get('seq')]
            broken = not at or at[0].get('hash') != cp.get('hash')
            if broken:
                out('REFUSED TO PUBLISH: the current beacon says MISMATCH -- '
                    'republishing would re-arm a broken seal without a human '
                    'seeing it. Run hover_log.py --verify, read the answer, '
                    'then --publish --force-after-verify. (exit 1)')
                return 1
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    cp = {'count': count, 'seq': seq, 'hash': tip_hash, 'published_at': ts}
    body = (
        '# TIP BEACON -- hover2 self-log passive tamper seal\n\n'
        'This file is a CHECKPOINT CLAIM, published after a clean chain\n'
        'verify, so that a rewrite of already-checkpointed history is\n'
        'visible on casual inspection without running the O(n) verifier.\n'
        'It does NOT substitute for `python hover_log.py --verify`.\n\n'
        'As of %s the log holds **%d entries**; the tip is **seq %d**,\n'
        'chain hash `%s`.\n\n'
        'Check me: `python hover_tip_beacon.py --check`\n\n'
        'CHECKPOINT: %s\n' % (ts, count, seq, tip_hash,
                              json.dumps(cp, sort_keys=True)))
    try:
        with open(beacon_path, 'w', encoding='utf-8') as f:
            f.write(body)
    except OSError as e:
        out('REFUSED TO PUBLISH: could not write beacon (%s). (exit 2)' % e)
        return 2
    out('PUBLISHED: seal at seq %d (%s...), %d entries, %s.'
        % (seq, str(tip_hash)[:16], count, ts))
    return 0


def _selftest():
    fails = []

    def chk(label, cond):
        print(('ok  ' if cond else 'FAIL') + '  ' + label)
        if not cond:
            fails.append(label)

    d = tempfile.mkdtemp(prefix='tipbeacon-selftest-')
    try:
        log = os.path.join(d, 'log.jsonl')
        beacon = os.path.join(d, 'beacon.md')
        with open(log, 'w', encoding='utf-8') as f:
            for i in range(1, 6):
                f.write(json.dumps({'seq': i, 'hash': 'h%d' % i,
                                    'summary': 'x'}) + '\n')
        quiet = lambda *_a: None

        chk('publish on a clean log', publish(log, beacon, out=quiet) == 0)
        chk('check passes right after publish',
            check(log, beacon, out=quiet) == 0)

        # negative control (a): tamper the checkpointed tip entry
        lines = open(log, encoding='utf-8').read().splitlines()
        lines[4] = json.dumps({'seq': 5, 'hash': 'TAMPERED', 'summary': 'x'})
        with open(log, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        chk('tampered checkpointed entry -> MISMATCH (exit 1)',
            check(log, beacon, out=quiet) == 1)
        chk('publish over a broken seal is REFUSED without force',
            publish(log, beacon, out=quiet) == 1)
        chk('publish over a broken seal allowed with --force-after-verify',
            publish(log, beacon, force=True, out=quiet) == 0)

        # negative control (b): grow past the bound without republishing
        with open(log, 'a', encoding='utf-8') as f:
            for i in range(6, 6 + STALE_AFTER):
                f.write(json.dumps({'seq': i, 'hash': 'h%d' % i,
                                    'summary': 'x'}) + '\n')
        chk('growth >= bound -> STALE (exit 1)',
            check(log, beacon, out=quiet) == 1)

        # negative control (c): delete the beacon
        os.remove(beacon)
        chk('beacon absent -> COULD NOT RUN (exit 2)',
            check(log, beacon, out=quiet) == 2)

        chk('unreadable log -> COULD NOT RUN (exit 2)',
            check(os.path.join(d, 'nope.jsonl'), beacon, out=quiet) == 2)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print()
    if fails:
        print('%d SELFTEST FAILURE(S): %s' % (len(fails), fails))
        return 1
    print('ALL SELFTEST CASES PASS')
    return 0


def main(argv):
    if '--selftest' in argv:
        return _selftest()
    if '--publish' in argv:
        return publish(force='--force-after-verify' in argv)
    return check()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
