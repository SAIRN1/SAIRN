"""The negative control for tools/accepted_risk_expiry_audit.py.

    python tests/run_accepted_risk_expiry_control.py

WHY IT DID NOT HAVE ONE UNTIL NOW. The tool carries a real internal blind lock
run by `--selftest`, and that is good and is NOT a control: a self-test is
edited in the same commit as its subject, so it is not independent of it.
`tools/checker_control_check.py` counted this checker as having nothing because
nothing under tests/ declared itself its control. It was promoted into the
report-only registry on 2026-09-16, and promotion is when that stops being
acceptable -- a registered check is one people are about to believe.

── THE DISTINCTION THE TOOL EXISTS FOR, AND WHAT A CONTROL MUST PROVE ──────
An accepted risk is a decision to ship a known problem UNTIL something changes.
If the "until" cannot be evaluated the acceptance is permanent, and nobody
decided that. The tool separates two ways that happens, and they need different
fixes, so the control must show it can tell them apart:

    UNCONDITIONAL  no expiry condition was ever stated
    UNINVOKED      a condition names a tool, and nothing runs that tool
    MANUAL         a condition that needs a person, correctly
    RUNNING        a condition, a tool, and something that invokes it

A classifier that collapsed any two of those would still produce a plausible
count. The arms below require all four to be distinguishable, and require the
RUNNING/UNINVOKED split to turn on the INVOKER LIST rather than on the text --
which is the one thing about this tool that is genuinely hard and the one place
a silent regression would read as good news.

── IT WRITES NOTHING ──────────────────────────────────────────────────────
Every arm classifies a string in memory against a synthetic invoker set.
"""
import os
import subprocess
import sys

CONTROLS_FOR = ['tools/accepted_risk_expiry_audit.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import accepted_risk_expiry_audit as E                           # noqa: E402

FAILS = []


def _dirt():
    st = subprocess.run(['git', '-C', REPO, 'status', '--porcelain'],
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace').stdout
    return set(l for l in st.splitlines() if l.strip())


DIRT_BEFORE = _dirt()


def arm(label, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        FAILS.append(label)


# A condition naming a tool that something runs.
RUNNING = ('accepted risk. re-check this when `tools/zz_watcher.py` reports '
           'a change.')
# The same sentence, naming a tool nothing invokes. ONE WORD DIFFERENT.
UNINVOKED = ('accepted risk. re-check this when `tools/zz_orphan.py` reports '
             'a change.')
# A condition a person has to evaluate.
MANUAL = 'accepted risk. re-check this the moment a human looks at the panel.'
# No condition at all.
UNCONDITIONAL = 'accepted risk. we will get to it.'

INVOKERS = {'zz_watcher.py'}


def main():
    # ── 1. ALL FOUR VERDICTS, AND THEY MUST DIFFER ─────────────────────────
    got = {name: E.classify(body, INVOKERS)[0] for name, body in (
        ('RUNNING', RUNNING), ('UNINVOKED', UNINVOKED),
        ('MANUAL', MANUAL), ('UNCONDITIONAL', UNCONDITIONAL))}
    for want, body in (('RUNNING', RUNNING), ('UNINVOKED', UNINVOKED),
                       ('MANUAL', MANUAL), ('UNCONDITIONAL', UNCONDITIONAL)):
        arm('%-13s is classified %s' % (want, want),
            E.classify(body, INVOKERS)[0] == want, E.classify(body, INVOKERS))
    arm('the four produce FOUR DISTINCT verdicts -- a classifier that returns '
        'one answer for everything cannot pass this',
        len(set(got.values())) == 4, got)

    # ── 2. THE SPLIT TURNS ON THE INVOKER LIST, NOT ON THE PROSE ───────────
    # THIS IS THE ARM THAT MATTERS. RUNNING and UNINVOKED differ by which tool
    # is named, and the only thing that can tell them apart is whether anything
    # actually runs it. If this ever stops depending on the invoker set, the
    # tool reports every risk as RUNNING and the report reads as good news.
    arm('the SAME sentence flips RUNNING -> UNINVOKED when its tool leaves the '
        'invoker set',
        E.classify(RUNNING, set())[0] == 'UNINVOKED',
        E.classify(RUNNING, set()))
    arm('...and flips back when it returns, so the verdict tracks the invoker '
        'set in both directions',
        E.classify(UNINVOKED, {'zz_orphan.py'})[0] == 'RUNNING',
        E.classify(UNINVOKED, {'zz_orphan.py'}))

    # ── 3. THE SILENT DIRECTION ────────────────────────────────────────────
    # Everything above asks the tool to SAY something. This requires it to say
    # nothing about a row that is not an accepted risk at all.
    tools_found = E.classify(UNCONDITIONAL, INVOKERS)[1]
    arm('an unconditional acceptance names 0 tools -- there is nothing to '
        'invoke, which is why it is a different finding from UNINVOKED',
        len(tools_found) == 0, tools_found)

    # ── 4. THE SWEEP OVER THE REAL REGISTERS STILL REACHES THEM ────────────
    # A correct classifier wired to a reader that returns nothing reports a
    # platform with no accepted risks, which reads as excellent news.
    rows = E.audit()
    arm('the audit reaches the real accept/defer decisions rather than an '
        'empty list', bool(rows), rows)
    if rows:
        verdicts = set(r.get('verdict') for r in rows)
        arm('...and reports more than one verdict across them, so it is not '
            'answering the same thing for every row', len(verdicts) > 1,
            sorted(verdicts))

    # ── 5. NO DIRT OF ITS OWN ──────────────────────────────────────────────
    added = _dirt() - DIRT_BEFORE
    arm('this probe added nothing newly dirty -- %d path(s) were already '
        'modified before it started and are not its doing' % len(DIRT_BEFORE),
        not added, sorted(added)[:5])

    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
