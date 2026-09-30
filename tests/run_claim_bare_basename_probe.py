"""tools/sairn_claim.py must not HARD-BLOCK on a bare shared basename.

    python tests/run_claim_bare_basename_probe.py

Exit 0 all arms pass, 1 any arm fails, 2 could not run.

── THE FALSE BLOCK (H2 seq 418, reproduced at HEAD) ────────────────────────
`file_verdict()` intersected the two declared file sets and refused on ANY
shared token. `declared_files()` stores whatever `FILE_TOKEN` matches, bare
basenames included -- so two claims naming the same AUDITOR-TOOL basename hard-
blocked each other:

    hover   "... FILES: citation_class_check.py hover_log.py register_citation_check.py"
    hover2  "... FILES: hover_log.py"
    -> ('refuse', {'hover_log.py'})

H1's `hover_log.py` lives in H1's own `hover-audit-log/` directory and H2's in
H2's. Neither is in the platform repo, no write conflict is possible, and the
two sessions were blocked from working at the same time by a filename.

A BARE BASENAME IS TOO WEAK A FILE IDENTITY TO REFUSE ON, and this file already
says so about the neighbouring case: a bare `docs/` is rejected as "a directory
claim this tool cannot reason about". A separator-bearing path is a reliable
cross-session identity; a lone basename names a file per clone.

── WHY THE CONTROLS ARE THE LOAD-BEARING HALF ──────────────────────────────
Widening a matcher until the complaint stops is indistinguishable from fixing
it. Arms 2-4 must pass BOTH before and after: a genuinely shared repo-relative
path still refuses, a MIXED overlap refuses on the real path and reports it as
the shared one, and a clear pair stays clear. The failure this fix must not
cause is two sessions editing one real file believing they were cleared.

Filed by H2 as TEXT ONLY -- that role edits nothing; this is hank applying it.
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for.
CONTROLS_FOR = ['sairn_claim.py']

import importlib.util
import os
import subprocess
import sys

REPO = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'],
                               text=True).strip()
TOOL = os.path.join(REPO, 'tools', 'sairn_claim.py')

# ── FAIL CLOSED ON AN ABSENT SUBJECT (PR §1.11) ─────────────────────────────
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


print('claim matcher -- a bare basename is not a file identity\n')

# ── ARM 1: THE FALSE BLOCK. The real strings, from the real claims. ─────────
H1 = ('citation work FILES: citation_class_check.py hover_log.py '
      'register_citation_check.py')
H2 = 'routable token validation FILES: hover_log.py'
v1, s1 = sc.file_verdict(H1, H2)
check('ARM 1: two claims sharing only a BARE auditor-tool basename are NOT '
      'hard-refused -- H1\'s hover_log.py and H2\'s are different files in '
      'different clones, neither in this repo',
      v1 != 'refuse', 'got %r shared=%r' % (v1, s1))
check('ARM 1b: ...and the weak overlap is still REPORTED rather than dropped, '
      'so the lexical matcher and the reader both still see it',
      s1 == {'hover_log.py'}, 'shared=%r' % (s1,))

# ── ARM 2: THE KNOWN-BAD CONTROL. A real shared path must still refuse. ─────
v2, s2 = sc.file_verdict('a FILES: tools/sairn_claim.py',
                         'b FILES: tools/sairn_claim.py')
check('ARM 2 CONTROL, must hold BOTH ways: a genuinely shared repo-relative '
      'path still REFUSES. Without this, "never refuse" satisfies arm 1 and '
      'two sessions edit one file believing they were cleared',
      v2 == 'refuse' and s2 == {'tools/sairn_claim.py'},
      'got %r shared=%r' % (v2, s2))

# ── ARM 3: MIXED. The real path decides, and is the one named. ─────────────
v3, s3 = sc.file_verdict('a FILES: tools/x.py hover_log.py',
                         'b FILES: tools/x.py hover_log.py')
check('ARM 3 CONTROL: a MIXED overlap refuses on the real path, and reports '
      'the real path as the reason rather than the basename',
      v3 == 'refuse' and 'tools/x.py' in s3, 'got %r shared=%r' % (v3, s3))

# ── ARM 4: no overlap is still clear, and no declaration is still unknown. ──
v4, _ = sc.file_verdict('a FILES: tools/a.py', 'b FILES: tools/b.py')
check('ARM 4 CONTROL: a genuinely disjoint pair is still CLEAR',
      v4 == 'clear', 'got %r' % (v4,))
v5, _ = sc.file_verdict('a claim with no declaration', 'b FILES: tools/b.py')
check('ARM 5 CONTROL: a side that declared nothing is still UNKNOWN, so the '
      'caller still falls through to the lexical matcher unchanged',
      v5 == 'unknown', 'got %r' % (v5,))

# ── ARM 6: A WINDOWS-SPELLED PATH IS STILL A PATH ──────────────────────────
# declared_files() normalises backslashes, so `tools\x.py` must count as
# separator-bearing. Without this arm the fix would silently treat every
# Windows-spelled path as a bare basename -- on the platform this repo is
# developed on, that is most of them.
v6, s6 = sc.file_verdict('a FILES: tools\\x.py', 'b FILES: tools/x.py')
check('ARM 6: a BACKSLASH-spelled path is separator-bearing and still refuses '
      '-- this repo is developed on Windows, so treating it as a bare name '
      'would turn the fix into a hole rather than a narrowing',
      v6 == 'refuse', 'got %r shared=%r' % (v6, s6))

print()
if fails:
    print('%d ARM(S) FAILED: %s' % (len(fails), ', '.join(fails)))
else:
    print('ALL ARMS PASS -- bare-basename false block cleared; every real '
          'shared path still refuses.')
sys.exit(1 if fails else 0)
