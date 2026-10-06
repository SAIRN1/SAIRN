"""
A check whose ONLY TRIGGER CANNOT FIRE FOR THE THING IT CHECKS.

REPORT-ONLY. Derives candidates, decides nothing, repairs nothing.

── WHAT THIS CLASS IS, AND THE INSTANCE THAT PRODUCED IT (2026-09-26) ───────
`tools/register_freshness_check.py` was written 2026-09-24 to catch a register
citation that no longer points at what it says. It was correct, it was
registered, and it never once ran because of an edit to either document it
checks. Its only wiring was `report_only_checks.REGISTRY`, and that sweep's
hook returns 0 immediately unless the Bash command was a `git push`:

    if payload and not pushes(cmd):
        return 0                      # report_only_checks.hook_main()

So the checker ran after a PUSH. The two documents it reads --
docs/CRITICALITY-TIERS.md and docs/tier-a-reviews.json -- are changed with
Write and Edit. Editing a citation-bearing document triggered nothing at all,
and a session that edited one and did not push ran it zero times.

THIS IS NOT THE SAME DEFECT AS A CHECK THAT STOPPED CHECKING (PR 1.1) and it
is not a check that never worked. Every arm was right. The finding is a wiring
fact: the trigger and the subject are in different worlds, and nothing about
either one says so. A check like that reports a clean result -- eventually,
somewhere else, attributed to somebody else's push.

── WHY THIS IS AN ENUMERATION AND NOT A VERDICT ────────────────────────────
Whether a document named in a checker's own `catches` text is its SUBJECT or
merely a SOURCE it reads is a judgement, and this tool cannot make it.
`flaky_checker_quarantine.py` names docs/SAIRN-PROCESS-RULES.md because it
CITES a rule; `index_duplicate_check.py` names docs/SAIRN-OPEN-WORK-INDEX.md
because that document IS what it checks. Both look identical to a regex.

So this derives the CANDIDATE SET from the authors' own declarations and leaves
the judgement where the judgement is -- the third instance of the split
`sairn_app_map_check.py` and `tooling_inventory.py` already make in this repo:
judgement human, enumeration derived. A tool that auto-classified would fill
the column with guesses.

── WHAT IT CANNOT SEE, PRINTED ON EVERY RUN ────────────────────────────────
See `BLIND_SPOTS` below. It is printed, not documented here and forgotten.

CLI:
    python tools/invocation_path_scan.py
    python tools/invocation_path_scan.py --json
    python tools/invocation_path_scan.py --selftest
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = os.path.join(REPO, '.claude', 'settings.json')
GATE = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')

# ── MODULE LEVEL AND GUARDED, BOTH, MOVED 2026-10-06 (cc) ───────────────────
# `report_only_checks.REGISTRY` refuses at import on an undocumented entry and
# says it does so "at IMPORT rather than in a suite". MEASURED 2026-10-06: that
# held for only 7 of its 14 importers, and this was one of the seven.
#
# GUARDED RATHER THAN BARE, because this tool already answers an unreadable
# registry with `COULD NOT RUN -- these inputs could not be read` and exit 2.
# Hoisting the import unguarded would replace that third state with a
# traceback. The import is now EVALUATED at import time and its outcome
# CARRIED, so the guarantee and the diagnosis both hold.
#
# AND THE CAUSE IS KEPT, which it was not before: the old `except Exception:
# return None` discarded the exception, so the report said only WHICH input
# could not be read and never WHY. Driven: a `RegistryIncomplete` naming one
# entry and one missing field was reduced to the bare words
# `report_only_checks.REGISTRY`. Same defect class as
# `checker_selftest_check.py`'s false disjunction, one notch milder -- that one
# asserted something false, this one asserted too little.
#
# THE sys.path INSERT MOVES WITH IT. The old one sat inside the function, so
# hoisting the import alone would work as a script and fail on import.
sys.path.insert(0, os.path.join(REPO, 'tools'))
try:
    import report_only_checks as _ROC                              # noqa: E402
    _ROC_WHY = None
except Exception as _e:                                            # noqa: BLE001
    _ROC, _ROC_WHY = None, '%s: %s' % (type(_e).__name__, _e)

# A document a human authors with Write/Edit. The extension is the signal: a
# .md or .json under docs/ is not produced by running a command, with the
# explicit exception of the generated ones, which are handled separately
# because their trigger story is genuinely different.
DOC_SUBJECT = re.compile(r'docs[/\\][A-Za-z0-9_.-]+\.(?:md|json)')

# GENERATED documents have a DIFFERENT trigger story and must not be counted
# with the hand-authored ones: an edit to them is not how they change, and the
# push gate already refuses a push that leaves one stale. Listed rather than
# derived because "is this document generated" is a fact about its generator,
# and the three generators name their own outputs in `catches` -- which is the
# same string this tool reads, so deriving it would be circular.
GENERATED_DOCS = (
    'docs/MASTER-PLAN.md',
    'docs/traceability-matrix.md',
    'docs/TOOLING-INVENTORY.md',
)

BLIND_SPOTS = [
    'A document named in `catches` may be a SOURCE the checker reads rather '
    'than its SUBJECT. This cannot tell those apart and does not try -- every '
    'row below needs a read before it is called a finding.',
    'A checker whose subject is CODE rather than a document is out of scope '
    'here entirely. Write/Edit fires for code too, so the same class exists '
    'there, and this tool would report every one of them as fine.',
    'Only checkers this repo REGISTERS are enumerated: report_only_checks.'
    'REGISTRY, the .claude/settings.json hooks, and the push gate. A check '
    'that exists as a bare script nobody wired is invisible here and is a '
    'different finding -- run `--json` and compare against `git ls-files '
    'tools/` if you want that set.',
    'It reads WIRING, never behaviour. A checker wired to Write|Edit that '
    'returns early for the file it was handed is reported as covered.',
    'The push-gate list comes from name occurrences in sairn_push_gate_hook.py, '
    'so a tool named only in a comment there reads as invoked.',
]


def read(path):
    try:
        return io.open(path, encoding='utf-8', errors='replace').read()
    except Exception:
        return None


def settings_triggers():
    """{tool_name: set(trigger labels)} from .claude/settings.json.

    Returns None if the file cannot be read or parsed -- a could-not-check.
    Treating an unreadable settings file as "no hooks" would report every
    registered checker as un-triggered, which is a loud wrong answer rather
    than a quiet one, but it is still a wrong answer and this refuses instead.
    """
    raw = read(SETTINGS)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    out = {}
    for event, blocks in (data.get('hooks') or {}).items():
        for block in blocks or []:
            matcher = block.get('matcher') or ''
            if 'Write' in matcher or 'Edit' in matcher:
                label = 'EDIT'
            elif 'Bash' in matcher:
                label = 'bash'
            elif event == 'SessionStart':
                label = 'session-start'
            else:
                label = event.lower()
            for h in block.get('hooks') or []:
                for m in re.finditer(r'tools/([A-Za-z0-9_]+\.py)',
                                     h.get('command') or ''):
                    out.setdefault(m.group(1), set()).add(label)
    # ── ONE HOP OF INDIRECTION, AND THIS TOOL'S FIRST RUN IS WHY ───────────
    # A checker is often wired through a WRAPPER rather than named in
    # settings.json itself. The first run of this scan reported
    # register_freshness_check.py as push-only AFTER citation_drift_hook.py had
    # been written specifically to run it on an edit -- because it looked for
    # the checker's own name in the hook command and the wrapper's name is what
    # is there. A scan that cannot see its own repo's fix reports a finding
    # that has already been closed, which is the same false-positive shape it
    # exists to warn about.
    #
    # ONE HOP ONLY, deliberately. Following arbitrary depth would eventually
    # decide that everything importing anything is triggered by everything, and
    # the answer would stop meaning "this runs when that file is edited".
    for wrapper, labels in list(out.items()):
        if 'EDIT' not in labels:
            continue
        wsrc = read(os.path.join(REPO, 'tools', wrapper))
        if not wsrc:
            continue
        for m in re.finditer(r"([A-Za-z0-9_]+\.py)", wsrc):
            name = m.group(1)
            if name == wrapper:
                continue
            out.setdefault(name, set()).add('EDIT(via %s)' % wrapper)
    return out


def registry_entries():
    """The report-only registry, or None on a could-not-check.

    The import moved to module level 2026-10-06 and is guarded there -- see the
    note beside it. `_ROC_WHY` carries the reason, which this function's own
    caller prints beside the input name.
    """
    if _ROC is None:
        return None
    try:
        return list(_ROC.REGISTRY)
    except Exception:                                          # noqa: BLE001
        return None


def sweep_is_push_only():
    """Is the report-only sweep's hook gated on `git push`?

    READ FROM THE SOURCE, not assumed, because this is the load-bearing fact
    of the whole report: if that gate is ever removed, every 'push' trigger
    below becomes 'bash' and most of the findings evaporate. A tool that
    hard-coded the answer would keep reporting the old one.
    """
    src = read(os.path.join(REPO, 'tools', 'report_only_checks.py'))
    if src is None:
        return None
    hook = src[src.find('def hook_main('):]
    if not hook:
        return None
    return bool(re.search(r'if payload and not pushes\(cmd\)\s*:\s*\n\s*return 0',
                          hook))


def gate_tools():
    src = read(GATE)
    if src is None:
        return None
    return set(re.findall(r'([A-Za-z0-9_]+\.py)', src))


def classify(entries, s_trig, gate, push_only):
    """One row per registered checker. No verdicts, only derived fields."""
    rows = []
    for e in entries:
        tool = e['tool']
        catches = e.get('catches', '') or ''
        docs = sorted(set(DOC_SUBJECT.findall(catches).__iter__()
                          if False else
                          [d.replace('\\', '/') for d in DOC_SUBJECT.findall(catches)]))
        triggers = set(s_trig.get(tool, set()))
        # REGISTRY MEMBERSHIP IS A PUSH TRIGGER, NOT A BASH ONE. That is the
        # whole point of reading hook_main() above rather than assuming.
        triggers.add('push' if push_only else 'bash(any)')
        if tool in gate:
            triggers.add('push-gate')
        hand = [d for d in docs if d not in GENERATED_DOCS]
        gen = [d for d in docs if d in GENERATED_DOCS]
        rows.append({
            'tool': tool,
            'declared_doc_subjects': docs,
            'hand_authored': hand,
            'generated': gen,
            'triggers': sorted(triggers),
            # ANY label beginning EDIT counts, including `EDIT(via wrapper)`.
            # An exact `'EDIT' in triggers` test reported a checker wired
            # through a wrapper as uncovered, which was this tool's own first
            # false positive.
            'has_edit_trigger': any(t.startswith('EDIT') for t in triggers),
        })
    return rows


def selftest():
    out, bad = [], 0

    def arm(name, ok, detail=''):
        nonlocal bad
        out.append('  %s %s%s' % ('ok  ' if ok else 'FAIL', name,
                                  '' if ok else '\n       ' + detail))
        if not ok:
            bad += 1

    # ── FIXTURES, NOT THE REAL REGISTRY (item 1). These keep meaning the same
    #    thing after the real findings are fixed. A selftest that asserted
    #    "register_freshness_check is flagged" would go red the moment that was
    #    corrected -- which is today.
    fx = [
        {'tool': 'flagged.py',
         'catches': 'a stale row in docs/SOME-REGISTER.md'},
        {'tool': 'covered.py',
         'catches': 'a stale row in docs/SOME-REGISTER.md'},
        {'tool': 'codesubject.py',
         'catches': 'a handler that writes without a confirm step'},
        {'tool': 'generated.py',
         'catches': 'docs/MASTER-PLAN.md no longer matching its sources'},
    ]
    s_trig = {'covered.py': {'EDIT'}}
    rows = {r['tool']: r for r in classify(fx, s_trig, set(), True)}

    arm('a doc-subject checker with NO edit trigger is reported as such',
        not rows['flagged.py']['has_edit_trigger']
        and rows['flagged.py']['hand_authored'] == ['docs/SOME-REGISTER.md'],
        'flagged.py came back as %r' % rows['flagged.py'])
    arm('the SAME checker wired to Write|Edit is NOT',
        rows['covered.py']['has_edit_trigger'],
        'covered.py came back as %r -- the settings.json matcher parse is not '
        'reaching it, which would report every wired checker as a finding'
        % rows['covered.py'])
    arm('a checker whose subject is CODE declares no document subject',
        rows['codesubject.py']['declared_doc_subjects'] == [],
        'codesubject.py came back as %r' % rows['codesubject.py'])
    arm('a GENERATED document is separated from a hand-authored one',
        rows['generated.py']['generated'] == ['docs/MASTER-PLAN.md']
        and rows['generated.py']['hand_authored'] == [],
        'generated.py came back as %r. Folding a generated document in with '
        'the hand-authored ones overstates the finding: an edit is not how it '
        'changes, and the push gate already refuses a stale one.'
        % rows['generated.py'])
    arm('registry membership is reported as a PUSH trigger when the sweep is '
        'push-gated',
        'push' in rows['flagged.py']['triggers'],
        'triggers came back %r -- if this says bash(any) the whole report is '
        'understating how narrow the wiring is'
        % rows['flagged.py']['triggers'])

    # THE SAME FIXTURES WITH THE SWEEP NOT PUSH-GATED. Without this, the
    # push_only parameter could be ignored entirely and every arm above passes.
    rows2 = {r['tool']: r for r in classify(fx, s_trig, set(), False)}
    arm('CONTROL -- push_only=False really changes the trigger label',
        'bash(any)' in rows2['flagged.py']['triggers']
        and 'push' not in rows2['flagged.py']['triggers'],
        'the push_only argument is not being used: %r'
        % rows2['flagged.py']['triggers'])

    # THE LIVE READ OF THE LOAD-BEARING FACT. Not a fixture -- if this stops
    # being true the report is wrong, so it is checked rather than assumed.
    po = sweep_is_push_only()
    arm('the sweep\'s push gate is still readable in report_only_checks.py',
        po is not None,
        'hook_main() could not be read, so whether the report-only sweep is '
        'push-gated is UNKNOWN. That is the fact every trigger label below '
        'rests on and it must not be guessed.')
    return out, bad


def main(argv):
    if '--selftest' in argv:
        out, bad = selftest()
        print('INVOCATION PATH SCAN -- selftest')
        for line in out:
            print(line)
        print('  %s' % ('ALL ARMS PASS' if not bad else '%d ARM(S) FAILED' % bad))
        return 1 if bad else 0

    entries = registry_entries()
    s_trig = settings_triggers()
    gate = gate_tools()
    push_only = sweep_is_push_only()
    # THE REASON TRAVELS WITH THE INPUT NAME, added 2026-10-06 (cc). Naming
    # the input that could not be read is necessary and was not sufficient:
    # a `RegistryIncomplete` that names one entry and one missing field was
    # being reduced to the eleven characters `...REGISTRY`, and the reader had
    # to go and reproduce it to learn what this process already knew.
    missing = [(n, w) for n, v, w in
               (('report_only_checks.REGISTRY', entries, _ROC_WHY),
                ('.claude/settings.json', s_trig, None),
                ('tools/sairn_push_gate_hook.py', gate, None),
                ('report_only_checks.hook_main()', push_only, None))
               if v is None]
    if missing:
        # PR 1.11. Every one of these is an input the classification depends
        # on; without any of them the answer is not "nothing found".
        print('COULD NOT RUN -- these inputs could not be read, so NOTHING was '
              'classified:', file=sys.stderr)
        for m, why in missing:
            print('    %s%s' % (m, ('\n        cause: %s' % why) if why
                                else ''), file=sys.stderr)
        return 2

    rows = classify(entries, s_trig, gate, push_only)
    flagged = [r for r in rows if r['hand_authored'] and not r['has_edit_trigger']]
    covered = [r for r in rows if r['hand_authored'] and r['has_edit_trigger']]
    gen_only = [r for r in rows if r['generated'] and not r['hand_authored']]
    no_doc = [r for r in rows if not r['declared_doc_subjects']]

    if '--json' in argv:
        print(json.dumps({'push_only_sweep': push_only, 'flagged': flagged,
                          'covered_at_edit': covered, 'generated_only': gen_only,
                          'no_declared_doc_subject': len(no_doc),
                          'blind_spots': BLIND_SPOTS}, indent=2))
        return 1 if flagged else 0

    print('INVOCATION PATH SCAN -- a check whose only trigger cannot fire for '
          'what it checks')
    print('')
    print('THE STRUCTURAL FACT THIS ALL RESTS ON, read from the source and not '
          'assumed:')
    print('  report_only_checks.hook_main() is gated on `git push`: %s'
          % ('YES -- every one of the %d registered checkers runs at PUSH '
             'time only' % len(rows) if push_only
             else 'NO -- it runs on any Bash command'))
    if push_only:
        print('  So a session that edits a document and never pushes runs them '
              'ZERO times.')
    print('')
    print('CANDIDATES -- declares a HAND-AUTHORED document as its subject, and '
          'has no Write|Edit trigger (%d)' % len(flagged))
    print('  These are candidates, NOT findings. Read each one: a document in '
          '`catches` may be a')
    print('  SOURCE the checker reads rather than the SUBJECT it checks, and '
          'this cannot tell.')
    for r in flagged:
        print('    %-34s %s' % (r['tool'], ', '.join(r['hand_authored'])))
        print('        triggers: %s' % ' + '.join(r['triggers']))
    print('')
    print('ALREADY COVERED AT EDIT TIME (%d)' % len(covered))
    for r in covered:
        print('    %-34s %s' % (r['tool'], ', '.join(r['hand_authored'])))
    print('')
    print('GENERATED-DOCUMENT SUBJECTS, counted SEPARATELY and not as findings '
          '(%d)' % len(gen_only))
    print('  An edit is not how a generated document changes, and the push gate '
          'already DENIES a')
    print('  push that leaves one stale -- a different and stronger guarantee '
          'than a report.')
    for r in gen_only:
        print('    %-34s %s' % (r['tool'], ', '.join(r['generated'])))
    print('')
    print('OUT OF SCOPE: %d registered checker(s) declare no document subject '
          'at all.' % len(no_doc))
    print('')
    print('WHAT THIS CANNOT SEE:')
    for b in BLIND_SPOTS:
        print('  - %s' % b)
    print('')
    print('REPORT ONLY. This tool classifies wiring and proposes nothing. '
          'Wiring a checker to')
    print('Write|Edit is a decision with a cost -- it runs on every edit in the '
          'repo -- and the')
    print('fix for a candidate below may equally be "its subject is not that '
          'document after all".')
    return 1 if flagged else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
