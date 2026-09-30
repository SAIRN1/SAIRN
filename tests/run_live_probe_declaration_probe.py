"""The control on tools/live_probe_declaration_check.py: each of the three real
failures must be caught, and the file's own prose must not be.

    python tests/run_live_probe_declaration_probe.py

── WHAT IT IS A CONTROL FOR ────────────────────────────────────────────────
tools/mech_gate_live_probe.py was written to be judged by
tools/live_probe_residue_audit.py, declared everything the auditor asks for, and
was unreadable to it three ways: a positional write action (absent from the
writing-probe list entirely), a multi-line residue concatenation (reported as
"declares no LIVE_PROBE_RESIDUE"), and a residue declaration that did not START
with a real path.

Every one of those is INDISTINGUISHABLE from not declaring at all, which is why
the subject asks a different question from the auditor: not "is there a
declaration" but "is the declaration UNREADABLE".

── AND THE HARDER HALF ─────────────────────────────────────────────────────
This check reads source looking for declaration names, so it is one comment away
from reporting the documents that describe the contract. Its first real run did
exactly that -- four findings, all prose, including the auditor's own docstring
examples. The must-not-fire arms below are the ones that decide whether it can be
a pre-commit gate.
"""
import io
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

TOOL = os.path.join(REPO, 'tools', 'live_probe_declaration_check.py')
if not os.path.isfile(TOOL):
    print('COULD NOT RUN: %s is missing. Nothing below was checked, and that is '
          'not a pass.' % TOOL)
    sys.exit(EXIT_COULD_NOT_RUN)

import live_probe_declaration_check as D                          # noqa: E402

# ── THE SUBJECT, DECLARED RATHER THAN INFERRED ──────────────────────────────
CONTROLS_FOR = ['live_probe_declaration_check.py']

passed = failed = 0


def ck(name, cond, detail=''):
    global passed, failed
    print(('  ok   ' if cond else '  FAIL ') + name)
    if cond:
        passed += 1
    else:
        failed += 1
        if detail:
            print('         ' + str(detail).replace('\n', '\n         ')[:500])


HOST = D.A.LIVE_HOST
GOOD = ("LIVE_PROBE_CLASS = 'VERIFICATION'\n"
        "LIVE_PROBE_RESIDUE = 'docs/live-residue/README.md -- one row, audit only'\n"
        "URL = 'https://%s/api/sd-data'\n"
        "action = 'write'\n" % HOST)


def kinds(src):
    return sorted(x['kind'] for x in D.inspect('fx.py', src))


print('tools/live_probe_declaration_check.py -- the three real failures, and the '
      'prose it must not report\n')

ck('0. the baseline fixture is CLEAN, or every arm below is measuring a broken '
   'fixture rather than the subject', kinds(GOOD) == [], kinds(GOOD))

# ── 1. THE THREE FAILURES THAT ACTUALLY HAPPENED ─────────────────────────────
ck('1. FAILURE 1 -- a POSITIONAL write action is WRITE-INVISIBLE-TO-THE-AUDITOR',
   'WRITE-INVISIBLE-TO-THE-AUDITOR' in kinds(
       GOOD.replace("action = 'write'", "call('write', 'mech_docs')")),
   kinds(GOOD.replace("action = 'write'", "call('write', 'mech_docs')")))

MULTI = GOOD.replace(
    "LIVE_PROBE_RESIDUE = 'docs/live-residue/README.md -- one row, audit only'",
    "LIVE_PROBE_RESIDUE = ('docs/live-residue/README.md -- one row, '\n"
    "                      'audit only')")
ck('2. FAILURE 2 -- a multi-line concatenation is UNPARSEABLE-DECLARATION, '
   'which is a DIFFERENT finding from "missing" and has a different fix',
   'UNPARSEABLE-DECLARATION' in kinds(MULTI), kinds(MULTI))

NOTFIRST = GOOD.replace(
    "'docs/live-residue/README.md -- one row, audit only'",
    "'one row per table, see docs/live-residue/README.md'")
ck('3. FAILURE 3 -- a residue path that is not the FIRST token is reported, '
   'because that is the token the auditor checks for existence',
   'RESIDUE-PATH-NOT-FIRST-OR-NOT-REAL' in kinds(NOTFIRST), kinds(NOTFIRST))

# ── 4. THE DIRECTIONS IT MUST NOT FIRE IN ────────────────────────────────────
ck('4. a file that never names the live host is ignored entirely -- this is not '
   'a general linter and pretending otherwise would put it in front of 900 files',
   kinds("LIVE_PROBE_RESIDUE = ('a' 'b')\nLIVE_PROBE_CLASS = ('x')\n") == [])

ck('4b. a GENUINELY ABSENT declaration is NOT reported -- that is the auditor\'s '
   'finding, and two tools reporting one fact can disagree about it',
   'UNPARSEABLE-DECLARATION' not in kinds("URL = 'https://%s/x'\n" % HOST))

ck('4c. "none -- <why>" needs no path, because a probe that cleans up after '
   'itself has no residue file to name',
   not [k for k in kinds(GOOD.replace(
       "'docs/live-residue/README.md -- one row, audit only'",
       "'none -- it upserts one row on the audit licence'"))
        if k.startswith('RESIDUE-PATH')])

ck('4d. a LOADER is not held to the write-literal rule -- it writes to real '
   'licences by design and the obligations are VERIFICATION\'s',
   'WRITE-INVISIBLE-TO-THE-AUDITOR' not in kinds(
       GOOD.replace("'VERIFICATION'", "'LOADER'")
           .replace("action = 'write'", "call('write', 'x')")))

# ── 5. THE PROSE PROBLEM, WHICH ITS OWN FIRST RUN CREATED ────────────────────
# FOUR FINDINGS, ALL PROSE. The auditor's docstring shows the three legal values
# as indented examples, and tools/tooling_inventory.py describes the contract in
# an entry. Both name the live host. An "is the name in the source" test read
# every one of those explanations as a broken declaration.
DOCSTRING_ONLY = (
    '"""A tool that EXPLAINS the contract.\n'
    '\n'
    "    LIVE_PROBE_CLASS = 'VERIFICATION'   # must obey all four obligations\n"
    "    LIVE_PROBE_RESIDUE = ('a' 'b')\n"
    '\n'
    'and it addresses https://%s in its prose too.\n'
    '"""\n'
    "SOMETHING = 1\n" % HOST)
ck('5. THE FIRST RUN\'S OWN FALSE POSITIVE: a docstring that SHOWS the '
   'declarations is not a declaration', kinds(DOCSTRING_ONLY) == [],
   kinds(DOCSTRING_ONLY))

COMMENT_ONLY = ("# LIVE_PROBE_CLASS = 'VERIFICATION'\n"
                "# LIVE_PROBE_RESIDUE = ('a' 'b')\n"
                "URL = 'https://%s/x'\n" % HOST)
ck('5b. ...and neither is a commented-out one',
   kinds(COMMENT_ONLY) == [], kinds(COMMENT_ONLY))

ck('5c. CONTROL FOR 5 AND 5b: the SAME declarations in real code ARE read, so '
   'those two arms are not passing because the check sees nothing at all',
   'UNPARSEABLE-DECLARATION' in kinds(
       "LIVE_PROBE_CLASS = 'VERIFICATION'\n"
       "LIVE_PROBE_RESIDUE = ('a' 'b')\n"
       "URL = 'https://%s/x'\n" % HOST))

# ── 6. IT REFUSES RATHER THAN SUBSTITUTING ITS OWN PARSER ────────────────────
ck('6. it depends on the AUDITOR\'S regexes by name, and _missing_parser() '
   'reports any that are gone -- a second copy would drift and then bless a '
   'declaration the auditor still cannot read',
   D._missing_parser() == [], D._missing_parser())
_real = D.A.RESIDUE_RE
try:
    del D.A.RESIDUE_RE
    ck('6b. KNOWN-BAD: with one of the auditor\'s regexes removed it reports the '
       'dependency by name rather than carrying on',
       D._missing_parser() == ['RESIDUE_RE'], D._missing_parser())
finally:
    D.A.RESIDUE_RE = _real
ck('6c. and the arm above put it back', D._missing_parser() == [])

# ── 7. THE PRE-COMMIT MODE READS THE INDEX ───────────────────────────────────
src = io.open(TOOL, encoding='utf-8').read()
ck('7. --staged reads STAGED content with `git show :<path>`, not the working '
   'tree -- a hook reading the worktree passes a commit whose staged version '
   'differs, which is the `git add -p` case',
   "'show', ':' + rel" in src and '--cached' in src)
ck('7b. ...and it restricts itself to tools/ tests/ scripts/, the auditor\'s own '
   'universe, so the two cannot disagree about which files are in scope',
   "('tools', 'tests', 'scripts')" in src)

p = subprocess.run([sys.executable, TOOL, '--staged'], cwd=REPO,
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
ck('7c. --staged runs and answers, whatever is staged right now (exit %d)'
   % p.returncode, p.returncode in (EXIT_CLEAN, EXIT_FINDING),
   (p.stdout or '') + (p.stderr or ''))
ck('7d. ...and says out loud that staged mode sees only what is staged',
   'STAGED MODE SEES ONLY WHAT IS STAGED' in (p.stdout or ''),
   (p.stdout or '')[-400:])

# ── 8. THE REAL RUN AND THE SELFTEST ─────────────────────────────────────────
p = subprocess.run([sys.executable, TOOL, '--selftest'], cwd=REPO,
                   capture_output=True, text=True, encoding='utf-8',
                   errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
ck('8. --selftest exits 0 (exit %d)' % p.returncode, p.returncode == EXIT_CLEAN,
   (p.stdout or '') + (p.stderr or ''))

p = subprocess.run([sys.executable, TOOL], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
out = (p.stdout or '') + (p.stderr or '')
ck('8b. the working-tree run is CLEAN on this repo, so arms 1-3 are controls '
   'rather than the tool\'s ordinary state (exit %d)' % p.returncode,
   p.returncode == EXIT_CLEAN
   and 'DECLARATIONS THE AUDITOR CANNOT PARSE: 0' in out,
   [l for l in out.split('\n') if 'CANNOT PARSE' in l])
ck('8c. ...and it prints its own blind population, including that it inherits '
   'every blind spot the auditor has',
   'BLIND TO THIS CHECK' in out and 'DYNAMICALLY BUILT' in out, out[-500:])

print('\n%d passed, %d failed' % (passed, failed))
sys.exit(EXIT_FINDING if failed else EXIT_CLEAN)
