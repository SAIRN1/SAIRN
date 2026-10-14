#!/usr/bin/env python
# -*- coding: utf-8 -*-
# OWNER: h1
"""hover_report_methodology_check.py -- the two rules H1 b28 item 5 adds to
every digest/report this role writes, enforced mechanically rather than
remembered:

  1. The digest must carry a numeric CONTEXT percent, or say in those words
     that it is NOT MEASURABLE. "ESTIMATE" / "reasoned guess" / a bare
     word with no number and no explicit not-measurable statement is
     REFUSED -- b27's own digest did exactly that ("CONTEXT: ESTIMATE...")
     and this rule exists so that shape cannot repeat silently.
  2. Any chain tip or RFC3161 token number quoted in the report or digest
     must match the REAL, LIVE beacon file and log tip at check time --
     not a number copied from an earlier draft, an earlier batch's digest,
     or typed from memory. This is the mechanical version of the read-back
     discipline item 1 added to hover_tip_beacon.py's own --publish,
     applied to the TEXT a human reads instead of the file a script reads.

REPORT-ONLY. Does not edit the report or digest it checks; a FINDING here
means fix the text and re-run, the same discipline unproven_arm_check.py
and drive_upload_verify.py already hold every other hover/cc deliverable to.

USAGE
  python hover_report_methodology_check.py --digest <path> --report <path>
  python hover_report_methodology_check.py --selftest
"""
import io
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

EXIT_OK = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

CONTEXT_LINE_RE = re.compile(r'^CONTEXT\b.*$', re.MULTILINE | re.IGNORECASE)
NUMERIC_PERCENT_RE = re.compile(r'\b\d{1,3}\s*%|\b\d{1,3}\s*percent\b', re.IGNORECASE)
NOT_MEASURABLE_RE = re.compile(r'not measurable', re.IGNORECASE)

# "chain tip 1385" / "Chain tip: 1385" / "chain tip seq1385" -- the shapes
# this role's own reports have actually used, deliberately permissive on
# punctuation since the goal is to catch a WRONG number, not police prose.
CHAIN_TIP_RE = re.compile(r'chain\s+tip[^0-9]{0,12}(\d{3,})', re.IGNORECASE)
TOKEN_RE = re.compile(r'token[^0-9]{0,12}(\d{3,})', re.IGNORECASE)


def check_context_line(text):
    """Returns (ok, detail). A missing CONTEXT line is its own finding,
    distinct from one present but carrying neither a number nor the
    explicit not-measurable statement -- the caller sees which failed."""
    m = CONTEXT_LINE_RE.search(text)
    if not m:
        return False, 'no line starting with CONTEXT found at all'
    line = m.group(0)
    if NUMERIC_PERCENT_RE.search(line):
        return True, 'numeric percent present: %s' % line.strip()
    if NOT_MEASURABLE_RE.search(line):
        return True, 'explicit not-measurable: %s' % line.strip()
    return False, ('CONTEXT line present but carries neither a numeric '
                    'percent nor the words "not measurable": %r' % line.strip())


def live_beacon_and_tip(beacon_path, log_entries_tip_seq):
    """Both numbers this check holds everything else to. Takes the log's
    real tip seq as an argument rather than re-deriving it, so this file
    has no import-time dependency on hover_log.py's own LOG_PATH wiring --
    the caller (which already resolved that correctly) passes it in."""
    if not os.path.isfile(beacon_path):
        return None, 'no beacon file at %s' % beacon_path
    text = io.open(beacon_path, encoding='utf-8').read()
    m = re.search(r'checkpoint_seq\s*:\s*(\d+)', text)
    if not m:
        return None, 'beacon exists but checkpoint_seq could not be parsed'
    return int(m.group(1)), None


def check_numbers_against_live(text, label, beacon_seq, log_tip_seq):
    """Every chain-tip and token number quoted in `text` must equal the
    REAL current value. Multiple quotes of the same correct number are
    fine (a report says "chain tip 1385" more than once); any quote of a
    DIFFERENT number is a finding, named with the number and what it
    should have been."""
    findings = []
    for m in CHAIN_TIP_RE.finditer(text):
        quoted = int(m.group(1))
        if quoted != log_tip_seq:
            findings.append(
                '%s quotes chain tip %d, but the live log tip is %d right now'
                % (label, quoted, log_tip_seq))
    for m in TOKEN_RE.finditer(text):
        quoted = int(m.group(1))
        if quoted != beacon_seq:
            findings.append(
                '%s quotes token %d, but TIP-BEACON.md on disk reads '
                'checkpoint_seq %d right now' % (label, quoted, beacon_seq))
    return findings


def run_check(digest_path, report_path, beacon_path, log_tip_seq):
    findings = []
    beacon_seq, err = live_beacon_and_tip(beacon_path, log_tip_seq)
    if err:
        print('COULD NOT RUN: %s -- cannot check any number against it.' % err)
        return EXIT_COULD_NOT_RUN

    digest_text = io.open(digest_path, encoding='utf-8').read()
    ok, detail = check_context_line(digest_text)
    if not ok:
        findings.append('CONTEXT rule: %s' % detail)
    else:
        print('  ok   CONTEXT line: %s' % detail)

    findings += check_numbers_against_live(digest_text, 'digest', beacon_seq, log_tip_seq)
    if report_path and os.path.isfile(report_path):
        report_text = io.open(report_path, encoding='utf-8').read()
        findings += check_numbers_against_live(report_text, 'report', beacon_seq, log_tip_seq)

    if findings:
        print('%d FINDING(S):' % len(findings))
        for f in findings:
            print('  ! %s' % f)
        return EXIT_FINDING
    print('  ok   every chain-tip/token number quoted matches the live '
          'beacon (seq %d) and log tip (seq %d) exactly' % (beacon_seq, log_tip_seq))
    return EXIT_OK


def run_fixtures():
    """Fixtures only, never the real beacon/digest. Each case is a real
    negative control: write a scratch digest/report and a scratch beacon,
    and prove the checker actually distinguishes good from bad."""
    ok_count = 0
    total = 0

    def check(label, got, want):
        nonlocal ok_count, total
        total += 1
        if got == want:
            ok_count += 1
            print('  ok   %s' % label)
        else:
            print('  FAIL %s (got %r, want %r)' % (label, got, want))

    scratch = tempfile.mkdtemp(prefix='hover_methodology_fixture_')
    beacon = os.path.join(scratch, 'TIP-BEACON.md')
    io.open(beacon, 'w', encoding='utf-8').write(
        'checkpoint_seq   : 500\ncheckpoint_hash  : deadbeef\n')

    good_digest = os.path.join(scratch, 'good_digest.txt')
    io.open(good_digest, 'w', encoding='utf-8').write(
        'DIGEST x\nSTATUS: ok\nCONTEXT 42%% of window used\n'
        'chain tip 500, token 500\n')
    check('a real numeric CONTEXT percent, correct numbers -> EXIT_OK',
          run_check(good_digest, None, beacon, 500), EXIT_OK)

    nm_digest = os.path.join(scratch, 'nm_digest.txt')
    io.open(nm_digest, 'w', encoding='utf-8').write(
        'DIGEST x\nCONTEXT: not measurable this session\nchain tip 500\n')
    check('explicit "not measurable" -> EXIT_OK, same as a real number',
          run_check(nm_digest, None, beacon, 500), EXIT_OK)

    estimate_digest = os.path.join(scratch, 'estimate_digest.txt')
    io.open(estimate_digest, 'w', encoding='utf-8').write(
        'DIGEST x\nCONTEXT: ESTIMATE, a reasoned guess\nchain tip 500\n')
    check('TEETH: "ESTIMATE" with no number and no "not measurable" -> FINDING '
          '(this is b27\'s own shape and must not pass again)',
          run_check(estimate_digest, None, beacon, 500), EXIT_FINDING)

    missing_digest = os.path.join(scratch, 'missing_digest.txt')
    io.open(missing_digest, 'w', encoding='utf-8').write(
        'DIGEST x\nSTATUS: ok\nchain tip 500\n')
    check('TEETH: no CONTEXT line at all -> FINDING',
          run_check(missing_digest, None, beacon, 500), EXIT_FINDING)

    wrong_tip_digest = os.path.join(scratch, 'wrong_tip.txt')
    io.open(wrong_tip_digest, 'w', encoding='utf-8').write(
        'DIGEST x\nCONTEXT 10%%\nchain tip 499, token 500\n')
    check('TEETH: chain tip quoted one BEHIND the real log tip -> FINDING',
          run_check(wrong_tip_digest, None, beacon, 500), EXIT_FINDING)

    wrong_token_digest = os.path.join(scratch, 'wrong_token.txt')
    io.open(wrong_token_digest, 'w', encoding='utf-8').write(
        'DIGEST x\nCONTEXT 10%%\nchain tip 500, token 1376\n')
    check('TEETH: token quoted that does not match the beacon file on disk '
          '-> FINDING (the exact shape of the b26 incident this batch traced)',
          run_check(wrong_token_digest, None, beacon, 500), EXIT_FINDING)

    no_beacon = os.path.join(scratch, 'no_beacon_here.md')
    check('TEETH: beacon file missing -> COULD_NOT_RUN, never a silent pass',
          run_check(good_digest, None, no_beacon, 500), EXIT_COULD_NOT_RUN)

    print('')
    print('%d/%d fixture checks correct' % (ok_count, total))
    return ok_count == total


def main(argv):
    if '--selftest' in argv:
        return EXIT_OK if run_fixtures() else EXIT_FINDING

    def opt(name):
        return argv[argv.index(name) + 1] if name in argv else None

    digest_path = opt('--digest')
    report_path = opt('--report')
    beacon_path = opt('--beacon')
    tip_seq = opt('--log-tip-seq')
    if not digest_path or not beacon_path or not tip_seq:
        print('usage: hover_report_methodology_check.py --digest PATH '
              '--beacon PATH --log-tip-seq N [--report PATH] | --selftest')
        return EXIT_COULD_NOT_RUN
    try:
        tip_seq = int(tip_seq)
    except ValueError:
        print('COULD NOT RUN: --log-tip-seq must be an integer')
        return EXIT_COULD_NOT_RUN
    return run_check(digest_path, report_path, beacon_path, tip_seq)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
