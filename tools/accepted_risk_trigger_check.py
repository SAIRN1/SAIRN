"""A trigger nobody watches is not a trigger -- the register's own rule, checked.

    python tools/accepted_risk_trigger_check.py
    python tools/accepted_risk_trigger_check.py --fixtures
    python tools/accepted_risk_trigger_check.py --json

Exit 0 clean, 1 on a finding, 2 when the register or the runners could not be
read. REPORT ONLY.

── WHY THIS IS ITS OWN FILE ───────────────────────────────────────────────────
`tools/weakness_combination.py` (item 53) found this. Its NOT_PROMOTED entry
says, in as many words, that its one genuinely mechanical half -- whether a
trigger claimed as MECHANICAL is watched by anything that runs -- COULD be
promoted on its own and SHOULD be split out first rather than promoting the
judgement half alongside it. This is that split, and the checker imports the
same functions so the two cannot disagree about what the register says.

── THE RULE, AND IT IS THE REGISTER'S OWN ─────────────────────────────────────
`docs/ACCEPTED-RISKS.md` opens by requiring every entry to name a trigger, and
requiring that trigger to be one of three things: MECHANICAL (a checker that
already runs, named by tool), an EVENT WITH AN OWNER, or honestly NONE. Its own
sentence: *"a trigger nobody watches is not a trigger."*

THIS CHECKS THE FIRST CLASS ONLY, and the distinction it turns on is narrow:

  PRODUCING a signal is not the same as CONSUMING one.

A module that returns a warning produces. Something has to read it. The entry
cannot show the difference, and the difference is the whole of whether the
trigger exists.

── WHAT COUNTS AS A CONSUMER ──────────────────────────────────────────────────
Anything that actually runs on this platform and names the mechanism:
`report_only_checks`, the push gate, `run_all_tests`, the hook settings, or a
GitHub workflow. Deliberately generous -- the finding this makes is "NOTHING
mentions it", which is a much stronger statement than "it is not wired the way
I expected".

── WHAT IT CANNOT DO ──────────────────────────────────────────────────────────
  * Tell you a mentioned mechanism is really acted on. Mentioned is necessary,
    not sufficient, and a clean run here is not evidence the trigger works.
  * Check a non-mechanical trigger. An EVENT WITH AN OWNER is a person, and no
    checker can tell whether a person is watching.
  * See a trigger nobody wrote down.
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import weakness_combination as W                                 # noqa: E402

CRITERIA_VERSION = '2026-09-15.1'


def fixtures():
    """The blind lock. Delegates to weakness_combination's, because the parsing
    and the classification ARE that module's -- re-implementing them here would
    give two sources that can disagree about the same register, which is the
    duplication this repo eliminates at the source rather than copying more
    carefully."""
    return W.fixtures()


def main(argv):
    if '--fixtures' in argv:
        lines, bad = fixtures()
        print('ACCEPTED-RISK TRIGGER CHECK -- blind lock, %d arms (shared with '
              'weakness_combination), no real register read' % len(lines))
        for l in lines:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad
                        else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    lines, bad = fixtures()
    if bad:
        print('THE FIXTURE LOCK FAILED -- the real register was not read.')
        for l in lines:
            print(l)
        return 2

    ents = W.parse()
    if ents is None:
        print('COULD NOT READ %s -- this is NOT a clean run.' % W.REGISTER)
        return 2
    runners = W.runner_text()
    if runners is None:
        print('COULD NOT READ ANY RUNNER FILE, so nothing could be checked.')
        print('This is NOT a clean run -- with no runner text every trigger')
        print('would look unwatched, which is a finding invented by a missing')
        print('file rather than found in one.')
        return 2

    unwatched = W.unwatched_triggers(ents, runners)
    claimed = [e for e in ents if e['mechanical_trigger']]

    if '--json' in argv:
        print(json.dumps({
            'criteria_version': CRITERIA_VERSION,
            'entries': len(ents),
            'claim_mechanical': [e['id'] for e in claimed],
            'unwatched': [{'id': i, 'missing': m, 'why': w}
                          for i, m, w in unwatched],
        }, indent=2))
        return 1 if unwatched else 0

    print('ACCEPTED-RISK TRIGGER CHECK -- criteria %s' % CRITERIA_VERSION)
    print('  %d entry(ies) in the register, %d claiming a MECHANICAL trigger.'
          % (len(ents), len(claimed)))
    print('')
    if not claimed:
        print('  NO ENTRY CLAIMS A MECHANICAL TRIGGER, so there is nothing here')
        print('  to check. That is NOT the same as clean: it means every')
        print('  accepted risk on this platform is watched by a person or by')
        print('  nothing, and this checker has no opinion about either.')
        return 0
    if unwatched:
        for ident, missing, why in unwatched:
            print('  UNWATCHED  %-6s %s' % (ident, why))
        print('')
        print('  A TRIGGER NOBODY WATCHES IS NOT A TRIGGER. Two fixes and they')
        print('  are not equivalent: wire a consumer, or change the entry to')
        print('  say what is really true. Leaving a monitored-looking entry')
        print('  that is not monitored is the worse of the three states,')
        print('  because it reads as coverage.')
        return 1
    print('  Every MECHANICAL trigger names a mechanism that at least one')
    print('  runner mentions. NECESSARY, NOT SUFFICIENT -- mentioned is not')
    print('  acted on, and a clean run here is not evidence the trigger works.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
