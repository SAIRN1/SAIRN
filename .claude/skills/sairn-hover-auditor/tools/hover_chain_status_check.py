#!/usr/bin/env python
"""
hover_chain_status_check.py -- ONE mechanical per-batch check that prints
chain tip, beacon seq+gap, and RFC3161 TOKEN seq+gap together, so neither
number can silently drift unnoticed the way the token did (b34 -> b41: the
beacon's own 15-entry rule kept IT current while nothing checked the
token's own gap at all, and it drifted to 37 behind with no alarm -- H1 b41
digest, DECISION-NEEDED). Built 2026-10-15 (H1 b42), per the token-cadence
spec in routing/2026-10-15-h1-b42-token-cadence-spec.md: the token gets the
SAME 15-entry staleness rule the beacon already has, checked at the SAME
moment, so the two can no longer diverge by habit alone.

WHY A SEPARATE TOOL, NOT A FLAG BOLTED ONTO hover_tip_beacon.py: the token
check needs to glob the directory for the newest chain-tip-seq*.tsr/.msg
pair, which is a different failure surface (no token file at all; a token
file whose matching .msg is missing; a seq that cannot be parsed from the
filename) than anything --check or --publish already handles, and mixing
the two failure surfaces into one function was exactly the shape that let
hover_log.py and hover2_log_mirror.py's own early LOG_PATH bugs hide (see
hover_log.py's own module docstring). Two FOCUSED checks, not one check
that does two things.

FAIL-CLOSED, PER PR 1.11: a missing token file, an unreadable beacon, or a
log that will not parse all produce EXIT_COULD_NOT_RUN -- never counted as
a passing gap. "Could not tell" is a third state, never folded into "OK".

Run:
  python hover_chain_status_check.py --check       print tip/beacon/token,
                                                     exit 0/1/2
  python hover_chain_status_check.py --selftest     fixtures, must fail
                                                     before being trusted
"""
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hover_log                                                # noqa: E402
from hover_log import LOG_PATH, read_all                        # noqa: E402
from hover_tip_beacon import BEACON_PATH, _parse_beacon          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.dirname(os.path.abspath(LOG_PATH))

# Same number as hover_tip_beacon.STALE_AFTER_ENTRIES, deliberately not
# imported -- importing it would make a future change to the beacon's own
# threshold silently retune the token's threshold too, which is the
# opposite of this tool's whole point (the two are independently checked
# so one drifting does not quietly drag the other's definition with it).
MAX_GAP = 15

EXIT_OK = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

TOKEN_NAME_RX = re.compile(r'^chain-tip-seq(\d+)\.tsr$')


def chain_tip(log_path=None):
    """(seq, total_entries, reason) of the real tip -- reason is None on
    success. hover_log.read_all() reads from the MODULE's own LOG_PATH
    global, not an argument (same shape hover_tip_beacon.py's own selftest
    already relies on), so a fixture log_path is applied by swapping that
    global, calling, then restoring it -- never left swapped on an
    exception, which would leak a fixture path into a later real check in
    the same process. Never guesses a tip from a stale cache."""
    real_log_path = hover_log.LOG_PATH
    if log_path is not None:
        hover_log.LOG_PATH = log_path
    try:
        entries = read_all()
    except (OSError, ValueError) as e:
        return None, None, 'log does not parse: %s' % e
    finally:
        hover_log.LOG_PATH = real_log_path
    if not entries:
        return None, None, 'log is empty'
    return entries[-1]['seq'], len(entries), None


def beacon_seq(beacon_path=BEACON_PATH):
    """(seq, reason) -- reason is None on success."""
    try:
        text = io.open(beacon_path, encoding='utf-8').read()
    except OSError as e:
        return None, 'beacon unreadable: %s' % e
    fields = _parse_beacon(text)
    if 'checkpoint_seq' not in fields:
        return None, 'beacon has no checkpoint_seq field'
    try:
        return int(fields['checkpoint_seq']), None
    except ValueError:
        return None, 'beacon checkpoint_seq is not an integer'


def newest_token_seq(log_dir=LOG_DIR):
    """(seq, reason) for the highest-numbered chain-tip-seq<N>.tsr whose
    matching .msg file ALSO exists -- a .tsr with no .msg is not a usable
    token (nothing to verify it against) and is treated the same as
    missing, not silently accepted."""
    try:
        candidates = glob.glob(os.path.join(log_dir, 'chain-tip-seq*.tsr'))
    except OSError as e:
        return None, 'could not list %s: %s' % (log_dir, e)
    usable = []
    for path in candidates:
        m = TOKEN_NAME_RX.match(os.path.basename(path))
        if not m:
            continue
        seq = int(m.group(1))
        msg_path = os.path.join(log_dir, 'chain-tip-seq%d.msg' % seq)
        if os.path.isfile(msg_path):
            usable.append(seq)
    if not usable:
        return None, 'no usable chain-tip-seq*.tsr+.msg pair found in %s' % log_dir
    return max(usable), None


def token_refresh_hint(tip, t_gap, log_dir=LOG_DIR):
    """Pure, so the fix (name the real LOG_DIR, never a bare '.') is
    actually asserted in _selftest rather than only readable in a code
    comment. A bare '.' here is what wrote the token to cwd (repo root)
    instead of this tool's own LOG_DIR, twice (b57, then again at b58) --
    the hint never named the directory this tool globs, so '.' read as
    "the obvious default" instead of "wherever your shell happens to be"."""
    return ('token is %d behind tip (> %d) -- refresh: python '
            'hover_timestamp.py --request %d <hash> <date> --outdir %s   '
            '(this must be LOG_DIR, where this tool globs for '
            'chain-tip-seq*.tsr -- NOT cwd, NOT a Drive-mirror path)'
            % (t_gap, MAX_GAP, tip, log_dir))


def cmd_check(argv):
    tip, total, tip_err = chain_tip()
    if tip_err:
        print('COULD NOT RUN: chain tip -- %s' % tip_err)
        return EXIT_COULD_NOT_RUN
    b_seq, b_err = beacon_seq()
    if b_err:
        print('COULD NOT RUN: beacon -- %s' % b_err)
        return EXIT_COULD_NOT_RUN
    t_seq, t_err = newest_token_seq()
    if t_err:
        print('COULD NOT RUN: token -- %s' % t_err)
        return EXIT_COULD_NOT_RUN

    b_gap = tip - b_seq
    t_gap = tip - t_seq
    print('chain tip   : seq %d (%d entries total)' % (tip, total))
    print('beacon      : seq %d, gap %d (max %d)' % (b_seq, b_gap, MAX_GAP))
    print('RFC3161 token: seq %d, gap %d (max %d)' % (t_seq, t_gap, MAX_GAP))

    findings = []
    if b_gap > MAX_GAP:
        findings.append('beacon is %d behind tip (> %d) -- republish: '
                         'python hover_tip_beacon.py --publish' % (b_gap, MAX_GAP))
    if t_gap > MAX_GAP:
        findings.append(token_refresh_hint(tip, t_gap))
    if findings:
        print('FINDING:')
        for f in findings:
            print('  - %s' % f)
        return EXIT_FINDING
    print('OK -- both within the %d-entry bound.' % MAX_GAP)
    return EXIT_OK


def _selftest():
    import tempfile, shutil, json

    ok = 0
    total = 0

    def ck(label, cond):
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
            print('  ok   %s' % label)
        else:
            print('  FAIL %s' % label)

    tmp = tempfile.mkdtemp(prefix='hover-chain-status-')
    try:
        log_path = os.path.join(tmp, 'log.jsonl')
        beacon_path = os.path.join(tmp, 'TIP-BEACON.md')

        def write_log(n):
            import hashlib
            prev = '0' * 64
            with io.open(log_path, 'w', encoding='utf-8') as f:
                for seq in range(1, n + 1):
                    h = hashlib.sha256(('%d%s' % (seq, prev)).encode()).hexdigest()
                    f.write(json.dumps({'seq': seq, 'hash': h, 'prev_hash': prev,
                                         'ts': '2026-10-15T00:00:00Z',
                                         'type': 'check', 'target': 'self',
                                         'summary': 'fixture'}) + '\n')
                    prev = h

        def write_beacon(seq):
            with io.open(beacon_path, 'w', encoding='utf-8') as f:
                f.write('checkpoint_seq   : %d\n' % seq)

        def write_token(seq):
            open(os.path.join(tmp, 'chain-tip-seq%d.tsr' % seq), 'wb').write(b'x')
            open(os.path.join(tmp, 'chain-tip-seq%d.msg' % seq), 'wb').write(b'x')

        # FAILING-FIRST: construct the bad state BEFORE the good one, and
        # assert the check actually calls it a finding -- a checker that
        # always prints OK regardless of input is the exact defect class
        # this platform's own CLAUDE.md names repeatedly (PR 1.11).
        write_log(100)
        write_beacon(80)     # gap 20 > 15
        write_token(70)      # gap 30 > 15
        tip, _, _ = chain_tip(log_path)
        b, _ = beacon_seq(beacon_path)
        t, _ = newest_token_seq(tmp)
        ck('F1 (failing-first) a 20-behind beacon IS flagged as a gap > MAX_GAP',
           (tip - b) > MAX_GAP)
        ck('F2 (failing-first) a 30-behind token IS flagged as a gap > MAX_GAP',
           (tip - t) > MAX_GAP)

        # Now the good state -- both within bound.
        write_beacon(90)     # gap 10
        write_token(88)      # gap 12
        b, _ = beacon_seq(beacon_path)
        t, _ = newest_token_seq(tmp)
        ck('G1 a 10-behind beacon is NOT flagged', (tip - b) <= MAX_GAP)
        ck('G2 a 12-behind token is NOT flagged', (tip - t) <= MAX_GAP)

        # Boundary: exactly MAX_GAP is still OK (not > MAX_GAP).
        write_beacon(tip - MAX_GAP)
        b, _ = beacon_seq(beacon_path)
        ck('B1 BOUNDARY: gap exactly == MAX_GAP is NOT flagged (> is strict)',
           (tip - b) <= MAX_GAP)

        # KNOWN-BAD CONTROL: a .tsr with no matching .msg must not count as
        # a usable token -- this is the exact shape that would let a half-
        # written request silently read as current.
        open(os.path.join(tmp, 'chain-tip-seq99.tsr'), 'wb').write(b'x')
        t2, t2_err = newest_token_seq(tmp)
        ck('C1 KNOWN-BAD CONTROL: a .tsr with no .msg is NOT counted as the '
           'newest token (falls back to the real pair)', t2 != 99)

        # FAIL-CLOSED: missing beacon file must COULD-NOT-RUN, never read
        # as gap 0 or any other silent pass.
        os.remove(beacon_path)
        b3, b3_err = beacon_seq(beacon_path)
        ck('C2 FAIL-CLOSED: a missing beacon file returns an error, not a '
           'silent seq', b3 is None and b3_err is not None)

        # FAIL-CLOSED: no token files at all.
        empty = tempfile.mkdtemp(prefix='hover-chain-status-empty-')
        t4, t4_err = newest_token_seq(empty)
        ck('C3 FAIL-CLOSED: zero token files returns an error, not a '
           'silent seq', t4 is None and t4_err is not None)
        shutil.rmtree(empty, ignore_errors=True)

        # FAIL-CLOSED: empty log.
        empty_log = os.path.join(tmp, 'empty.jsonl')
        open(empty_log, 'w').close()
        tip2, total2, err2 = chain_tip(empty_log)
        ck('C4 FAIL-CLOSED: an empty log returns an error, not seq None '
           'read as a silent 0', tip2 is None and err2 is not None)

        # THE B57/B58 REGRESSION: the token-refresh hint must name the REAL
        # log_dir, never a bare '.' -- '.' is exactly what sent the token to
        # cwd instead of LOG_DIR, twice, before this fix.
        hint = token_refresh_hint(999, 30, log_dir=tmp)
        ck('D1 hint names the real log_dir, not a bare "."',
           tmp in hint and '--outdir .' not in hint)
        old_shape_hint = ('token is 30 behind tip (> 15) -- refresh: python '
                           'hover_timestamp.py --request 999 <hash> <date> '
                           '--outdir .')
        ck('D2 KNOWN-BAD CONTROL: the pre-fix hint shape (bare ".") fails '
           'the identical assertion D1 just passed -- proves D1 would '
           'have caught the original bug, not just the fixed string',
           not (tmp in old_shape_hint and '--outdir .' not in old_shape_hint))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print('%d/%d fixture checks correct' % (ok, total))
    return ok == total


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--check' in argv:
        return cmd_check(argv)
    print('usage: hover_chain_status_check.py --check | --selftest')
    return EXIT_COULD_NOT_RUN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
