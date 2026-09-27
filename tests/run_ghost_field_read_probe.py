"""Control pair for tools/ghost_field_read_scan.py.

Run:  python tests/run_ghost_field_read_probe.py

CONTROLS_FOR = ['tools/ghost_field_read_scan.py']

A checker that has never been seen to FAIL is a checker whose behaviour nobody
knows, and its clean line is then evidence for the wrong conclusion. So this
drives BOTH directions on the REAL files:

  plant the defect -> the scan must NAME it, at the right file and field
  restore the file -> the scan must go back to exactly what it said before

── THE FIXTURES ARE SYNTHETIC AND THAT IS STATED RATHER THAN GLOSSED ────────
`tools/unreachable_failure_path_scan.py`'s probe can restore the real pre-fix
`slabSyncOne` body out of git history, because that defect was COMMITTED. Two of
the three defects this scan was built for were caught IN SESSION and never
reached a commit:

  * `out.unmapped_requirements_pending` in api/_lib/compliance-rules.js -- the
    original, caught before the commit; `git log -S` finds it only inside two
    commit MESSAGES describing it.
  * `opts.facility_training_year_start` -- the same file, found by this scan on
    its first run and fixed in the same change.

The third DID ship and IS recoverable, so it is the fixture that matters:

  * `v.actual_start` / `v.actual_end` in sairnsenior.html's
    `rfDeliveredHoursFor()`, which returned 0 for every client for as long as
    the function existed.

MUTATION 1 restores that real pre-fix body. Mutations 2 and 3 re-plant the two
in-session shapes by hand, and are labelled SYNTHETIC in their own output so a
reader is not told a fixture is history when it is not.

── WHAT A PASS HERE DOES AND DOES NOT MEAN ─────────────────────────────────
It means the scan reports the shape it claims to report, and is silent on the
shipped tree. It does NOT mean the scan finds every wrong-field gate -- the
scan's own header names the two members of that family it cannot decide, and no
control can close a gap the tool does not attempt.
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCAN = os.path.join(REPO, 'tools', 'ghost_field_read_scan.py')

EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

passed, failed = 0, 0


def ok(cond, label, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print('  ok   %s' % label)
    else:
        failed += 1
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:400])


def run_scan():
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.run([sys.executable, SCAN], cwd=REPO, env=env,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def read(rel):
    with io.open(os.path.join(REPO, rel), encoding='utf-8', newline='') as fh:
        return fh.read()


def write(rel, text):
    with io.open(os.path.join(REPO, rel), 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)


if not os.path.isfile(SCAN):
    # PR 1.11. The subject is absent, so nothing was tested. Never a pass.
    print('COULD NOT RUN: tools/ghost_field_read_scan.py is not on disk. This '
          'control tested nothing; that is a third state, not a clean run.')
    sys.exit(EXIT_COULD_NOT_RUN)

print('CONTROL PAIR -- tools/ghost_field_read_scan.py\n')

# ── DIRECTION 2 FIRST, so the baseline is taken before anything is touched ──
print('BASELINE -- the shipped tree')
base_rc, base_out = run_scan()
ok(base_rc in (EXIT_CLEAN, EXIT_FINDING),
   'the scan runs and reports a real exit code (%d), not a crash' % base_rc,
   base_out[-400:])
ok('actual_start' not in base_out,
   'the shipped tree does NOT report `actual_start` -- the real defect this '
   'scan was built for is fixed, so the mutation below is re-planting it')
ok('facility_training_year_start' not in base_out,
   '...nor `facility_training_year_start`, the second one it found itself')
# `charge_lines` IS STILL REPORTED AND THAT IS CORRECT, so there is deliberately
# no arm asserting its absence. The third confirmed instance was api/sd-data.js
# reconciling a derived invoice against `data.charge_lines`, a key NO write path
# on this platform stores. The fix made the impossible comparison a named third
# state instead of "every line added"; it did NOT make the key exist. So the
# capability check still cannot pass, the scan still says so, and an arm
# demanding silence here would have to be satisfied by hiding a true finding --
# which is the reword-past-the-matcher move (PR 4.3) pointed at a checker.
# It clears when somebody writes `charge_lines` on the invoice, which is the
# real follow-up and is a separate change.
ok('charge_lines' in base_out,
   'CONTROL, the other direction: the scan DOES still report `charge_lines` -- '
   'the key genuinely does not exist yet, so a clean line here would mean the '
   'scan had been silenced rather than satisfied')
baseline_findings = base_out.count('\n  ! ')
print('       baseline findings: %d' % baseline_findings)

MUTATIONS = [
    # (label, file, old, new, the field the scan must name, real_or_synthetic)
    ('MUTATION 1 -- the REAL pre-fix rfDeliveredHoursFor body, restored',
     'sairnsenior.html',
     '    var vh=visitHours(v);\n    if(isFinite(vh)&&vh>0)h+=vh;',
     '    if(!v.actual_start||!v.actual_end)return;\n'
     '    var ms=new Date(v.actual_end).getTime()-new Date(v.actual_start).getTime();\n'
     '    if(isFinite(ms)&&ms>0)h+=ms/3600000;',
     'actual_start', 'REAL (shipped, then fixed 2026-09-27)'),
    ('MUTATION 2 -- the facility_training_year fall-through, re-planted',
     'api/_lib/compliance-rules.js',
     "    const start = String(trainingYearStart || '');",
     "    if (opts_never_set_anywhere.ghost_window_anchor) { return out; }\n"
     "    const start = String(trainingYearStart || '');",
     'ghost_window_anchor', 'SYNTHETIC (the real one never reached a commit)'),
]

for label, rel, old, new, field, provenance in MUTATIONS:
    print('\n%s\n       provenance: %s' % (label, provenance))
    original = read(rel)
    if old not in original:
        # The anchor is gone. A probe that silently could not apply its own
        # mutation reports a pass it never earned -- PR 1.3.
        ok(False, 'ANCHOR NOT FOUND in %s -- this mutation did NOT run, so '
                  'nothing below it was tested' % rel, old[:120])
        continue
    ok(original.count(old) == 1,
       'the anchor in %s is UNIQUE, so the mutation lands where intended' % rel,
       'count=%d' % original.count(old))
    write(rel, original.replace(old, new, 1))
    try:
        rc, out = run_scan()
        ok(rc == EXIT_FINDING,
           'with the defect planted the scan exits 1 FINDING (got %d)' % rc,
           out[-400:])
        ok(('`' + field) in out or ('.' + field) in out,
           'and it NAMES `%s` -- not merely a count going up' % field,
           '\n'.join(l for l in out.split('\n') if field in l)[:400] or out[-300:])
        ok(rel in out,
           'and it names the FILE it is in (%s)' % rel,
           '\n'.join(l for l in out.split('\n') if rel in l)[:300])
    finally:
        write(rel, original)
        ok(read(rel) == original,
           'and %s is restored BYTE-IDENTICAL afterwards' % rel)

# ── DIRECTION 2: back to silence on the same question ──────────────────────
print('\nAFTER -- the tree is restored')
after_rc, after_out = run_scan()
ok('actual_start' not in after_out and 'ghost_window_anchor' not in after_out,
   'the scan is silent again on both planted fields, so the reports above were '
   'caused by the mutations and not by something else that changed')
ok(after_out.count('\n  ! ') == baseline_findings,
   'and the finding count is back to the baseline (%d)' % baseline_findings,
   'now %d' % after_out.count('\n  ! '))

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
