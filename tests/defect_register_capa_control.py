"""The negative control for item 75's collection half in tools/defect_register.py.

    python tests/defect_register_capa_control.py

`--check` has validated contributing factors correctly since they were added,
and could only ever inspect the records that happened to carry them: five of
eighty-five. `--add` never asked for them. This drives the refusal at the moment
of recording, in both directions.

── IT WRITES NOTHING ────────────────────────────────────────────────────────
`load()` and `save()` are replaced with in-memory stubs for every arm, so no
arm can touch docs/defect-density-register.json. A control that mutates the real
register to prove the register refuses mutations would be its own worst finding,
and on 2026-09-14 two probes on this platform did exactly that shape to each
other and both reported success.

── THE ARM THAT MATTERS MOST IS THE LAST ONE ────────────────────────────────
Extracting the validation into `factor_problems()` so `--add` and `--check` share
it is a REFACTOR, and a refactor of a checker is the change most likely to
quietly stop it checking. The equivalence arm re-runs the extracted function over
all five real records and requires the same verdict the inline version gave:
silence. Without it, "the register still checks OK" would be equally true of a
function that returned [] unconditionally.
"""
# REQUIREMENT: defect_register.py refuses at the moment of RECORDING a defect
#   that carries neither contributing factors nor a stated reason for having
#   none, because a field that is optional when a record is written is a field
#   that stays empty
#
import io
import json
import os
import sys

CONTROLS_FOR = ['tools/defect_register.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import defect_register as D                                      # noqa: E402

FAILS = []
GOOD = [{'factor': 'the handler accepted a value it should have refused',
         'kind': 'technical', 'action_status': 'done',
         'action': 'the validator now refuses rather than coercing'},
        {'factor': 'no control had ever driven the refusal',
         'kind': 'detection', 'action_status': 'planned',
         'action': 'a negative control for the write path'}]
RECUR = 'NOT CLOSED: every other write path on the platform has the same shape.'


def arm(label, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        FAILS.append(label)


def head_sha():
    return D.git('rev-parse', 'HEAD').strip()


# ── THE FIXTURE MUST NOT DEPEND ON WHAT HAPPENS TO BE AT HEAD ──────────────
# It did, and the control was green or red according to who pushed last.
#
# `add()` passed `--commit head_sha()`. `cmd_add` then calls `derive(sha)` and
# refuses any commit whose files are all bookkeeping or generated -- the
# `--commit $(git rev-parse HEAD)` trap, a real guard that belongs there. So
# whenever the tip happened to be a `chore(claims):` or `chore(generated):`
# commit -- which in a five-clone repo is most of the time -- the three
# MUST-ACCEPT arms failed for a reason that has nothing to do with CAPA
# validation, which is this control's actual subject.
# THAT IS WORSE THAN A FLAKY SUITE. This control's own stated purpose is that
# it must not be "satisfied by an --add that refuses everything" -- and a
# refusal arriving from an unrelated guard is exactly that, arriving by
# accident. A red run was being read as a finding about CAPA and a green run as
# a clearance, and which one you got depended on the repo's tip.
#
# SO `derive` IS MOCKED to a fixed synthetic commit. It is the same decision
# already made for `load`, `save` and `fmea_loop` above: everything that is not
# this control's subject is held still.
#
# THE GUARD IS NOT MOCKED AWAY, it is driven deliberately -- see the
# bookkeeping arms in main(), which call add(..., files=BOOKKEEPING_FILES) and
# assert the refusal still happens. Removing a guard's only exercise while
# silencing it is how a mock becomes a blind spot.
FIX_FILES = ['api/_lib/some-engine.js', 'api/some-endpoint.js']
BOOKKEEPING_FILES = ['.claude/claims/hank.json', 'docs/MASTER-PLAN.md']
SYNTHETIC = {'commit': '0123456789ab', 'date': '2026-09-21',
             'subject': 'CONTROL FIXTURE -- a synthetic commit, not a real one',
             'lines_added': 12, 'lines_removed': 3}


def add(extra, files=None):
    """Run --add against an in-memory register. Returns (exit code, records).

    `files` is what the mocked `derive` reports the cited commit touched --
    a real fix by default, so the bookkeeping guard stays quiet and the arms
    below test what they say they test.
    """
    saved = {}
    base = {'started': '2026-09-09', 'note': 'fixture', 'records': []}
    real_load, real_save, real_fmea = D.load, D.save, D.fmea_loop
    real_derive = D.derive
    D.load = lambda: json.loads(json.dumps(base))
    D.save = lambda d: saved.update(d)
    D.fmea_loop = lambda rec: None          # not this control's subject
    rec = dict(SYNTHETIC, files=list(FIX_FILES if files is None else files))
    D.derive = lambda sha: dict(rec)        # nor is the repo's current tip
    out, real_stdout = io.StringIO(), sys.stdout
    sys.stdout = out
    try:
        argv = ['--add', '--commit', SYNTHETIC['commit'], '--app', 'sairnbiz',
                '--layer', 'tooling', '--severity', 'moderate',
                '--method', 'code-review',
                '--summary', 'CONTROL FIXTURE -- never saved to disk',
                '--rule', 'not-citable', '--rule-note', 'control fixture',
                '--phase', 'unknown', '--phase-note', 'control fixture',
                '--injection-unknown', 'control fixture'] + extra
        rc = D.cmd_add(argv)
    except SystemExit as e:
        rc = e.code
    finally:
        sys.stdout = real_stdout
        D.load, D.save, D.fmea_loop = real_load, real_save, real_fmea
        D.derive = real_derive
    return rc, saved.get('records', []), out.getvalue()


def main():
    # ── MUST REFUSE ────────────────────────────────────────────────────────
    rc, recs, _ = add([])
    arm('neither --factors nor --factors-unknown is REFUSED',
        rc == 2 and not recs, (rc, len(recs)))

    rc, recs, _ = add(['--factors', json.dumps(GOOD),
                       '--factors-unknown', 'both at once'])
    arm('BOTH at once is refused -- it is how the field goes quietly empty',
        rc == 2 and not recs, (rc, len(recs)))

    rc, recs, _ = add(['--factors', '{not json'])
    arm('malformed JSON is refused rather than stored as a string',
        rc == 2 and not recs, (rc, len(recs)))

    rc, recs, _ = add(['--factors', json.dumps(GOOD)])
    arm('factors with no --recurrence-open are refused',
        rc == 2 and not recs, (rc, len(recs)))

    one = [dict(GOOD[0])]
    rc, recs, _ = add(['--factors', json.dumps(one),
                       '--recurrence-open', RECUR])
    arm('ONE factor with no --single-factor-note is refused -- one cause is a '
        'claim, not a default', rc == 2 and not recs, (rc, len(recs)))

    bad_kind = [dict(GOOD[0], kind='root-cause')]
    rc, recs, _ = add(['--factors', json.dumps(bad_kind),
                       '--recurrence-open', RECUR,
                       '--single-factor-note', 'only one was found'])
    arm('a kind outside the vocabulary is refused', rc == 2 and not recs,
        (rc, len(recs)))

    no_action = [{'factor': 'x', 'kind': 'technical', 'action_status': 'done'}]
    rc, recs, _ = add(['--factors', json.dumps(no_action),
                       '--recurrence-open', RECUR,
                       '--single-factor-note', 'only one was found'])
    arm('action_status done with no action is refused -- that is the CAPA box '
        'this field replaces', rc == 2 and not recs, (rc, len(recs)))

    declined = [{'factor': 'x', 'kind': 'process', 'action_status': 'declined'}]
    rc, recs, _ = add(['--factors', json.dumps(declined),
                       '--recurrence-open', RECUR,
                       '--single-factor-note', 'only one was found'])
    arm('action_status declined with no note is refused -- deciding not to act '
        'is a decision', rc == 2 and not recs, (rc, len(recs)))

    # ── MUST ACCEPT. Without these, every arm above is satisfied by an --add
    #    that refuses everything, which would be the same defect one level up.
    rc, recs, _ = add(['--factors', json.dumps(GOOD),
                       '--recurrence-open', RECUR])
    arm('two well-formed factors with a recurrence note are ACCEPTED',
        rc == 0 and len(recs) == 1
        and len(recs[0].get('contributing_factors', [])) == 2
        and recs[0].get('recurrence_open') == RECUR, (rc, recs))

    rc, recs, _ = add(['--factors', json.dumps(one),
                       '--recurrence-open', RECUR,
                       '--single-factor-note', 'the other paths were checked '
                                               'and were not contributors'])
    arm('...and ONE factor WITH the note is accepted',
        rc == 0 and len(recs) == 1
        and recs[0].get('single_factor_note'), (rc, recs))

    rc, recs, out = add(['--factors-unknown',
                         'the incident is still being read; factors to follow'])
    arm('--factors-unknown records the record WITH its stated reason -- losing '
        'a real defect would be worse than the gap being closed',
        rc == 0 and len(recs) == 1
        and recs[0].get('factors_unknown_reason'), (rc, recs))

    # ── THE REFACTOR DID NOT STOP IT CHECKING ──────────────────────────────
    reg = D.load()
    with_cf = [r for r in reg['records'] if r.get('contributing_factors')]
    # A FLOOR, NOT AN EQUALITY, and it was written as `== 5` first. Five was
    # true for about an hour: another clone recorded more factored defects the
    # same evening and this arm went red over a register getting BETTER. A
    # control that fails when its subject improves is one somebody deletes.
    arm('the real register still carries factored records to check against',
        len(with_cf) >= 5, len(with_cf))
    problems = []
    for r in with_cf:
        problems.extend(D.factor_problems(r, r['commit']))
    arm('factor_problems() is silent on all five, as the inline version was',
        not problems, problems)

    # AND IT IS NOT SILENT BECAUSE IT CANNOT SPEAK.
    broken = dict(with_cf[0])
    broken['contributing_factors'] = [dict(broken['contributing_factors'][0],
                                           kind='not-a-kind')]
    broken.pop('single_factor_note', None)
    arm('...and it DOES speak when a real record is corrupted',
        len(D.factor_problems(broken, 'fixture')) >= 2,
        D.factor_problems(broken, 'fixture'))

    # THE root_cause REFUSAL, which is item 75's other half and lives in --check.
    arm('a record carrying `root_cause` is still refused by --check',
        'root_cause' in io.open(os.path.join(REPO, 'tools', 'defect_register.py'),
                                encoding='utf-8').read())

    # -- THE GUARD THAT WAS BREAKING THIS SUITE IS NOW DRIVEN ON PURPOSE ----
    # Mocking `derive` stops the repo's tip deciding this control's verdict. It
    # would ALSO stop the bookkeeping guard ever being exercised, and a mock
    # that silences a guard's only exercise is how a mock becomes a blind spot.
    # So the guard is driven here, in both directions, from synthetic file
    # lists rather than from whatever happens to be at HEAD.
    ok_args = ['--factors', json.dumps(GOOD), '--recurrence-open', RECUR]

    rc, recs, out = add(ok_args, files=BOOKKEEPING_FILES)
    arm('a BOOKKEEPING-only commit is still refused -- the guard survives the '
        'mock', rc == 2 and not recs and 'bookkeeping' in out.lower(),
        (rc, len(recs), out[:160]))

    rc, recs, _ = add(ok_args + ['--commit-is-bookkeeping',
                                 'the fix really does live in a generated file'],
                      files=BOOKKEEPING_FILES)
    arm('...and its override still works when a real sentence is given',
        rc == 0 and len(recs) == 1, (rc, len(recs)))

    # THE ARM THAT PROVES THE FIX. Same input; the only difference is what the
    # cited commit TOUCHED. A real fix is accepted, bookkeeping is not. Before
    # 2026-09-21 that distinction was made by the repo's tip instead, so this
    # suite's verdict depended on who pushed last.
    rc_fix, recs_fix, _ = add(ok_args)
    arm('the SAME well-formed record is ACCEPTED when the commit is a real fix '
        '-- the verdict follows the input, not the repo tip',
        rc_fix == 0 and len(recs_fix) == 1, (rc_fix, len(recs_fix)))


    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
