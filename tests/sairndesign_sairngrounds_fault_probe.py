"""The two new suites must DENY, not merely agree.

tests/sairndesign_server_backup.js and tests/sairngrounds_server_backup.js are
the last two of the three first-suites docs/MASTER-PLAN.md called for. Both are
green on the shipped tree, and a suite whose findings are clean has by
construction never refused anything -- so this plants real defects and proves
each one is caught.

ONE PROBE, TWO APPS, because the mechanism is identical and a second file would
be a second place to keep the worktree discipline correct.

THE ARM THAT MATTERS MOST IN EACH APP is the Tier A by-name arm: it removes a
money resource from the registry, the client AND the schema together, so every
PAIRWISE assertion still passes -- the three lists then agree perfectly with
each other. Only the by-name section, which reads Tier A out of
docs/CRITICALITY-TIERS.md, can see it. That is the test the pairwise checks
cannot replace, and the probe exists partly to prove it is not decorative.

EVERY ARM MUTATES A COPY IN A THROWAWAY WORKTREE, never this clone, and every
anchor is COUNTED rather than merely found -- both lessons this repo learned the
expensive way on 2026-09-10.

Run: python tests/sairndesign_sairngrounds_fault_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()

DSN_SUITE = os.path.join('tests', 'sairndesign_server_backup.js')
GRD_SUITE = os.path.join('tests', 'sairngrounds_server_backup.js')
DSN_REG = os.path.join('api', '_resources', 'sairndesign.js')
GRD_REG = os.path.join('api', '_resources', 'sairngrounds.js')
DSN_SQL = os.path.join('sql', 'sairndesign_data_schema.sql')
GRD_SQL = os.path.join('sql', 'sairngrounds_data_schema.sql')
# msb_licenses is in the PHASE 2 file, not the first one. The count guard
# returned 0 for it and that is how this was found rather than assumed.
GRD_SQL2 = os.path.join('sql', 'sairngrounds_data_schema_phase2.sql')
DSN_HTML = 'sairndesign.html'
GRD_HTML = 'sairngrounds.html'

TOUCHED = [DSN_REG, GRD_REG, DSN_SQL, GRD_SQL, GRD_SQL2, DSN_HTML, GRD_HTML]

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


print('sairndesign + sairngrounds -- both new suites must refuse a tree that has '
      'stopped agreeing\n')

wt = tempfile.mkdtemp(prefix='sairn-dg-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    ORIG = {}
    for rel in TOUCHED:
        ORIG[rel] = io.open(os.path.join(wt, rel), encoding='utf-8', newline='').read()

    def run(suite):
        r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                           capture_output=True, text=True)
        return r.returncode, (r.stdout or '') + (r.stderr or '')

    def write(rel, text):
        io.open(os.path.join(wt, rel), 'w', encoding='utf-8', newline='').write(text)

    def restore():
        for rel, txt in ORIG.items():
            write(rel, txt)

    def once(rel, needle):
        n = ORIG[rel].count(needle)
        assert n == 1, ('fixture invalid: %r matches %d places in %s, not 1 -- widen the '
                        'anchor rather than letting replace() pick' % (needle, n, rel))
        return needle

    def all_n(rel, needle, expect):
        """Replace EVERY occurrence, with the count asserted first.

        The rule from the platform anchor sweep is "know how many you are
        hitting", not "it must be exactly one". A rename that has to stay
        consistent across a file legitimately touches many places; what is
        forbidden is not knowing the number. The single-anchor guard caught
        this on the first run -- `'sdn_invoices'` appears eight times in
        sairndesign.html -- which is the guard working on new code again.
        """
        n = ORIG[rel].count(needle)
        assert n == expect, ('fixture invalid: %r matches %d places in %s, expected %d'
                             % (needle, n, rel, expect))
        return needle

    def arm(suite, label, marker, edits):
        try:
            for edit in edits:
                rel, old, new = edit[0], edit[1], edit[2]
                count = edit[3] if len(edit) > 3 else None
                if count is None:
                    write(rel, ORIG[rel].replace(once(rel, old), new, 1))
                else:
                    write(rel, ORIG[rel].replace(all_n(rel, old, count), new))
            rc, out = run(suite)
            check(label, rc == 1 and marker in out,
                  'exit=%s marker_present=%s' % (rc, marker in out))
        finally:
            restore()

    # ── CONTROLS FIRST, so a refusal later is not a checker refusing everything
    for suite, name in ((DSN_SUITE, 'sairndesign'), (GRD_SUITE, 'sairngrounds')):
        rc, out = run(suite)
        check('%s: the shipped tree PASSES' % name, rc == 0, out[-300:])

    # ── SAIRNDESIGN ────────────────────────────────────────────────────────
    arm(DSN_SUITE, 'sairndesign: a registered resource whose table is gone is caught',
        'registered with no table',
        [(DSN_SQL, 'create table if not exists public.sdn_samples (',
          'create table if not exists public.zz_gone_samples (')])

    arm(DSN_SUITE, 'sairndesign: a table nothing can write is caught',
        'tables nothing can write',
        [(DSN_REG, "    'sdn_moodboards',\n", '')])

    # THE ONE PAIRWISE CANNOT SEE: sdn_invoices removed from registry, client and
    # schema together. All three then agree with each other perfectly.
    arm(DSN_SUITE, 'sairndesign: dropping the Tier A INVOICES from all three sides is '
                   'still caught',
        'sdn_invoices is not registered',
        [(DSN_REG, "'sdn_invoices',", "'zz_renamed_invoices',"),
         (DSN_SQL, 'public.sdn_invoices', 'public.zz_renamed_invoices', 6),
         (DSN_HTML, "'sdn_invoices'", "'zz_renamed_invoices'", 8)])

    # ── SAIRNGROUNDS ───────────────────────────────────────────────────────
    arm(GRD_SUITE, 'sairngrounds: an alias pointing at a table that is gone is caught',
        'aliases pointing at nothing',
        [(GRD_SQL, 'create table if not exists public.grd_jobs (',
          'create table if not exists public.zz_gone_jobs (')])

    arm(GRD_SUITE, 'sairngrounds: an alias kept alive by nothing is caught',
        'no longer registered',
        [(GRD_REG, "    'properties',\n", '')])

    arm(GRD_SUITE, 'sairngrounds: dropping the Tier A LICENSES from all three sides is '
                   'still caught',
        'msb_licenses is not registered',
        [(GRD_REG, "'msb_licenses',", "'zz_renamed_licenses',"),
         (GRD_SQL2, 'public.msb_licenses', 'public.zz_renamed_licenses', 6),
         (GRD_HTML, "'msb_licenses'", "'zz_renamed_licenses'", 5)])

    ok = all(io.open(os.path.join(wt, rel), encoding='utf-8', newline='').read() == txt
             for rel, txt in ORIG.items())
    check('all seven files restored byte for byte after every arm', ok)
finally:
    subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                   capture_output=True, text=True)
    shutil.rmtree(wt, ignore_errors=True)

dirty = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--'] + TOUCHED,
                       capture_output=True, text=True).stdout.strip()
check('this clone\'s own files are untouched', dirty == '', dirty)

print('\n%s  sairndesign_sairngrounds_fault_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
