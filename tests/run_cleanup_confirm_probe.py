"""Control for tools/cleanup_confirm_check.py -- driven on both sides.

    python tests/run_cleanup_confirm_probe.py

A checker that has only ever returned clean is unproven. This one is worse than
unproven if it is only driven one way: its FIRST crude version called 17 of 26
real files non-compliant, and hand-reading three showed two were false
positives. Every arm below is one of the shapes that produced a wrong answer,
kept as a fixture so it cannot produce one again.

FIXTURES ARE SYNTHETIC. Pinning arms to real cleanup files would rot the moment
one is edited -- the failure `tests/reachability/live_mode_probe.py` records
against its own first version. Nothing here reads or writes the repo.
"""
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = os.path.join(REPO, 'tools', 'cleanup_confirm_check.py')
R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def verdict(sql):
    """Write a fixture, run the checker on it, return (rc, output)."""
    d = tempfile.mkdtemp(prefix='cleanupchk-')
    p = os.path.join(d, 'zz_probe_cleanup.sql')
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(sql)
    try:
        r = subprocess.run([sys.executable, TOOL, p], cwd=REPO,
                           capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    finally:
        os.remove(p)
        os.rmdir(d)


# ── A. the defect this exists to catch ─────────────────────────────────────
rc, out = verdict(
    "-- removes the round-trip test rows\n"
    "delete from public.sdn_clients  where client_id  = 'X-1';\n"
    "delete from public.sdn_vendors  where vendor_id  = 'X-2';\n")
check('A1 live deletes with no confirm are a GAP', rc, 1)
check('A2 and every unconfirmed table is named',
      'sdn_clients' in out and 'sdn_vendors' in out, True)
check('A3 and the missing expectation is called out',
      'no expected answer stated' in out, True)

# ── B. the compliant shape passes ──────────────────────────────────────────
rc, out = verdict(
    "delete from public.sdn_clients where client_id = 'X-1';\n"
    "-- select count(*) from public.sdn_clients where client_id = 'X-1';  -- expect 0\n")
check('B1 a per-statement confirm passes', rc, 0)
check('B2 and is reported OK', 'OK  ' in out, True)

# ── C. the confirm may live inside a comment ───────────────────────────────
# Every compliant file in this repo ships its confirm commented out: it is an
# instruction to paste after the destructive half has run, not a statement to
# execute. A checker that only counted live SQL would fail all of them.
rc, out = verdict(
    "delete from public.leg_cases where case_id = 'X';\n"
    "-- Confirm afterwards (expect 0):\n"
    "--   select count(*) from public.leg_cases where case_id = 'X';\n")
check('C1 a commented confirm counts', rc, 0)

# ── D. select and count(*) on DIFFERENT LINES ──────────────────────────────
# The real false positive from sairnlaw_remove_probe_rule_2026-08-25.sql: a
# grouped count whose `select` and `count(*)` sit on separate lines. A
# single-line regex reported a compliant file as having no confirm at all.
rc, out = verdict(
    "delete from public.law_deadline_rules where rule_id = 'zz';\n"
    "-- Expected exactly, and nothing else: 13 rows.\n"
    "-- select jurisdiction,\n"
    "--        count(*) as rules\n"
    "-- from public.law_deadline_rules\n"
    "-- group by 1;\n")
check('D1 a multi-line confirm counts', rc, 0)

# ── E. an expectation stated mid-sentence ──────────────────────────────────
# sairnroofing_verify_3b_cleanup.sql says "Expect 0 here anyway" in prose. The
# first matcher demanded the word immediately after `--` and rejected it.
rc, out = verdict(
    "delete from public.rf_jobs where job_id = 'X';\n"
    "-- The id is attribution, not a foreign key. Expect 0 here anyway, since\n"
    "-- the verify jobs are deleted above:\n"
    "--   select count(*) from public.rf_jobs where job_id = 'X';\n")
check('E1 an expectation in prose counts', rc, 0)

# ── F. a commented statement is an OFFER, not an action ────────────────────
# sairnroofing_verify_damage_cleanup_2026-08-26.sql was flagged for a delete
# that is commented out under "SEPARATE, AND NOT THIS RUN'S DEBRIS" -- another
# session's row, deliberately left. Its two LIVE deletes are both confirmed.
rc, out = verdict(
    "delete from public.rf_claims where claim_id like 'X-%';\n"
    "-- Confirm afterwards (expect 0):\n"
    "--   select count(*) from public.rf_claims where claim_id like 'X-%';\n"
    "-- SEPARATE, and not this run's debris -- another session's credential:\n"
    "--   delete from public.sairnroofing_employee_auth where employee_id = 'y';\n")
check('F1 a commented delete does not make a confirmed file a GAP', rc, 0)
check('F2 and it is still counted as offered', '1 live, 1 offered' in out, True)

# ── G. a file whose statements are ALL commented is a menu ─────────────────
rc, out = verdict(
    "-- Run only the statements you actually want:\n"
    "-- delete from public.bld_bids where bid_id = 'X';\n"
    "-- delete from public.bld_tna_assessments where subject_employee_id = 'y';\n")
check('G1 a menu-only file is not a GAP', rc, 0)
check('G2 and is labelled MENU', 'MENU' in out, True)

# ── H. verification through the live ENDPOINT is accepted ──────────────────
# CLAUDE.md PREFERS this over a re-select: it proves the APP can see the
# change, which a select as owner does not -- sairncash_waitlist re-selected
# fine as owner the whole time it was 502ing for every real user.
rc, out = verdict(
    "delete from public.sairncode_employee_auth where employee_id = 'gate-test';\n"
    "-- Verify after running (expect 401 INVALID_CREDENTIALS -- the row is gone):\n"
    "--   curl -s -X POST https://sairn.vercel.app/api/sc-auth \\\n"
    "--     -d '{\"action\":\"login\",\"employee_id\":\"gate-test\"}'\n")
check('H1 an API confirm passes', rc, 0)
check('H2 and says so rather than claiming a SQL read-back',
      'verified through the live endpoint' in out, True)

# ── I. a file with nothing destructive has nothing to confirm ──────────────
rc, out = verdict("-- select count(*) from public.rf_jobs;  -- expect 3\n")
check('I1 a read-only file is not reported at all', rc, 0)
check('I2 and is not counted as a file with destructive statements',
      '0 file(s) with destructive statements' in out, True)

# ── J. `update` only counts when it reaches a SET ──────────────────────────
# "update" is an ordinary English word and these files are mostly prose.
rc, out = verdict("-- This is an update to the earlier note about public.rf_jobs.\n"
                  "-- Nothing here changes any row.\n")
check('J1 the word "update" in prose is not a destructive statement',
      '0 file(s) with destructive statements' in out, True)

for k in sorted(R):
    ok, actual, expected = R[k]
    print('  %-6s %s' % ('ok' if ok else 'FAIL', k))
    if not ok:
        print('         expected %r, got %r' % (expected, actual))
bad = [k for k in R if not R[k][0]]
print()
print('cleanup-confirm: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
