"""tools/criticality_tier_check.py must DENY, not just agree.

The register is clean today, and a gate whose findings are clean has by
construction never refused anything -- so nobody knows whether it can.

REWRITTEN 2026-09-10 when the register moved from app-level to RESOURCE-level
tiering. The old arms anchored on app rows (`sairnvet.html` being Tier B, then
`stonedesk-catalog.html` being UNTIERED) and BOTH failed loudly as those rows
changed during the day, which is the probe working -- but the rows themselves
are gone now, so the arms are rebuilt against the structure rather than moved
again.

EVERY ARM MUTATES A COPY IN A THROWAWAY WORKTREE, never this clone. Deliberate:
this repo established that a probe which edits tracked files is
indistinguishable from residue when it dies, and the register is a file a reader
would trust on sight.

Run: python tests/run_criticality_tier_probe.py
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
REL_DOC = os.path.join('docs', 'CRITICALITY-TIERS.md')
REL_TOOL = os.path.join('tools', 'criticality_tier_check.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run(wt):
    r = subprocess.run([sys.executable, os.path.join(wt, REL_TOOL)],
                       cwd=wt, capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('criticality tiers -- the checker must refuse a register that has stopped '
      'describing the platform\n')

wt = tempfile.mkdtemp(prefix='sairn-crit-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True)
if add.returncode != 0:
    print('SKIPPED: could not create a worktree -- nothing was verified.')
    print(add.stderr.strip()[:300])
    sys.exit(3)

DOC = os.path.join(wt, REL_DOC)
try:
    ORIGINAL = io.open(DOC, encoding='utf-8', newline='').read()

    # ── ARM 1: THE CONTROL, FIRST, so a refusal later cannot be confused with
    #    a checker that refuses everything.
    rc, out = run(wt)
    check('the shipped register PASSES', rc == 0, out[-400:])
    check('...and it reports what it counted', 'RESOURCES_REGISTERED:' in out)
    check('...and it does NOT claim the tiers are correct',
          'It does not say the tier is right' in out,
          'a checker that implies more reach than it has is worse than none')

    def mutate(new_text, label, marker):
        io.open(DOC, 'w', encoding='utf-8', newline='').write(new_text)
        rc2, out2 = run(wt)
        check(label, rc2 == 1 and marker in out2,
              'exit=%s marker_present=%s' % (rc2, marker in out2))
        io.open(DOC, 'w', encoding='utf-8', newline='').write(ORIGINAL)

    def one_row(needle):
        hits = [l for l in ORIGINAL.split('\n') if l.startswith(needle)]
        assert len(hits) == 1, ('fixture invalid: %r matches %d rows, not 1 -- widen '
                                'the anchor rather than letting replace() pick'
                                % (needle, len(hits)))
        return hits[0]

    # ── ARM 2: A REGISTERED RESOURCE WITH NO ROW ───────────────────────────
    # The one that matters most: a resource is added and nobody states its
    # worst case. It must not pass by not being mentioned.
    inv = one_row('| `sd_invoices` |')
    mutate(ORIGINAL.replace(inv + '\n', '', 1),
           'a registered resource with NO ROW is refused', 'NO TIER')

    # ── ARM 3: A ROW FOR SOMETHING THAT IS NOT A RESOURCE ──────────────────
    # The unit of the table is the registry. A row for an unregistered key
    # would make the counts mean two things at once.
    mutate(ORIGINAL.replace(inv, '| `zz_not_a_resource` | **A** | nothing | nothing |\n'
                            + inv, 1),
           'a row for something not in any registry is refused', 'NOT A RESOURCE')

    # ── ARM 4: A TIER OUTSIDE THE VOCABULARY ───────────────────────────────
    # One scheme, taken from the SOUP register. A row inventing HIGH or P1 is
    # how a second scheme starts.
    mutate(ORIGINAL.replace(inv, inv.replace('| **A** |', '| **CRITICAL** |', 1), 1),
           'a tier outside A/B/C is refused', 'BAD TIER')

    # ── ARM 5: A TIER A ROW WITH NOTHING TO CHECK IT AGAINST ───────────────
    # THE LINE THAT KEEPS THE A TIER HONEST. B and C are classified by the
    # stated rule; A is hand-verified. That difference has to be enforceable
    # rather than promised, or A degrades into rule-guessing.
    parts = inv.rsplit('|', 2)
    stripped = parts[0] + '|  |'
    mutate(ORIGINAL.replace(inv, stripped, 1),
           'a Tier A row with an EMPTY evidence cell is refused', 'NO EVIDENCE')

    # ── ARM 6: A ROLLUP THAT DISAGREES WITH ITS OWN DETAIL ─────────────────
    roll = one_row('| `stonedesk` |')
    mutate(ORIGINAL.replace(roll, roll.replace('| **10** |', '| **3** |', 1), 1),
           'a rollup count that contradicts the rows is refused', 'COUNT')

    # ── ARM 7: A HALF-TIERED APP ───────────────────────────────────────────
    # A resource row under an app whose rollup says NOT YET RE-TIERED. Without
    # this, a partly-done app reads as an untouched one.
    mutate(ORIGINAL.replace(roll, roll.replace('**RE-TIERED**', '**NOT YET RE-TIERED**', 1), 1),
           'resource rows under a NOT-YET-RE-TIERED app are refused', 'HALF DONE')

    # ── ARM 8: AN APP NOBODY HAS EVEN SAID "NOT YET" ABOUT ─────────────────
    # Caught a real gap in the register's own first draft: sairncash had a
    # registry and no rollup line.
    cash = one_row('| `sairncash` |')
    mutate(ORIGINAL.replace(cash + '\n', '', 1),
           'an app with a registry and NO ROLLUP LINE is refused', 'NO ROLLUP')

    check('the register was restored byte for byte after every arm',
          io.open(DOC, encoding='utf-8', newline='').read() == ORIGINAL)
finally:
    subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', wt],
                   capture_output=True, text=True)
    shutil.rmtree(wt, ignore_errors=True)

here = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', REL_DOC],
                      capture_output=True, text=True).stdout.strip()
check('this clone\'s own register is untouched', here == '', here)

print('\n%s  run_criticality_tier_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
