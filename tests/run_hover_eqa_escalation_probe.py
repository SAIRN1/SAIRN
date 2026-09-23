"""The control on tools/hover_eqa_escalation.py.

    python tests/run_hover_eqa_escalation_probe.py

Exit 0 every arm passes, 1 an arm failed.

THE TOOL'S WHOLE JOB IS TO SAY "OVERDUE" TO SOMEBODY WHO IS NOT HOVER, so the
arm that matters is not that it can say `current` -- a function returning
`current` unconditionally would pass that. Both directions are driven on
synthetic logs, and so is the THIRD state, which is the one an escalation gets
wrong in the dangerous direction: a tool that reports `current` because it could
not find the log has escalated nothing and looks like a pass.

THE FIXTURES ARE SYNTHETIC AND WRITTEN FROM THE RULE. The real logs are read
ONLY by the last two arms, which assert the tool agrees with the live corpus
without asserting what the live corpus says -- a control that depends on
today's hover state goes red for a reason that is not a defect, which this
repo has already recorded once (F16 in run_hover_separation_probe.py).
"""
CONTROLS_FOR = ['tools/hover_eqa_escalation.py']

import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

import hover_eqa_escalation as E          # noqa: E402

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('  ok   %s' % label)
    else:
        FAILS.append(label)
        print('  FAIL %s' % label)
        if detail:
            print('       %s' % str(detail)[:300])


def write_log(rows):
    fd, path = tempfile.mkstemp(suffix='.jsonl', prefix='eqa-')
    os.close(fd)
    with io.open(path, 'w', encoding='utf-8') as fh:
        for r in rows:
            fh.write(json.dumps(r) + '\n')
    return path


def entry(seq, checkpoint=False, process=False):
    return {'seq': seq, 'eqa_checkpoint': checkpoint, 'process_pass': process}


print('\nHOVER EQA ESCALATION -- both directions, and the third state')
TMP = []
try:
    # ── OVERDUE: cadence passes since the last checkpoint ──────────────────
    over = write_log([entry(1, checkpoint=True)]
                     + [entry(n, process=True) for n in (2, 3, 4)])
    TMP.append(over)
    v, d = E.assess(over)
    ok('exactly CADENCE process passes since the checkpoint is OVERDUE',
       v == 'overdue', (v, d))

    # ── CURRENT: one short of the cadence. Without this, an always-overdue
    # rule passes the arm above and the escalation becomes noise nobody reads.
    under = write_log([entry(1, checkpoint=True)]
                      + [entry(n, process=True) for n in (2, 3)])
    TMP.append(under)
    v, d = E.assess(under)
    ok('CONTROL: one short of the cadence is CURRENT, so the rule is not '
       'always-overdue', v == 'current', (v, d))

    # ── AND THE COUNT IS FROM THE LAST CHECKPOINT, not from the start.
    # A rule counting every process pass ever would call this overdue.
    reset = write_log([entry(1, process=True), entry(2, process=True),
                       entry(3, process=True), entry(4, process=True),
                       entry(5, checkpoint=True), entry(6, process=True)])
    TMP.append(reset)
    v, d = E.assess(reset)
    ok('a later checkpoint RESETS the count -- four earlier passes do not make '
       'it overdue', v == 'current', (v, d))

    # ── NEVER VALIDATED is overdue, not unknown: the field exists, and the
    # answer to "has it ever happened" is no.
    never = write_log([entry(n, process=True) for n in (1, 2, 3, 4)])
    TMP.append(never)
    v, d = E.assess(never)
    ok('a log where the field exists and was NEVER set true is OVERDUE, and '
       'says it has never been recorded',
       v == 'overdue' and 'never' in d, (v, d))

    # ── THE THIRD STATE, THE ONE AN ESCALATION GETS WRONG DANGEROUSLY ──────
    nofield = write_log([{'seq': 1, 'summary': 'x'}, {'seq': 2, 'summary': 'y'}])
    TMP.append(nofield)
    v, d = E.assess(nofield)
    ok('a log with NO eqa_checkpoint field is UNKNOWN, never "current"',
       v == 'unknown', (v, d))
    empty = write_log([])
    TMP.append(empty)
    ok('an EMPTY log is UNKNOWN, not current', E.assess(empty)[0] == 'unknown',
       E.assess(empty))
    ok('an ABSENT log is UNKNOWN, not current',
       E.assess(os.path.join(REPO, 'no-such-file.jsonl'))[0] == 'unknown',
       E.assess(os.path.join(REPO, 'no-such-file.jsonl')))
    bad = write_log([])
    io.open(bad, 'w', encoding='utf-8').write('{not json\n')
    TMP.append(bad)
    ok('an UNPARSEABLE log is UNKNOWN and names the reason, rather than being '
       'read as an empty one', E.assess(bad)[0] == 'unknown', E.assess(bad))

    # ── EXIT CODES CARRY THE SAME THREE STATES ────────────────────────────
    # A caller that only reads the exit code must not see a could-not-tell as
    # a pass; this repo's own PR 1.11 is the rule and 2 is reserved for it.
    ok('the three exit codes are distinct, and 2 is reserved for could-not-run',
       len({E.EXIT_CLEAN, E.EXIT_OVERDUE, E.EXIT_COULD_NOT_RUN}) == 3
       and E.EXIT_COULD_NOT_RUN == 2,
       (E.EXIT_CLEAN, E.EXIT_OVERDUE, E.EXIT_COULD_NOT_RUN))

    # ── IT MUST NOT WRITE. The whole boundary argument rests on this.
    src = io.open(os.path.join(REPO, 'tools/hover_eqa_escalation.py'),
                  encoding='utf-8').read()
    ok('the tool has no write path at all -- no write-mode open, no .write(), '
       'no subprocess',
       "'w'" not in src.split('def main(')[0].replace("io.open(path, encoding='utf-8')", '')
       and '.write(' not in src and 'subprocess' not in src,
       [x for x in ('w-mode', '.write(', 'subprocess') if x in src])

    # ── AGAINST THE REAL CORPUS, WITHOUT DEPENDING ON WHAT IT SAYS TODAY ──
    logs = E.hover_logs()
    ok('it finds at least one real hover log on this machine, so the arms '
       'above are not the only thing exercised', len(logs) >= 1, logs)
    if logs:
        verdicts = {E.assess(p)[0] for _s, p in logs}
        ok('every real log returns one of the three declared verdicts and '
           'nothing else', verdicts <= {'current', 'overdue', 'unknown'},
           verdicts)
finally:
    for p in TMP:
        try:
            os.remove(p)
        except OSError:
            pass

print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
