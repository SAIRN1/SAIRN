"""tests/sairnfreedom_server_backup.js must DENY, not merely agree.

SAIRNfreedom had no dedicated suite AND no fault probe -- docs/MASTER-PLAN.md
measured it as the worst of the three verticals with neither. The suite is the
first half; this is the second, because a suite whose findings are clean has by
construction never refused anything and nobody knows whether it can.

EVERY ARM MUTATES A COPY IN A THROWAWAY WORKTREE, never this clone. This repo
established on 2026-09-10 that a probe which edits tracked files is
indistinguishable from residue when it dies, and it established it the hard way:
a stranded PROBE commit reached origin twice in two days, once deleting a field
that had already made SAIRNlaw compute Florida five days late.

EVERY ANCHOR IS COUNTED, NOT MERELY FOUND, per the same day's platform sweep. An
anchor is a string match against code somebody else keeps editing, so going
AMBIGUOUS is how it ages -- and a probe that plants in whichever place came
first is asserting something about a line nobody chose.

Run: python tests/sairnfreedom_fault_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
SUITE = os.path.join('tests', 'sairnfreedom_server_backup.js')
HTML = os.path.join('sairnfreedom.html')
REG = os.path.join('api', '_resources', 'sairnfreedom.js')
SCHEMA = os.path.join('sql', 'sairnfreedom_data_schema.sql')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run(wt):
    r = subprocess.run(['node', os.path.join(wt, SUITE)], cwd=wt,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('sairnfreedom -- the suite must refuse a registry, client or schema that '
      'has stopped agreeing\n')

wt = tempfile.mkdtemp(prefix='sairn-sf-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

try:
    ORIG = {}
    for rel in (HTML, REG, SCHEMA):
        ORIG[rel] = io.open(os.path.join(wt, rel), encoding='utf-8', newline='').read()

    def write(rel, text):
        io.open(os.path.join(wt, rel), 'w', encoding='utf-8', newline='').write(text)

    def restore():
        for rel, txt in ORIG.items():
            write(rel, txt)

    def once(rel, needle):
        n = ORIG[rel].count(needle)
        assert n == 1, ('fixture invalid: %r matches %d places in %s, not 1 -- widen '
                        'the anchor rather than letting replace() pick' % (needle, n, rel))
        return needle

    def arm(label, marker, edits):
        try:
            for rel, old, new in edits:
                write(rel, ORIG[rel].replace(once(rel, old), new, 1))
            rc, out = run(wt)
            check(label, rc == 1 and marker in out,
                  'exit=%s marker_present=%s' % (rc, marker in out))
        finally:
            restore()

    # ── ARM 0: THE CONTROL, FIRST ──────────────────────────────────────────
    rc, out = run(wt)
    check('the shipped tree PASSES', rc == 0, out[-400:])
    check('...and it ran the ORC section rather than skipping it',
          'charitable disbursements' in out, out[-300:])

    # ── ARM 1: a registered resource the client stops pushing ──────────────
    arm('a registered resource the client no longer pushes is caught',
        'registered and never sent',
        [(HTML, "'sf_inventory_counts','sf_ledger','sf_members'",
          "'sf_inventory_counts','sf_members'")])

    # ── ARM 2: a table with nothing to write it ────────────────────────────
    arm('a table nothing can write is caught',
        'tables nothing can write',
        [(REG, "    'sf_vendors',\n", '')])

    # ── ARM 3: THE ONE A PAIRWISE COUNT CANNOT SEE ─────────────────────────
    # Remove charitable disbursements from ALL THREE sides. Every pairwise
    # assertion still passes -- the three lists agree perfectly with each other.
    # Only the by-name section catches it, which is the whole reason that
    # section exists and is worth more than the four arms above combined:
    # sf_disbursements is the ORC 2915 reportable side of a fraternal post's
    # gaming, and the registry's own header names it as the reason this app got
    # a server at all.
    arm('dropping CHARITABLE DISBURSEMENTS from all three sides is still caught',
        'sf_disbursements is not registered',
        [(REG, "    'sf_disbursements',\n", ''),
         (HTML, "'sf_ceremonial_items','sf_disbursements',",
          "'sf_ceremonial_items',"),
         (SCHEMA, 'create table if not exists public.sf_disbursements (',
          'create table if not exists public.zz_removed_disb (')])

    # ── ARM 4: the backup hook goes silent again ───────────────────────────
    arm('inlining the backup logger back into st() is caught',
        'no longer delegates',
        [(HTML, 'catch(e2){ sfBackupHookFailed(k, e2); }',
          'catch(e2){ try{ console.error(e2); }catch(_e){} }')])

    # ── ARM 5: the derived sync map becomes a hand-kept second list ─────────
    arm('hand-listing SF_SYNCED_ON instead of deriving it is caught',
        'no longer derived',
        [(HTML, 'SF_SYNCED.forEach(function(k){ SF_SYNCED_ON[k]=true; });',
          "SF_SYNCED_ON['sf_ledger']=true;")])

    # ── ARM 6: a second, undeclared sd-data caller ──────────────────────────
    arm('a second direct sd-data caller is caught',
        'more than one place calls sd-data',
        [(HTML, 'return fetch(SF_DATA_API, {',
          'if(0){ fetch(SF_DATA_API, {}); }\n  return fetch(SF_DATA_API, {')])

    ok = all(io.open(os.path.join(wt, rel), encoding='utf-8', newline='').read() == txt
             for rel, txt in ORIG.items())
    check('all three files restored byte for byte after every arm', ok)
finally:
    subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                   capture_output=True, text=True)
    shutil.rmtree(wt, ignore_errors=True)

dirty = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--',
                        HTML, REG, SCHEMA], capture_output=True, text=True).stdout.strip()
check('this clone\'s own files are untouched', dirty == '', dirty)

print('\n%s  sairnfreedom_fault_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
