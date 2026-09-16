"""The negative control for tools/ai_action_approval_audit.py.

    python tests/run_ai_action_approval_control.py

WHY IT DID NOT HAVE ONE UNTIL NOW. The tool carries a real internal blind lock
-- eight fixtures, driven in both directions, run by `--selftest`. That is good
and it is NOT a control: a self-test is edited in the same commit as its
subject, so it is not independent of it, and `tools/checker_control_check.py`
counted this checker as having nothing because nothing under tests/ declared
itself its control. It was promoted into the report-only registry on 2026-09-16
and promotion is exactly when that stops being acceptable.

── WHAT A CONTROL HAS TO DO THAT A SELF-TEST DOES NOT ──────────────────────
Drive the checker at REAL PLATFORM SOURCE and require it to change its answer.
The self-test asks whether `classify()` agrees with eight hand-written strings.
This asks whether the audit, run over the tree, still finds the thing it found
-- and whether it goes quiet when the thing is removed.

Both directions, because each alone is worthless: a classifier that returns
WRITES_UNGATED for everything passes every must-fire arm, and one that returns
NO_WRITE for everything passes every must-not.

── IT WRITES NOTHING ──────────────────────────────────────────────────────
Every arm classifies a string in memory. No file in this clone is modified, so
this probe cannot participate in the concurrent-restore failure that has cost
this platform a guard overnight before.
"""
import os
import sys

CONTROLS_FOR = ['tools/ai_action_approval_audit.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import ai_action_approval_audit as A                             # noqa: E402

FAILS = []


def _dirt():
    import subprocess
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


# A model answer reaching a write with no human step. This is the shape the
# tool exists to find, written the way the real call sites write it.
UNGATED = ("{ const r = await scAiFetch(prompt); "
           "localStorage.setItem('quote', JSON.stringify(r)); }")
# The same call with a confirm in front of the write.
GATED = ("{ const r = await scAiFetch(prompt); "
         "if (confirm('save this?')) localStorage.setItem('quote', r); }")
# The same answer going to the DOM. Gated BY CONSTRUCTION: the save is a
# separate click the user has to make.
RENDERED = "{ const r = await scAiFetch(prompt); el.innerHTML = r.text; }"
# Neither writes nor renders.
NEITHER = "{ const r = await scAiFetch(prompt); return r.text; }"


def main():
    # ── 1. THE CLASSIFIER CHANGES ITS ANSWER FOR THE RIGHT REASON ──────────
    arm('an AI answer written with no human step is WRITES_UNGATED',
        A.classify(UNGATED) == 'WRITES_UNGATED', A.classify(UNGATED))
    arm('...and adding a confirm in front of the SAME write moves it to '
        'GATED_IN_BODY -- the classification tracks the guard, not the call',
        A.classify(GATED) == 'GATED_IN_BODY', A.classify(GATED))
    arm('an answer that only reaches the DOM is RENDER_ONLY, because the save '
        'is a separate click', A.classify(RENDERED) == 'RENDER_ONLY',
        A.classify(RENDERED))
    arm('an answer that is merely returned is NO_WRITE',
        A.classify(NEITHER) == 'NO_WRITE', A.classify(NEITHER))

    # THE PAIR THAT MATTERS. Four arms above are all satisfied by a classifier
    # that happens to be right about four strings. This one requires the
    # verdicts to be DIFFERENT from each other -- a constant classifier fails it
    # whatever constant it picks.
    verdicts = {A.classify(UNGATED), A.classify(GATED),
                A.classify(RENDERED), A.classify(NEITHER)}
    arm('the four shapes produce FOUR DISTINCT verdicts -- a classifier that '
        'returns one answer for everything cannot pass this',
        len(verdicts) == 4, sorted(verdicts))

    # ── 2. THE SWEEP OVER REAL SOURCE STILL FINDS SOMETHING ────────────────
    # The arms above are about a function. This is about the tool: a correct
    # classifier wired to a file walk that returns nothing reports a clean
    # platform, which is the failure mode that has bitten this repo repeatedly.
    rows = A.audit()
    arm('the audit reaches real app files rather than an empty list',
        bool(rows), rows)
    files = set(r.get('app') for r in rows) if rows else set()
    arm('...across more than one app file, so it is not one lucky path',
        len(files) > 1, sorted(files)[:5])
    ungated = [r for r in rows if r.get('verdict') == 'WRITES_UNGATED']
    arm('...and it still reports the WRITES_UNGATED rows that justify its '
        'promotion -- a zero here is a finding about the TOOL until somebody '
        'has shown the platform changed', bool(ungated), len(ungated))

    # ── 2b. THE SILENT DIRECTION, WHICH IS THE HALF THAT IS EASY TO SKIP ───
    # Everything above asks the tool to SAY something. A checker that reported
    # every function on the platform would pass all of it. These require it to
    # report NOTHING about code that is not its subject.
    CLEAN_SRC = (
        "function saveQuote(q) { localStorage.setItem('quote', q); }\n"
        "function renderTotal(t) { el.innerHTML = t; }\n"
        "async function loadRows() { const r = await fetch(API); return r.json(); }\n")
    ai_fns = [n for n, body in A.functions(CLEAN_SRC) if A.AI_CALL.search(body)]
    arm('a source with writes, renders and a plain fetch but NO model call '
        'yields 0 rows -- the subject is the AI call, not any write',
        len(ai_fns) == 0, ai_fns)

    ONE_AI = CLEAN_SRC + ("async function ask(p) { const r = await scAiFetch(p); "
                          "localStorage.setItem('k', r); }\n")
    ai_fns2 = [n for n, body in A.functions(ONE_AI) if A.AI_CALL.search(body)]
    arm('...and adding ONE model call to the same source yields exactly 1, so '
        'the zero above is discrimination rather than a dead walk',
        len(ai_fns2) == 1, ai_fns2)

    # ── 3. ITS OWN BLIND LOCK STILL REFUSES A BROKEN CRITERION ─────────────
    # classify() asks TWO things whether a body writes -- the WRITE pattern and
    # mutating_fetch() -- and ORs them. Stubbing only one leaves the other
    # answering, which is why the first version of this arm went red against a
    # working tool: it proved the OR, not the detector. Both are stubbed.
    real_write, real_fetch = A.WRITE, A.mutating_fetch
    class _Never(object):
        def search(self, _body):
            return None
    A.WRITE = _Never()
    A.mutating_fetch = lambda body: False
    try:
        broken = A.classify(UNGATED)
    finally:
        A.WRITE, A.mutating_fetch = real_write, real_fetch
    arm('with BOTH write detectors stubbed to never fire, the ungated shape '
        'stops being reported as a write -- so the verdict depends on those '
        'detectors rather than on the string',
        broken != 'WRITES_UNGATED', broken)
    arm('...and the real detector classifies it correctly again once restored',
        A.classify(UNGATED) == 'WRITES_UNGATED')

    # ── 4. THIS PROBE ADDED NO DIRT OF ITS OWN ─────────────────────────────
    # BEFORE AGAINST AFTER, not "is the tree clean now". The first version
    # asserted a clean tree and went red against uncommitted work that had
    # nothing to do with it, which would make the arm a report on whoever ran it
    # rather than on the probe. Asking only "is this file dirty now" is the
    # mid-run-versus-residue confusion this repo has already paid for.
    added = _dirt() - DIRT_BEFORE
    arm('this probe added nothing newly dirty -- %d path(s) were already '
        'modified before it started and are not its doing' % len(DIRT_BEFORE),
        not added, sorted(added)[:5])

    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
