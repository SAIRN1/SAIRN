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


def add(extra):
    """Run --add against an in-memory register. Returns (exit code, records)."""
    saved = {}
    base = {'started': '2026-09-09', 'note': 'fixture', 'records': []}
    real_load, real_save, real_fmea = D.load, D.save, D.fmea_loop
    D.load = lambda: json.loads(json.dumps(base))
    D.save = lambda d: saved.update(d)
    D.fmea_loop = lambda rec: None          # not this control's subject
    out, real_stdout = io.StringIO(), sys.stdout
    sys.stdout = out
    try:
        argv = ['--add', '--commit', head_sha(), '--app', 'sairnbiz',
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

    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
