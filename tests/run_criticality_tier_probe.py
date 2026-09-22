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
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['criticality_tier_check.py']

import io
import re
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
REL_DOC = os.path.join('docs', 'CRITICALITY-TIERS.md')
REL_TOOL = os.path.join('tools', 'criticality_tier_check.py')

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run(wt):
    r = subprocess.run([sys.executable, os.path.join(wt, REL_TOOL)],
                       cwd=wt, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('criticality tiers -- the checker must refuse a register that has stopped '
      'describing the platform\n')

wt = tempfile.mkdtemp(prefix='sairn-crit-')
shutil.rmtree(wt, ignore_errors=True)
add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
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
    # ── THE HARDCODED 10 WENT STALE AND THIS ARM WENT RED (2026-09-22) ────
    # It read `roll.replace('| **10** |', '| **3** |')`. StoneDesk's Tier A
    # count was 10 when that was written; sd_exec_msgs and sd_negotiated_prices
    # were re-tiered afterwards and it is 12. The replace matched NOTHING, the
    # mutated document was byte-identical to the original, the checker passed
    # -- correctly, it had nothing to complain about -- and the arm reported
    # FAIL because the marker never appeared.
    #
    # RED IS THE SAFE DIRECTION AND IT IS STILL WRONG: the arm was failing for
    # a reason that has nothing to do with the property it guards, so a reader
    # learns to expect one red arm here, which is how a probe stops being read
    # at all. And it is the SECOND thing in this file to go stale by somebody
    # else correctly re-tiering a row -- the count is a fact about the table,
    # so it must be DERIVED from the table rather than typed beside it.
    #
    # The mutation now reads whatever the A count is and writes a different
    # number, and it ASSERTS the edit landed. A mutation that plants nothing
    # must be a loud failure about the ANCHOR, never a quiet one about the
    # subject.
    roll = one_row('| `stonedesk` |')
    m6 = re.search(r'\| \*\*(\d+)\*\* \|', roll)
    assert m6, ('fixture invalid: the stonedesk rollup row carries no '
                '| **N** | A-count cell -- the row shape changed and this arm '
                'is not testing what it says it tests: %r' % roll)
    a_count = int(m6.group(1))
    wrong = a_count + 7           # any number the rows cannot support
    rolled = roll.replace(m6.group(0), '| **%d** |' % wrong, 1)
    assert rolled != roll, 'the rollup mutation did not land'
    mutate(ORIGINAL.replace(roll, rolled, 1),
           'a rollup count that contradicts the rows is refused (A=%d -> %d)'
           % (a_count, wrong), 'COUNT')

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
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
    shutil.rmtree(wt, ignore_errors=True)

here = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', REL_DOC],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
check('this clone\'s own register is untouched', here == '', here)


# -- THE READER ITSELF, DRIVEN DIRECTLY. Added 2026-09-14. -----------------
# Every arm above runs the whole tool in a worktree, which is right for "does
# it deny". It cannot see WHICH NAMES the tool decided were registered, and
# that is exactly where the defect was: apps_with_registries() matched any line
# of the shape 'name', anywhere in the file, so it scraped the notSynced array
# -- the list of keys that DELIBERATELY never reach a server.
#
# And the answer depended on COMMENT PLACEMENT. sairnvet declares three
# local-only keys together; two carry trailing comments and were invisible, the
# third has its comment on the lines above and was scraped. The checker then
# reported "sairnvet/sv_audit_backed is registered and has no row" -- a finding
# produced entirely by where somebody put a //.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import criticality_tier_check as C            # noqa: E402

_names, _err = C.resource_names(
    os.path.join(REPO, 'api', '_resources', 'sairnvet.js'))
check('the reader parses sairnvet at all', _err is None and _names, str(_err))
for _k in ('sv_audit_backed', 'sv_settings', 'sv_examrooms_turnover'):
    check('notSynced key %-22s is NOT a registered resource' % _k,
          _names is not None and _k not in _names,
          'notSynced is the list of things that never reach a server; counting '
          'one is the opposite of what registered means')
check('THE PAIRED POSITIVE: real resources ARE still counted, so the fix is not '
      'just a narrower reader that sees nothing',
      _names is not None and 'sv_controlled' in _names and len(_names) > 30,
      '%s names' % (len(_names) if _names else 0))

# ALL THREE FILE SHAPES PARSE. The first version of the narrowed reader knew
# only the multi-line array and reported the other two as a changed file shape,
# which was loud and wrong.
for _app, _why in (('sairnvet', 'multi-line array'),
                   ('sairncash', 'resources: [] -- explicitly empty, a real answer'),
                   ('sairncode', 'resources: RESOURCES -- a reference to a const')):
    _n, _e = C.resource_names(
        os.path.join(REPO, 'api', '_resources', _app + '.js'))
    check('%-11s parses (%s)' % (_app, _why), _e is None, str(_e))

# AND AN UNPARSEABLE FILE IS AN ERROR, NOT AN EMPTY APP -- returning zero names
# would make every resource in it vanish from the check and the app would read
# CLEAN, which is the fail-open direction from a completeness checker.
_n, _e = C.resource_names(os.path.join(REPO, 'tools', 'criticality_tier_check.py'))
check('a file with no resources array is an ERROR, not an app with no resources',
      _n is None and _e, 'returned %r / %r' % (_n, _e))

print('\n%s  run_criticality_tier_probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
