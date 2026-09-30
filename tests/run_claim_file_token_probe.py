"""A claim must not name a file that does not exist and never has.

    python tests/run_claim_file_token_probe.py

Exit 0 all arms pass, 1 any arm fails, 2 could not run.

── THE DEFECT, AND IT SURFACED FOURTEEN DAYS LATE ──────────────────────────
A weekly idle-tool survey reported `items.md` as a tool untouched for 14 days
and asked whether it was safe to retire. There is no such file. There never was:
`git log --all` has never tracked one. It entered the claim record inside a
queue2 task string -- *"...items.md item 45..."* -- as shorthand for an item in a
queue document, and the claim matcher's FILE_TOKEN read it as a filename.

So a typo in a claim string became, a fortnight later, a retirement question
about a file nobody could find. The cost was not the typo; it was that nothing
looked at the string WHEN IT WAS WRITTEN, when the author was still in the room
and could have said what they meant.

── WHAT IS FLAGGED AND WHAT IS DELIBERATELY NOT ────────────────────────────
ONLY a BARE basename -- no separator -- that matches no tracked file's basename
anywhere in the repo.

A PATH-SHAPED token that does not exist is NOT flagged, and that exemption is
load-bearing rather than a convenience: claiming a file before creating it is
the correct order of work under PR 2.2, and this very session's claim named
three files that did not exist yet. A check that warned about those would fire
on every honest new-tool claim and be ignored within the week -- which is the
failure mode that matters most for a warning nobody is obliged to act on.

A bare basename that DOES match a tracked basename is also not flagged. That is
a different finding with a different answer -- H2 seq 418, the per-clone
ambiguity -- and conflating them would put two answers behind one message.
"""
CONTROLS_FOR = ['sairn_claim.py']

import importlib.util
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'sairn_claim.py')

if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- tools/sairn_claim.py does not exist, so NOTHING '
          'was verified. This is a failure, not a skip.')
    sys.exit(2)

sys.path.insert(0, os.path.join(REPO, 'tools'))
_spec = importlib.util.spec_from_file_location('sairn_claim', TOOL)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


print('claim file tokens -- a name that resolves to nothing, caught at claim '
      'time\n')

# ── A. THE REAL STRING THAT CAUSED IT ──────────────────────────────────────
REAL = ('sb_ts frozen week access path, dose audit local time display, clone '
        'registry fifth, items.md item 45, dispatch_state item 47 FAI, '
        'license.js gate column')
got = sc.unresolvable_file_tokens(REAL)
check('A1. THE REAL CASE: items.md is flagged -- a bare basename no tracked '
      'file carries, which is what surfaced 14 days later as a phantom '
      'retirement question',
      'items.md' in got, got)
check('A2. ...and license.js in the SAME string is NOT flagged, because '
      'api/_lib/license.js is tracked. A check that flagged both would be '
      'telling the author their real file is imaginary',
      'license.js' not in got, got)

# ── B. THE EXEMPTION THAT KEEPS THIS USABLE ────────────────────────────────
# Claiming a file before creating it is the correct order of work. This
# session's own claim named three files that did not exist yet.
NEW = ('tools/required_write_permission_check.py '
       'tests/run_required_write_permission_probe.py')
check('B1. a PATH-SHAPED token that does not exist yet is NOT flagged -- '
      'claiming before creating is PR 2.2, and warning on it would make this '
      'fire on every honest new-tool claim',
      sc.unresolvable_file_tokens(NEW) == [],
      sc.unresolvable_file_tokens(NEW))
check('B2. ...including a deep path that does not exist',
      sc.unresolvable_file_tokens('docs/nowhere/at/all/thing.md') == [],
      sc.unresolvable_file_tokens('docs/nowhere/at/all/thing.md'))
check('B3. ...and a WINDOWS-spelled path is a path too, not a bare name -- '
      'this repo is developed on Windows and treating tools\\x.py as bare '
      'would flag most real claims',
      sc.unresolvable_file_tokens('tools\\nope_not_here.py') == [],
      sc.unresolvable_file_tokens('tools\\nope_not_here.py'))

# ── C. THE OTHER FINDING IS NOT THIS ONE ───────────────────────────────────
check('C1. a bare basename that DOES match a tracked file is not flagged -- '
      'hover_log.py is the per-clone ambiguity from H2 seq 418, a different '
      'finding with a different answer',
      sc.unresolvable_file_tokens('FILES: sairn_claim.py') == [],
      sc.unresolvable_file_tokens('FILES: sairn_claim.py'))

# ── D. KNOWN-BAD CONTROLS. Without these, "flag nothing" passes A1. ───────
check('D1. an invented bare name IS flagged',
      sc.unresolvable_file_tokens('rewrite frobnicator.py today')
      == ['frobnicator.py'],
      sc.unresolvable_file_tokens('rewrite frobnicator.py today'))
check('D2. ...and several are all reported, not just the first',
      set(sc.unresolvable_file_tokens('a.py and b.md and c.json'))
      == {'a.py', 'b.md', 'c.json'},
      sc.unresolvable_file_tokens('a.py and b.md and c.json'))
check('D3. ordinary prose with a full stop is not a filename -- "item 45. the" '
      'must not read as a file',
      sc.unresolvable_file_tokens('finish item 45. the next one is 46.') == [],
      sc.unresolvable_file_tokens('finish item 45. the next one is 46.'))
check('D4. a version number is not a filename',
      sc.unresolvable_file_tokens('bump to 2.11 and 3.4') == [],
      sc.unresolvable_file_tokens('bump to 2.11 and 3.4'))
check('D5. an empty task is not a finding',
      sc.unresolvable_file_tokens('') == [], sc.unresolvable_file_tokens(''))

# ── E. IT WARNS AT CLAIM TIME, WHICH IS THE WHOLE POINT ───────────────────
# A finding that only a survey can reach is a finding that arrives 14 days late.
src = open(TOOL, encoding='utf-8').read()
check('E1. the claim path calls it, so the author sees it while they are still '
      'in the room', 'unresolvable_file_tokens(' in src
      and src.count('unresolvable_file_tokens(') >= 2,
      src.count('unresolvable_file_tokens('))
# AND IT MUST NOT BLOCK. Driven rather than grepped: a real claim carrying a
# phantom token still succeeds, in a throwaway clone so this repo's claim record
# is untouched.
_i = src.find('def unresolvable_file_tokens(')
_call = src.find('unresolvable_file_tokens(', src.find('def _warn_unresolvable')
                 if 'def _warn_unresolvable' in src else _i + 10)
check('E2. the warning path contains no refusal -- a claim naming a file that '
      'does not exist YET is normal, and a blocking check here would be wrong '
      'more often than right',
      'return 1' not in src[_call:_call + 700]
      and 'NOT CLAIMED' not in src[_call:_call + 700],
      src[_call:_call + 200])

# ── F. THE INDEX IS REAL ──────────────────────────────────────────────────
names = sc.tracked_basenames()
check('F1. the tracked-basename index is populated -- an empty one would flag '
      'every token in every claim', len(names) > 500, len(names))
check('F2. ...and it contains a file this repo certainly has',
      'sairn_claim.py' in names)
check('F3. ...and does NOT contain the phantom', 'items.md' not in names)

print()
if fails:
    print('%d ARM(S) FAILED: %s' % (len(fails), ', '.join(fails)))
else:
    print('ALL ARMS PASS -- the phantom is caught at claim time, and every '
          'legitimate shape is left alone.')
sys.exit(1 if fails else 0)
